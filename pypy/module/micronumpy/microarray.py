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
from pypy.module.micronumpy.array import squeeze_shape
from pypy.module.micronumpy.array import squeeze, SQUEEZE_ME
from pypy.module.micronumpy.array import shape_prefix

from pypy.rpython.lltypesystem.lltype import cast_ptr_to_int

class MicroIter(Wrappable):
    _immutable_fields_ = ['array', 'offset', 'step', 'shape', 'ndim']
    def __init__(self, array):
        self.array = array
        self.i = 0
        self.shape = array.shape[0]
        self.step = array.slice_steps[0]
        self.stride = array.strides[0]
        self.ndim = len(array.shape)
        self.offset = 0

    def descr_iter(self, space):
        return space.wrap(self)
    descr_iter.unwrap_spec = ['self', ObjSpace]
    
    def descr_next(self, space):
        if self.i < self.shape:
            if self.ndim > 1:
                ar = MicroArray(self.array.shape,
                                self.array.dtype,
                                parent=self.array,
                                offset=self.offset + self.array.offset,
                                strides=self.array.strides[1:],
                                slice_steps=self.array.slice_steps[1:])
                next = space.wrap(ar)
            elif self.ndim == 1:
                next = self.array.getitem(space, self.offset)
            else:
                raise OperationError(space.w_ValueError,
                       space.wrap("Something is horribly wrong with this array's shape. Has %d dimensions." % len(self.array.shape)))
            self.i += 1
            self.offset += self.step * self.stride
            return next
        else:
            raise OperationError(space.w_StopIteration, space.wrap(""))
    descr_next.unwrap_spec = ['self', ObjSpace]

MicroIter.typedef = TypeDef('iterator',
                            __iter__ = interp2app(MicroIter.descr_iter),
                            next = interp2app(MicroIter.descr_next),
                           )


class MicroArray(BaseNumArray):
    _immutable_fields_ = ['parent', 'data', 'offset', 'shape', 'slice_steps', 'strides']
    def __init__(self, shape, dtype,
                 order='C', strides=None, parent=None,
                 offset=0, slice_steps=None):
        assert dtype is not None

        self.shape = shape
        self.dtype = dtype
        self.parent = parent
        self.order = order
        self.offset = offset

        if slice_steps is not None:
            self.slice_steps = slice_steps
        else:
            self.slice_steps = []

        for i in range(len(self.slice_steps), len(shape)):
            self.slice_steps.append(1)

        size = size_from_shape(shape)

        if strides is not None:
            self.strides = strides
        else:
            self.strides = []

        for i in range(len(self.strides), len(shape)):
            self.strides.append(self.stride(i))

        if size > 0 and parent is None:
            self.data = dtype.dtype.alloc(size)
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
            return self.dtype.dtype.w_getitem(space, self.data, self.offset + offset)
        except IndexError, e:
            raise OperationError(space.w_IndexError,
                                 space.wrap("index out of bounds"))

    def setitem(self, space, offset, w_value):
        """Helper function.
           Sets a value at an offset in the data."""
        try:
            self.dtype.dtype.w_setitem(space, self.data, self.offset + offset, w_value)
        except IndexError, e:
            raise OperationError(space.w_IndexError,
                                 space.wrap("index out of bounds"))

    def stride(self, i):
        if self.order == 'C':
            return stride_row(self.shape, i) # row order for C
        elif self.order == 'F':
            return stride_column(self.shape, i)
        else:
            raise NotImplementedError("Unknown order: '%s'" % self.order)

    def index2slices(self, space, w_index):
        dtype = self.dtype.dtype

        offset = 0

        try:
            index = space.int_w(space.index(w_index))
            if index < 0:
                index += self.shape[0]
            elif index >= self.shape[0]:
                raise OperationError(space.w_IndexError,
                                     space.wrap("index out of bounds"))

            offset = index * self.slice_steps[0] * self.strides[0]
            return offset, self.shape[1:], self.slice_steps[1:], self.strides[1:]
        except OperationError, e:
            if e.match(space, space.w_TypeError): pass
            else:raise

        if isinstance(w_index, W_SliceObject):
            start, stop, step, length = w_index.indices4(space, self.shape[0])
            offset = start * self.slice_steps[0] * self.strides[0]

            shape = self.shape[:]
            slice_steps = self.slice_steps[:]
            shape[0] = length
            slice_steps[0] *= step
            return offset, shape, slice_steps, self.strides[:]
        elif space.is_w(w_index, space.w_Ellipsis):
            return 0, self.shape[:], self.slice_steps[:], self.strides[:]

        indices = space.fixedview(w_index)
        
        ndim = len(self.shape)

        indexlen = len(indices)
        if indexlen > ndim:
            raise OperationError(space.w_IndexError,
                                 space.wrap("invalid index"))

        shape = [0] * ndim
        strides = [0] * ndim
        slice_steps = [0] * ndim

        resdim = 0

        for i in range(indexlen):
            w_index = indices[i]
            try:
                index = space.int_w(space.index(w_index))
                if index < 0:
                    index += self.shape[i]
                elif index >= self.shape[i]:
                    raise OperationError(space.w_IndexError,
                                         space.wrap("index out of bounds"))
                offset += index * self.slice_steps[i] * self.strides[i]
                continue

            except OperationError, e:
                if e.match(space, space.w_TypeError): pass
                else: raise

            if isinstance(w_index, W_SliceObject):
                start, stop, step, length = w_index.indices4(space, self.shape[i])
                offset += start * self.slice_steps[i] * self.strides[i]
                shape[resdim] = length
                slice_steps[resdim] = self.slice_steps[i] * step
                strides[resdim] = self.strides[i]
                resdim += 1
            elif space.is_w(w_index, space.w_Ellipsis):
                shape[resdim] = self.shape[i]
                slice_steps[resdim] = self.slice_steps[i]
                strides[resdim] = self.strides[i]
                resdim += 1
            else:
                index = space.str(w_index)
                raise OperationError(space.w_ValueError,
                                     space.wrap("Don't support records,"
                                                " so pretend we don't have this field"))
                raise OperationError(space.w_NotImplementedError, # this is the correct error
                                     space.wrap("Don't support records yet.")) # for what we actually do

        return offset, shape[:resdim], slice_steps[:resdim], strides[:resdim]

    def descr_getitem(self, space, w_index):
        offset, shape, slice_steps, strides = self.index2slices(space, w_index)

        size = size_from_shape(shape)

        if len(shape) == 0:
            return self.getitem(space, offset)
        else:
            ar = MicroArray(shape,
                            dtype=self.dtype,
                            parent=self,
                            offset=self.offset + offset,
                            strides=strides,
                            slice_steps=slice_steps)
            return space.wrap(ar)
    descr_getitem.unwrap_spec = ['self', ObjSpace, W_Root]

    def set_slice_single_value(self, space, offset, shape, slice_steps, strides, w_value):
        if len(shape) > 1:
            for i in range(shape[0]):
                self.set_slice_single_value(space, offset, shape[1:], slice_steps[1:], strides[1:], w_value)
                offset += slice_steps[0] * strides[0]
        else:
            for i in range(shape[0]):
                self.setitem(space, offset, w_value)
                offset += slice_steps[0] * strides[0]

    def set_slice(self, space, offset, shape, slice_steps, strides, w_value):
        try:
            length = space.int_w(space.len(w_value))

            if length == 1:
                w_value = space.getitem(w_value, space.wrap(0))
                self.set_slice_single_value(space, offset, shape, slice_steps, strides, w_value)
            else:
                raise OperationError(space.w_NotImplementedError, # XXX: TODO
                                     space.wrap("TODO"))
        except OperationError, e:
            if e.match(space, space.w_TypeError):
                self.set_slice_single_value(space, offset, shape, slice_steps, strides, w_value)
            else: raise

    def descr_setitem(self, space, w_index, w_value):
        dtype = self.dtype.dtype

        offset, shape, slice_steps, strides = self.index2slices(space, w_index)
        #print "Shape:", shape, "Steps:", slice_steps, "Strides:", strides

        size = size_from_shape(shape)

        try:
            value_shape = infer_shape(space, w_value)
            value_size = size_from_shape(value_shape)
        except OperationError, e:
            if e.match(space, space.w_TypeError):
                value_shape = []
                value_size = 0
            else: raise

        if len(value_shape) == 0 and len(shape) > 0:
            self.set_slice_single_value(space, offset, shape, slice_steps, strides,
                                        self.dtype.dtype.coerce(space, w_value))
        elif len(shape) == 0:
            if len(value_shape) > 0:
                raise OperationError(space.w_ValueError,
                                     space.wrap("shape mismatch: objects cannot"
                                                " be broadcast to a single shape"))

            self.setitem(space, offset, self.dtype.dtype.coerce(space, w_value))
        else:
            if shape != value_shape:
                raise OperationError(space.w_ValueError,
                                     space.wrap("shape mismatch: objects cannot"
                                                " be broadcast to a single shape"))

            self.set_slice(space,
                           offset, shape, slice_steps, strides,
                           w_value)
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

def descr_get_array_interface(space, self):
    w_dict = space.newdict()
    data_ptr = space.wrap(cast_ptr_to_int(self.data))
    data = [data_ptr, space.w_False]
    content = [(space.wrap('shape'), descr_get_shape(space, self)),
               (space.wrap('data'), space.newtuple(data)),
               (space.wrap('typestr'), space.wrap(self.dtype.dtype.typestr())),
               (space.wrap('version'), space.wrap(3))]
    w_dict.initialize_content(content)
    return w_dict

#TODO: add to typedef when ready
def descr_new(space, w_cls, w_shape, w_dtype=NoneNotWrapped,
              w_buffer=NoneNotWrapped, w_offset=NoneNotWrapped,
              w_strides=NoneNotWrapped, order='C'):
    from pypy.module import micronumpy
    shape_w = space.fixedview(w_shape)
    dtype_w = micronumpy.dtype.get(space, w_dtype)

    if w_strides is not None:
        strides_w = space.fixedview(w_strides)
    else:
        strides_w = []

    if w_offset is not None:
        offset_w = space.int_w(w_offset)
    else:
        offset_w = 0

    result = MicroArray(shape_w, dtype_w,
                        order=order,
                        strides=strides_w)
    return space.wrap(result)
descr_new.unwrap_spec = [ObjSpace, W_Root, W_Root, W_Root,
                         W_Root, W_Root,
                         W_Root, str]

MicroArray.typedef = TypeDef('uarray',
                             dtype = GetSetProperty(descr_get_dtype, cls=MicroArray),
                             shape = GetSetProperty(descr_get_shape, cls=MicroArray),
                             __array_interface__ = GetSetProperty(descr_get_array_interface, cls=MicroArray),
                             __getitem__ = interp2app(MicroArray.descr_getitem),
                             __setitem__ = interp2app(MicroArray.descr_setitem),
                             __len__ = interp2app(MicroArray.descr_len),
                             __repr__ = interp2app(MicroArray.descr_repr),
                             __str__ = interp2app(MicroArray.descr_str),
                             __iter__ = interp2app(MicroArray.descr_iter),
                            )

app_fill_array = gateway.applevel("""
    def fill_array(array, data):
        _fill_array([], array, data)

    def _fill_array(start, array, data):
        i = 0
        for element in data:
            try:
                _fill_array(start + [i], array, element)
            except TypeError, e:
                array[start + [i]] = element
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
               w_ar, w_xs)

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
