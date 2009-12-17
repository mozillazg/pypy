from pypy.interpreter.baseobjspace import ObjSpace, W_Root, Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app, NoneNotWrapped
from pypy.rlib.debug import make_sure_not_resized

from pypy.rlib.objectmodel import specialize

result_types = {
                (int, int): int,
                (int, float): float,
                (float, int): float,
                (float, float): float
               }

class BaseNumArray(Wrappable):
    pass

def iterable_type(space, w_xs):
    xs = space.fixedview(w_xs)
    type = int
    for i in range(len(xs)):
        type = result_types[type, xs[i]]
    return type

def int_unwrapper(space, w_x):
    return space.int_w(space.int(w_x))

def float_unwrapper(space, w_x):
    return space.float_w(space.float(w_x))

def create_numarray(type, unwrapper, name):
    class NumArray(BaseNumArray):
        def __init__(self, space, length, dtype):
            #ignore dtype, irrelevant to optimized numarray implementations too
            self.length = length
            self.space = space
            self.storage = [type(0.0)] * length
            make_sure_not_resized(self.storage)


        def _dup_size(self, type):
            return self.__class__(space, result_types[self.type, type], self.length)

        def create_scalar_op(unwrap, f):
            def scalar_operation(self, w_x):
                space = self.space
                x = unwrap(w_x)
                result = self._dup_size(type(x))
                for i in range(self.length):
                    result[i] = f(self.storage[i], x)
                return space.wrap(result)
            return scalar_operation

        def create_fixedview_op(unwrap, f):
            def fixedview_operation(self, w_xs):
                space = self.space

                try:
                    xs = space.fixedview(w_xs, len(self.storage))
                except UnpackValueError, e:
                    # w_xs is of the wrong size
                    raise OperationError(space.w_ValueError,
                                         space.wrap("shape mismatch: objects cannot be broadcast to the same shape"))

                result = self._dup_size(iterable_type(space, xs))

                i = 0
                for w_x in xs:
                    result[i] = f(self.storage[i], unwrap(w_x))
                    i += 1
                return result
            return fixedview_operation

        #def mul_iterable(self, w_xs):
            #return self.fixedview_operation(w_xs, mul)
        
#        def descr_mul(self, w_x):
#            space = self.space
#            if space.type(w_x) in [W_Int, W_Float]: #complex, long
#                try:
#                    return self.mul_scalar(space.int_w(w_x))
#                except TypeError:
#                    return self.mul_scalar(space.float_w(w_x))
#            else:
#                return self.mul_iterable(w_x)
#        descr_mul.unwrap_spec = ['self', W_Root]

        def descr_getitem(self, index):
            space = self.space
            try:
                return space.wrap(self.storage[index])
            except IndexError:
                raise OperationError(space.w_IndexError,
                                     space.wrap("list index out of range"))
        descr_getitem.unwrap_spec = ['self', int]

        def descr_setitem(self, index, w_value):
            space = self.space
            try:
                self.storage[index] = unwrapper(space, w_value)
            except IndexError:
                raise OperationError(space.w_IndexError,
                                     space.wrap("list index out of range"))
            return space.w_None
        descr_setitem.unwrap_spec = ['self', int, W_Root]

        def descr_len(self):
            return self.space.wrap(len(self.storage))
        descr_len.unwrap_spec = ['self']

    def descr_init(xs): pass

    NumArray.typedef = TypeDef(
        name,
        #__init__ = interp2app(descr_init), #FIXME
        __getitem__ = interp2app(NumArray.descr_getitem),
        __setitem__ = interp2app(NumArray.descr_setitem),
        __len__     = interp2app(NumArray.descr_len),
    )
    return NumArray

IntArray = create_numarray(int, int_unwrapper, 'IntArray')
NumArray = IntArray # FIXME: compatibility for now
FloatArray = create_numarray(float, float_unwrapper, 'FloatArray')

#def array(space, w_xs): 
#    w_length = space.len(w_xs)
#    length = space.int_w(w_length)
#    #TODO: discover type
#    result = NumArray(space, type, length)
#array.unwrap_spec = [ObjSpace, W_Root]

def compute_pos(space, indexes, dim):
    current = 1
    pos = 0
    for i in range(len(indexes)):
        index = indexes[i]
        d = dim[i]
        if index >= d or index <= -d - 1:
            raise OperationError(space.w_IndexError,
                                 space.wrap("invalid index"))
        if index < 0:
            index = d + index
        pos += index * current
        current *= d
    return pos

class MultiDimArray(BaseNumArray):
    def __init__(self, space, dim, dtype):
        self.dim = dim
        self.space = space
        # ignore dtype for now
        size = 1
        for el in dim:
            size *= el
        self.storage = [0] * size
        make_sure_not_resized(self.storage)

    def _unpack_indexes(self, space, w_index):
        indexes = [space.int_w(w_i) for w_i in space.fixedview(w_index)]
        if len(indexes) != len(self.dim):
            raise OperationError(space.w_IndexError, space.wrap(
                'Wrong index'))
        return indexes

    def descr_getitem(self, w_index):
        space = self.space
        indexes = self._unpack_indexes(space, w_index)
        pos = compute_pos(space, indexes, self.dim)
        return space.wrap(self.storage[pos])
    descr_getitem.unwrap_spec = ['self', W_Root]

    def descr_setitem(self, w_index, value):
        space = self.space
        indexes = self._unpack_indexes(space, w_index)
        pos = compute_pos(space, indexes, self.dim)
        self.storage[pos] = value
        return space.w_None
    descr_setitem.unwrap_spec = ['self', W_Root, int]

    def descr_len(self):
        return self.space.wrap(self.dim[0])
    descr_len.unwrap_spec = ['self']

MultiDimArray.typedef = TypeDef(
    'NumArray',
    __getitem__ = interp2app(MultiDimArray.descr_getitem),
    __setitem__ = interp2app(MultiDimArray.descr_setitem),
    __len__     = interp2app(MultiDimArray.descr_len),
)

def unpack_dim(space, w_dim):
    if space.is_true(space.isinstance(w_dim, space.w_int)):
        return [space.int_w(w_dim)]
    dim_w = space.fixedview(w_dim)
    return [space.int_w(w_i) for w_i in dim_w]

def unpack_dtype(space, w_dtype):
    if space.is_w(w_dtype, space.w_int):
        return 'i'
    else:
        raise NotImplementedError

def zeros(space, w_dim, w_dtype):
    dim = unpack_dim(space, w_dim)
    dtype = unpack_dtype(space, w_dtype)
    if len(dim) == 1:
        return space.wrap(NumArray(space, dim[0], dtype))
    else:
        return space.wrap(MultiDimArray(space, dim, dtype))
zeros.unwrap_spec = [ObjSpace, W_Root, W_Root]
