from pypy.interpreter.baseobjspace import ObjSpace
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.baseobjspace import W_Root
from pypy.objspace.std.sliceobject import W_SliceObject
from pypy.interpreter.error import OperationError

from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.gateway import NoneNotWrapped

from pypy.module import micronumpy
from pypy.module.micronumpy.dtype import null_data

from pypy.module.micronumpy.array import BaseNumArray
from pypy.module.micronumpy.array import infer_shape
from pypy.module.micronumpy.array import stride_row, stride_column, size_from_shape
from pypy.module.micronumpy.array import normalize_slice_starts

def index_w(space, w_index):
    return space.int_w(space.index(w_index))

class MicroIter(Wrappable):
    _immutable_fields_ = ['array', 'step', 'stop', 'ndim']
    def __init__(self, array):
        self.array = array
        self.i = array.slice_starts[0]
        self.step = array.slice_steps[0]
        self.stop = self.i + array.shape[0]
        self.ndim = len(self.array.shape)

    def descr_iter(self, space):
        return space.wrap(self)
    descr_iter.unwrap_spec = ['self', ObjSpace]
    
    def descr_next(self, space):
        if self.i < self.stop:
            if self.ndim > 1:
                ar = MicroArray(self.array.shape[1:],
                                self.array.dtype,
                                parent=self.array,
                                strides=self.array.strides[1:],
                                slice_starts=self.array.offsets + [self.i],
                                slice_steps=self.array.slice_steps[1:])
                self.i += 1
                return space.wrap(ar)
            elif self.ndim == 1:
                next = self.array.getitem(space, self.array.offset + self.array.flatten_index([self.i]))
                self.i += 1
                return next
            else:
                raise OperationError(space.w_ValueError,
                       space.wrap("Something is horribly wrong with this array's shape. Has %d dimensions." % len(self.array.shape)))
        else:
            raise OperationError(space.w_StopIteration, space.wrap(""))
    descr_next.unwrap_spec = ['self', ObjSpace]

MicroIter.typedef = TypeDef('iterator',
                            __iter__ = interp2app(MicroIter.descr_iter),
                            next = interp2app(MicroIter.descr_next),
                           )

class MicroArray(BaseNumArray):
    _immutable_fields_ = ['parent', 'shape', 'strides', 'offset', 'slice_starts']
    def __init__(self, shape, dtype, order='C', strides=[], parent=None, offset=0, slice_starts=[], slice_steps=[]):
        assert dtype is not None

        self.shape = shape
        self.dtype = dtype
        self.parent = parent
        self.order = order
        self.offset = offset

        self.slice_starts = slice_starts[:]
        for i in range(len(shape) - len(slice_starts)):
            self.slice_starts.append(0)

        self.slice_steps = slice_steps[:]
        for i in range(len(shape) - len(slice_steps)):
            self.slice_steps.append(1)

        dtype = dtype.dtype #XXX: ugly

        size = size_from_shape(shape)

        self.strides = strides[:]
        stridelen = len(self.strides)
        for i in range(len(self.shape) - stridelen):
            self.strides.append(self.stride(stridelen + i)) # XXX calling self.stride repeatedly is a bit wasteful

        if size > 0 and parent is None:
            self.data = dtype.alloc(size)
        elif parent is not None:
            self.data = parent.data
        else:
            self.data = null_data

    def descr_len(self, space):
        return space.wrap(self.shape[0])
    descr_len.unwrap_spec = ['self', ObjSpace]

    def getitem(self, space, offset):
        """Helper function.
           Grabs a value at an offset into the data."""
        try:
            dtype = self.dtype.dtype #XXX: kinda ugly
            return dtype.w_getitem(space, self.data, offset)
        except IndexError, e:
            raise OperationError(space.w_IndexError,
                                 space.wrap("index out of bounds"))

    def setitem(self, space, index, w_value):
        dtype = self.dtype.dtype #XXX: kinda ugly
        dtype.w_setitem(space, self.data, index, w_value) #maybe hang onto w_dtype separately?

    def flatten_index(self, index):
        """Computes offset into subarray from all information.
           Gives offset into subarray, not into data."""
        offset = 0
        for i in range(len(index)):
            offset += (self.slice_starts[i] + self.slice_steps[i] * index[i]) * self.strides[i]
        return offset

    def stride(self, i):
        if self.order == 'C':
            return stride_row(self.shape, i) # row order for C
        elif self.order == 'F':
            return stride_column(self.shape, i) #
        else:
            raise OperationError(space.w_NotImplementedError,
                                 space.wrap("Unknown order: '%s'" % self.order))

    def opposite_stride(self, i):
        if self.order == 'C': # C for C not Column, but this is opposite
            return stride_column(self.shape, i)
        elif self.order == 'F':
            return stride_row(self.shape, i)
        else:
            raise OperationError(space.w_NotImplementedError,
                                 space.wrap("Unknown order: '%s'" % self.order))

    def index2slices(self, space, w_index):
        dtype = self.dtype.dtype
        try:
            index = space.int_w(space.index(w_index))
            slice_starts = self.slice_starts[:]
            slice_starts[0] += index
            return slice_starts, self.shape[1:], self.slice_steps[1:]
        except OperationError, e:
            if e.match(space, space.w_TypeError): pass
            else:raise

        try:
            indices = space.fixedview(w_index)

            indexlen = len(indices)
            slack = len(self.shape) - indexlen

            assert slack >= 0
            
            slice_starts = self.slice_starts[:]
            slice_steps = self.slice_steps[:]
            strides = self.strides[:]
            shape = self.shape[:]

            for i in range(indexlen):
                w_index = indices[i]
                try:
                    index = space.int_w(space.index(w_index))
                    slice_starts[i] += index
                    shape[i] = 1
                    continue

                except OperationError, e:
                    if e.match(space, space.w_TypeError): pass
                    else: raise

                if isinstance(w_index, W_SliceObject):
                    start, stop, step, length = w_index.indices4(space, self.shape[i])
                    slice_starts[i] += start
                    shape[i] = length
                    slice_steps[i] *= step
                elif space.is_w(w_index, space.w_Ellipsis):
                    pass # I can't think of anything we need to do
                else:
                    # XXX: no exception handling because we *want* to blow up
                    print 'type(w_index) = %s, w_index = %s' % (type(w_index), w_index)
                    index = space.str(w_index)
                    raise OperationError(space.w_NotImplementedError,
                                         space.wrap("Don't support records yet.")) # XXX: and we may never

            try:
                slice_starts = normalize_slice_starts(slice_starts, self.shape) # XXX: could make in-place
            except IndexError, e:
                raise OperationError(space.w_IndexError,
                                     space.wrap("invalid index"))

            return slice_starts, shape, slice_steps

        finally: pass

    def descr_getitem(self, space, w_index):
        slice_starts, shape, slice_steps = self.index2slices(space, w_index)

        size = size_from_shape(shape)

        if size == 1:
            return self.getitem(space,
                                self.offset + self.flatten_index(slice_starts))
        else:
            ar = MicroArray(shape,
                            dtype=dtype,
                            parent=self,
                            offset=self.offset + offset, # XXX: need to figure out how to name things better 
                            slice_starts=slice_starts, # XXX: begin renaming slice_starts
                            slice_steps=slice_steps)
            return space.wrap(ar)
    descr_getitem.unwrap_spec = ['self', ObjSpace, W_Root]

    def set_slice_single_value(self, space, offset, shape, offsets, steps, w_value):
        index = offsets
        if len(shape) > 1:
            for i in shape[0]:
                self.set_slice_single_value(space, offset, shape[1:], index, steps[1:], w_value)
                index[len(index) - len(shape)] += steps[0] # XXX: reason
        else:
            dtype = self.dtype.dtype
            for i in range(0, shape[0]):
                self.set_slice_single_value(self, space,
                                            offset, shape, index, steps,
                                            w_value)
                index[len(index)-1] += steps[0] # XXX: don't do steps in range

    def set_slice(self, space, shape, offsets, steps, w_value):
        if self.dtype.w_is_compatible(space, w_value):
            self.set_slice_single_value(space, shape, offsets, steps, w_value)
        else:
            length = space.int_w(space.len(w_value))

            if length == 1:
                self.set_slice_single_value(space, shape, offsets, steps, w_value)
            else:
                raise OperationError(space.w_NotImplementedError,
                                     space.wrap("TODO"))

    def descr_setitem(self, space, w_index, w_value):
        dtype = self.dtype.dtype

        slice_starts, shape, slice_steps = self.index2slices(space, w_index)

        size = size_from_shape(shape)

        if size == 1:
            self.setitem(space,
                         self.offset + self.flatten_index(slice_starts),
                         w_value)
        else:
            try:
                if space.int_w(space.len(w_value)) == 1:
                    w_value = space.getitem(w_value, space.wrap(0))
                value_shape = infer_shape(space, w_value)
                value_size = size_from_shape(value_shape)

            except OperationError, e:
                if e.match(space, space.w_TypeError):
                    value_size = 1
                else: raise

                if value_size == 1:
                    pass # TODO: set one value many times

                if value_shape != shape:
                    raise OperationError(space.w_ValueError,
                                         space.wrap("shape mismatch: objects cannot"
                                                    " be broadcast to a single shape"))
                else:
                    self.set_slice(space, offset, shape, slice_starts, slice_steps, w_value)

    descr_setitem.unwrap_spec = ['self', ObjSpace, W_Root, W_Root]

    def descr_repr(self, space):
        return app_descr_repr(space, space.wrap(self))
    descr_repr.unwrap_spec = ['self', ObjSpace]

    # FIXME: Can I use app_descr_str directly somehow?
    def descr_str(self, space):
        return app_descr_str(space, space.wrap(self))
    descr_str.unwrap_spec = ['self', ObjSpace]

    def descr_iter(self, space):
        return space.wrap(MicroIter(self))
    descr_iter.unwrap_spec = ['self', ObjSpace]

    def __del__(self):
        if self.parent is None:
            assert self.data != null_data
            dtype = self.dtype.dtype
            dtype.free(self.data)

from pypy.interpreter import gateway

app_formatting = gateway.applevel("""
    from StringIO import StringIO
    def stringify(out, array, prefix='', commas=False, first=False, last=False, depth=0):
        if depth > 0 and not first:
            out.write('\\n')
            out.write(prefix) # indenting for array(
            out.write(' ' * depth) 

        out.write("[")
        if len(array.shape) > 1:
            i = 1
            for x in array:
                if i == 1:
                    stringify(out, x,
                              first=True, commas=commas, prefix=prefix, depth=depth + 1)
                elif i >= len(array):
                    stringify(out, x,
                              last=True, commas=commas, prefix=prefix, depth=depth + 1)
                else:
                    stringify(out, x,
                              commas=commas, prefix=prefix, depth=depth + 1)

                i += 1
            out.write("]")
        else:
            if commas:
                separator = ', '
            else:
                separator = ' '

            out.write(separator.join([str(x) for x in array]))

            if commas and not last:
                out.write("],")
            else:
                out.write("]")

    def descr_str(self):
        out = StringIO()
        stringify(out, self)
        result = out.getvalue()
        out.close()
        return result

    def descr_repr(self):
        out = StringIO()
        out.write("array(")
        stringify(out, self, commas=True, prefix='      ') 
        out.write(")")
        result = out.getvalue()
        out.close()
        return result
                       """)

app_descr_repr = app_formatting.interphook('descr_repr')
app_descr_str = app_formatting.interphook('descr_str')

# Getters, strange GetSetProperty behavior
# forced them out of the class
def descr_get_dtype(space, self):
    return space.wrap(self.dtype)

def descr_get_shape(space, self):
    return space.newtuple([space.wrap(x) for x in self.shape])

#TODO: add to typedef when ready
def descr_new(space, w_cls, w_shape, w_dtype=NoneNotWrapped,
              w_buffer=NoneNotWrapped, w_offset=NoneNotWrapped,
              w_strides=NoneNotWrapped, order='C'):
    from pypy.module.micronumpy import dtype
    shape_w = unpack_shape(space, w_shape)
    dtype_w = dtype.get(space, w_dtype)
    result = MicroArray(shape_w, dtype_w)
    #TODO: load from buffer
    return space.wrap(result)
descr_new.unwrap_spec = [ObjSpace, W_Root, W_Root, W_Root,
                         W_Root, W_Root,
                         W_Root, str]

MicroArray.typedef = TypeDef('uarray',
                             dtype = GetSetProperty(descr_get_dtype, cls=MicroArray),
                             shape = GetSetProperty(descr_get_shape, cls=MicroArray),
                             __getitem__ = interp2app(MicroArray.descr_getitem),
                             __setitem__ = interp2app(MicroArray.descr_setitem),
                             __len__ = interp2app(MicroArray.descr_len),
                             __repr__ = interp2app(MicroArray.descr_repr),
                             __str__ = interp2app(MicroArray.descr_str),
                             __iter__ = interp2app(MicroArray.descr_iter),
                            )

def reconcile_shapes(space, a, b):
    assert a == b, "Invalid assertion I think" # FIXME
    return a

app_fill_array = gateway.applevel("""
    def fill_array(start, a, b):
        i = 0
        for x in b:
            try:
                fill_array(start + [i], a, x)
            except TypeError, e:
                a[start + [i]] = x
            i += 1
                                  """)

fill_array = app_fill_array.interphook('fill_array')

def array(space, w_xs, w_dtype=NoneNotWrapped, copy=True, order='C', subok=False, w_ndim=NoneNotWrapped):
    if not order in 'CF':
        raise OperationError(space.w_TypeError,
                             space.wrap("order not understood"))

    if w_dtype is None:
        dtype = micronumpy.dtype.infer_from_iterable(space, w_xs)
    else:
        dtype = micronumpy.dtype.get(space, w_dtype)

    assert dtype is not None
    wrappable_dtype = dtype.wrappable_dtype()

    shape = infer_shape(space, w_xs)

    ar = MicroArray(shape, wrappable_dtype, order=order)
    w_ar = space.wrap(ar)

    fill_array(space,
               space.newlist([]), w_ar, w_xs)

    return w_ar
array.unwrap_spec = [ObjSpace, W_Root, W_Root, bool, str, bool, W_Root]

def zeros(space, w_shape, w_dtype=NoneNotWrapped, order='C'):
    try:
        shape_w = space.fixedview(w_shape)
        shape = [space.int_w(x) for x in shape_w]
    except OperationError, e:
        if e.match(space, space.w_TypeError):
            shape = [space.int_w(w_shape)]
        else: raise
    
    if w_dtype:
        dtype = micronumpy.dtype.get(space, w_dtype)
    else:
        dtype = micronumpy.dtype.int_descr

    ar = MicroArray(shape, dtype.wrappable_dtype())
    ar.order = order

    for i in range(size_from_shape(shape)):
        ar.setitem(space, i, space.wrap(0))

    return space.wrap(ar)
zeros.unwrap_spec = [ObjSpace, W_Root, W_Root]
