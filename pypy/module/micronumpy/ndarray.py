from pypy.interpreter.baseobjspace import ObjSpace, W_Root, Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app, NoneNotWrapped
from pypy.interpreter.baseobjspace import ObjSpace, W_Root, Wrappable
from pypy.rlib.debug import make_sure_not_resized

from pypy.module.micronumpy.sdarray import sdresult
from pypy.module.micronumpy.sdarray import GenericArray

from pypy.module.micronumpy.mdarray import mdresult

def unpack_shape(space, w_shape):
    if space.is_true(space.isinstance(w_shape, space.w_int)):
        return [space.int_w(w_shape)]
    shape_w = space.fixedview(w_shape)
    return [space.int_w(w_i) for w_i in shape_w]

class ArrayIter(Wrappable): #FIXME: 1d only!
    def __init__(self, space, array, i):
        self.space = space
        self.array = array
        self.i = i

    def descr_iter(self):
        self.space = space
        return space.wrap(self)
    descr_iter.unwrap_spec = ['self']

    def descr_next(self):
        space = self.space
        try:
            result = self.array.array.storage[self.i]
            self.i += 1
            return space.wrap(result)
        except IndexError, e:
            raise OperationError(space.w_StopIteration, space.wrap(""))
    descr_iter.unwrap_spec = ['self']

ArrayIter.typedef = TypeDef('ArrayIter',
                            __iter__ = interp2app(ArrayIter.descr_iter),
                            next = interp2app(ArrayIter.descr_next))

def infer_shape(space, w_values): 
    return space.len(w_values) #TODO: handle multi-dimensional arrays...

class ndarray(Wrappable):
    def __init__(self, space, w_values, w_shape, w_dtype):
        self.array = None
        self.space = space
        if w_dtype == space.w_None:
            #TODO: infer type from w_values (better than this)
            w_dtype = space.type(space.getitem(w_values, space.wrap(0))) #FIXED

        self.dtype = w_dtype
        if w_shape == space.w_None:
            values_shape = infer_shape(space, w_values)
            shape_w = unpack_shape(space, values_shape)
        else:
            shape_w = unpack_shape(space, w_shape)

        try:
            if len(shape_w) == 1:
                length = shape_w[0]
                self.array = sdresult(space, w_dtype)(space, length)
            else:
                self.array = mdresult(space, w_dtype)(space, shape_w) #w_shape still may be w_None 
        except KeyError, e:
            raise OperationError(space.w_NotImplementedError,
                    space.wrap("Haven't implemented generic array yet!"))

        if not w_values == space.w_None:
            self.array.load_iterable(space, w_values) #TODO: implement loading for multi-dimensional arrays

    def validate_index(self, space, w_i):
        if space.type(w_i) == space.w_int: return

        if space.type(w_i) == space.w_str:
            raise OperationError(space.w_NotImplementedError,
                                 space.wrap("Haven't implemented field access yet!"))

        try:
            index_dimensionality = space.int_w(space.len(w_i))
            array_dimensionality = len(self.array.shape)
            if index_dimensionality > array_dimensionality:
                raise OperationError(space.w_IndexError,
                        space.wrap("Index dimensionality (%d) greater than array dimensionality (%d)." % (index_dimensionality, array_dimensionality)))
        except OperationError, e:
            if e.match(space, space.w_TypeError): pass
            else: raise

    def descr_mul(self, w_x):
        space = self.space
        if space.type(w_x) in (W_ListType, W_TupleType): #TODO: fooo
            #xs = space.fixedview(w_x)
            pass
        else:
            result_array = sdresult(space, space.type(w_x))(space, self.array.length)
            result_array.mul_scalar(self.array, w_x)
            result = ndarray(space, space.w_None, space.wrap(result_array.length), space.w_None) #FIXME: make ndarray.__init__ understand null args
            result.array = result_array
    descr_mul.unwrap_spec = ['self', W_Root]

    def descr_iter(self):
        space = self.space
        return space.wrap(ArrayIter(space, self, 0))
    descr_iter.unwrap_spec = ['self']

    def descr_getitem(self, space, w_i):
        self.validate_index(space, w_i)
        return self.array.getitem(w_i)
    descr_getitem.unwrap_spec = ['self', ObjSpace, W_Root]

    def descr_setitem(self, space, w_i, w_x):
        self.validate_index(space, w_i)
        self.array.setitem(w_i, w_x)
    descr_setitem.unwrap_spec = ['self', ObjSpace, W_Root, W_Root]

    def descr_len(self, space):
        return self.array.len()
    descr_len.unwrap_spec = ['self', ObjSpace]

ndarray.typedef = TypeDef(
    'ndarray',
    #__init__ = interp2app(descr_init), #FIXME
    __iter__ = interp2app(ndarray.descr_iter),
    __getitem__ = interp2app(ndarray.descr_getitem),
    __setitem__ = interp2app(ndarray.descr_setitem),
    __len__     = interp2app(ndarray.descr_len),
)

def array(space, w_values, w_shape=None, w_dtype=None):
    return ndarray(space, w_values, w_shape, w_dtype)
array.unwrap_spec = [ObjSpace, W_Root, W_Root, W_Root]

def zeros(space, w_shape, w_dtype):
    return array(space, space.w_None, w_shape, w_dtype)
zeros.unwrap_spec = [ObjSpace, W_Root, W_Root]
