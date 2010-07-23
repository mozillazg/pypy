from pypy.interpreter.baseobjspace import ObjSpace
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError

from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.gateway import NoneNotWrapped

from pypy.rlib.debug import make_sure_not_resized

from pypy.module import micronumpy
from pypy.module.micronumpy.array import BaseNumArray
from pypy.module.micronumpy.array import construct_array, infer_shape
from pypy.module.micronumpy.dtype import null_data

from pypy.module.micronumpy.array import stride_row, stride_column

def size_from_shape(shape):
    size = 1
    for dimension in shape:
        size *= dimension
    return size

def index_w(space, w_index):
    return space.int_w(space.index(w_index))

class MicroIter(Wrappable):
    _immutable_fields_ = ['array', 'stride']
    def __init__(self, array):
        self.array = array
        self.i = 0

    def descr_iter(self, space):
        return space.wrap(self)
    descr_iter.unwrap_spec = ['self', ObjSpace]
    
    def descr_next(self, space):
        if self.i < self.array.shape[0]: #will change for row/column
            if len(self.array.shape) > 1:
                ar = MicroArray(self.array.shape[1:], # ok for column major?
                                self.array.dtype,
                                parent=self.array,
                                strides=self.array.strides[1:],
                                offset=self.array.get_offset(self.array.flatten_index([self.i])))
                self.i += 1
                return space.wrap(ar)
            elif len(self.array.shape) == 1:
                next = self.array.getitem(space, self.array.flatten_index([self.i]))
                self.i += 1
                return next
            else:
                raise OperationError(space.w_ValueError,
                       space.wrap("Something is horribly wrong with this array's shape. Has %d dimensions." % len(self.array.shape)))
        else:
            raise OperationError(space.w_StopIteration, space.wrap(""))
    descr_next.unwrap_spec = ['self', ObjSpace]

    def __str__(self):
        from pypy.rlib.rStringIO import RStringIO as StringIO
        out = StringIO()
        out.write('iterator(i=')
        out.write(str(self.i))
        out.write(', array=')
        out.write(repr(self.array))
        out.write(')')
        result = out.getvalue()
        out.close()
        return result

MicroIter.typedef = TypeDef('iterator',
                            __iter__ = interp2app(MicroIter.descr_iter),
                            next = interp2app(MicroIter.descr_next),
                           )

class MicroArray(BaseNumArray):
    _immutable_fields_ = ['parent', 'offset']
    def __init__(self, shape, dtype, order='C', strides=None, parent=None, offset=0):
        self.shape = shape
        self.dtype = dtype
        self.parent = parent
        self.offset = offset

        self.order = order

        assert self.dtype is not None
        dtype = dtype.dtype #XXX: ugly

        size = size_from_shape(shape)

        if strides is not None:
            self.strides = strides
        else:
            self.strides = [0] * len(self.shape)
            for i in range(len(self.shape)):
                self.strides[i] = self.stride(i) # XXX calling self.stride repeatedly is a bit wasteful

        if size > 0 and parent is None:
            self.data = dtype.alloc(size)
        elif parent is not None:
            self.data = parent.data
        else:
            self.data = null_data

    def get_offset(self, index):
        return self.offset + index

    def descr_len(self, space):
        return space.wrap(self.shape[0])
    descr_len.unwrap_spec = ['self', ObjSpace]

    def getitem(self, space, index):
        try:
            dtype = self.dtype.dtype #XXX: kinda ugly
            return dtype.w_getitem(space, self.data,
                                   self.get_offset(index))
        except IndexError, e:
            raise OperationError(space.w_IndexError,
                                 space.wrap("index out of bounds"))

    def setitem(self, space, index, w_value):
        dtype = self.dtype.dtype #XXX: kinda ugly
        dtype.w_setitem(space, self.data, self.get_offset(index), w_value) #maybe hang onto w_dtype separately?

    def flatten_applevel_index(self, space, w_index):
        try:
            index = space.int_w(w_index)
            return index
        except OperationError, e:
            if not e.match(space, space.w_TypeError):
                raise

        index = space.fixedview(w_index)
        index = [index_w(space, w_x) for w_x in index]

        # Normalize indices
        for i in range(len(index)):
            if index[i] < 0:
                index[i] = self.shape[i] + index[i]
        return self.flatten_index(index) 

    def flatten_index(self, index):
        offset = 0
        for i in range(len(index)):
            offset += index[i] * self.strides[i]
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

    def descr_getitem(self, space, w_index):
        try:
            index = self.flatten_applevel_index(space, w_index)
            
            try:
                index_dimension = space.int_w(space.len(w_index))
            except OperationError, e:
                if e.match(space, space.w_TypeError):
                    index_dimension = 1
                else: raise

            if index_dimension == len(self.shape):
                return self.getitem(space, index)
            elif index_dimension < len(self.shape):
                assert index_dimension > 0
                array = MicroArray(self.shape[index_dimension:], self.dtype,
                                   parent=self, offset=self.get_offset(index))
                return space.wrap(array)
            else:
                raise OperationError(space.w_IndexError,
                                     space.wrap("invalid index"))

        except OperationError, e:
            if e.match(space, space.w_TypeError): pass # is there any way this can be caught here?
            else: raise

        # XXX: here be demons

        try:
            indices = []
            index = space.fixedview(w_index)
            if len(index) > len(self.shape):
                raise OperationError(space.w_ValueError,
                                           space.wrap("Index has more dimensions (%d) than array (%d)" % (len(index), len(self.shape))))

            for i in range(len(index)):
                indices.append([])

            for subindex in index:
                try:
                    raise OperationError(space.w_NotImplementedError,
                                         space.wrap("Haven't implemented newaxis."))
                except OperationError, e:
                    pass
                
        except OperationError, e:
            if e.match(space, space.w_StopIteration): pass
            else: raise


    descr_getitem.unwrap_spec = ['self', ObjSpace, W_Root]

    def descr_setitem(self, space, w_index, w_value):
        index = self.flatten_applevel_index(space, w_index)
        self.setitem(space, index, w_value)
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
        if self.parent is None and self.data != null_data:
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
