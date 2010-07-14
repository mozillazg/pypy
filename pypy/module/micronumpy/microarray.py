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
from pypy.module.micronumpy.dtype import null_storage

def size_from_shape(shape):
    size = 1
    for dimension in shape:
        size *= dimension
    return size

def index_w(space, w_index):
    return space.int_w(space.index(w_index))

def stride_row(shape, i):
    stride = 1
    ndim = len(shape)
    for s in shape[i + 1:]:
        stride *= s
    return stride

def stride_column(shape, i):
    if i < 1: return 1
    elif i == 1:
        return shape[0]
    stride = 1
    for s in shape[:i-1]:
        stride *= s
    return stride

class MicroIter(Wrappable):
    def __init__(self, array):
        self.array = array
        self.i = 0

    def descr_iter(self, space):
        return space.wrap(self)
    descr_iter.unwrap_spec = ['self', ObjSpace]
    
    def descr_next(self, space):
        if self.i < space.int_w(space.len(self.array)):
            next = self.array.getitem(space, self.i) # FIXME: wrong for multi dimensional! (would be easy applevel)
            self.i += 1
            return next
        else:
            raise OperationError(space.w_StopIteration, space.wrap(""))
    descr_next.unwrap_spec = ['self', ObjSpace]

MicroIter.typedef = TypeDef('iterator',
                            __iter__ = interp2app(MicroIter.descr_iter),
                            next = interp2app(MicroIter.descr_next),
                           )

class MicroArray(BaseNumArray):
    def __init__(self, shape, dtype, parent=None, offset = 0):
        self.shape = shape
        self.dtype = dtype
        self.parent = parent
        self.offset = offset
        self.order = 'C' #XXX: more forgiving to give it valid default

        assert self.dtype is not None
        dtype = dtype.dtype #XXX: ugly

        size = size_from_shape(shape)

        if size > 0 and parent is None:
            self.data = dtype.alloc(size)
        elif parent is not None:
            self.data = parent.data
        else:
            self.data = null_storage

    def descr_len(self, space):
        return space.wrap(self.shape[0])
    descr_len.unwrap_spec = ['self', ObjSpace]

    def getitem(self, space, index):
        try:
            dtype = self.dtype.dtype #XXX: kinda ugly
            return dtype.w_getitem(space, self.data, self.offset + index)
        except IndexError, e:
            raise OperationError(space.w_IndexError,
                                 space.wrap("index out of bounds"))

    def setitem(self, space, index, w_value):
        dtype = self.dtype.dtype #XXX: kinda ugly
        dtype.w_setitem(space, self.data, self.offset + index, w_value) #maybe hang onto w_dtype separately?

    def flatten_applevel_index(self, space, w_index):
        try:
            index = space.int_w(w_index)
            return index
        except OperationError, e:
            if not e.match(space, space.w_TypeError):
                raise

        index = space.fixedview(w_index)
        index = [index_w(space, w_x) for w_x in index]
        # XXX: normalize
        for i in range(len(index)):
            if index[i] < 0:
                index[i] = self.shape[i] + index[i]
        return self.flatten_index(space, index) 

    def create_flatten_index(stride_function):
        def flatten_index(self, index):
            offset = 0
            for i in range(len(index)):
                stride = stride_function(self.shape, i)
                offset += index[i] * stride
            return offset
        return flatten_index

    flatten_index_r = create_flatten_index(stride_row)
    flatten_index_c = create_flatten_index(stride_column)

    # FIXME: when different types are supported
    # this function will change
    def flatten_index(self, space, index):
        if self.order == 'C':
            return self.flatten_index_r(index) # row order for C
        elif self.order == 'F':
            return self.flatten_index_c(index) #
        else:
            raise OperationError(space.w_NotImplementedError,
                                 space.wrap("Unknown order: '%s'" % self.order))

    def descr_getitem(self, space, w_index):
        try:
            index = self.flatten_applevel_index(space, w_index)
            
            try:
                #w_iter = space.iter(w_index) # XXX: I guess len() should throw TypeError
                                              # FIXME: what about slices?
                index_dimension = space.int_w(space.len(w_index))
            except OperationError, e:
                if e.match(space, space.w_TypeError):
                    index_dimension = 1
                else: raise

            if index_dimension == len(self.shape):
                return self.getitem(space, index)
            elif index_dimension < len(self.shape):
                array = MicroArray(self.shape[index_dimension:], self.dtype,
                                   parent=self, offset=self.offset + index)
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
        return space.wrap("<MicroArray Object>")
    descr_repr.unwrap_spec = ['self', ObjSpace]

    def descr_iter(self, space):
        return space.wrap(MicroIter(self))
    descr_iter.unwrap_spec = ['self', ObjSpace]

    def __del__(self):
        if self.parent is None and self.data is not None:
            dtype = self.dtype.dtype
            dtype.free(self.data)

from pypy.interpreter import gateway

app_formatting = gateway.applevel("""
    from StringIO import StringIO
    def str(out, array):
        out.write("[")
        if len(array.shape) > 1:
            out.write(',\\n'.join([str(x) for x in array]))
        else:
            out.write(', '.join([str(x) for x in array]))
        out.write("]")

    def descr_str(self):
        out = StringIO()
        str(out, self)
        result = out.getvalue()
        out.close()
        return result

    def descr_repr(self):
        out = StringIO()
        out.write("array(")
        str(out, self)
        out.write(")")
        result = out.getvalue()
        out.close()
        return result
                       """)

app_descr_repr = app_formatting.interphook('descr_repr')

def microarray_descr_repr(self, space):
    return app_descr_repr(space, space.wrap(self))
microarray_descr_repr.unwrap_spec = ['self', ObjSpace]

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
                             __repr__ = microarray_descr_repr,
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
    if w_dtype is None:
        dtype = micronumpy.dtype.infer_from_iterable(space, w_xs)
    else:
        dtype = micronumpy.dtype.get(space, w_dtype)

    assert dtype is not None
    wrappable_dtype = dtype.wrappable_dtype()

    shape = infer_shape(space, w_xs)

    ar = MicroArray(shape, wrappable_dtype)
    ar.order = order
    w_ar = space.wrap(ar)

    fill_array(space,
               space.wrap([]), w_ar, w_xs)

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
