from pypy.interpreter.baseobjspace import ObjSpace, W_Root, Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app, NoneNotWrapped
from pypy.interpreter.baseobjspace import ObjSpace, W_Root, Wrappable
from pypy.rlib.debug import make_sure_not_resized

from pypy.module.micronumpy.sdarray import sdresult
from pypy.module.micronumpy.sdarray import GenericArray

from pypy.module.micronumpy.mdarray import mdresult

def result_type(space, w_types):
    types = {
            (space.w_int, space.w_int): space.w_int,
            (space.w_int, space.w_float): space.w_float,
            (space.w_float, space.w_int): space.w_float,
            (space.w_float, space.w_float): space.w_float
            }
    return types[w_types]

def mul_scalar(result, source, w_x):     result.mul_scalar(source, w_x)
def mul_fixedview(result, source, w_xs): result.mul_fixedview(source, w_xs)

def div_scalar(result, source, w_x):     result.div_scalar(source, w_x)
def div_fixedview(result, source, w_xs): result.div_fixedview(source, w_xs)

def add_scalar(result, source, w_x):     result.add_scalar(source, w_x)
def add_fixedview(result, source, w_xs): result.add_fixedview(source, w_xs)

def sub_scalar(result, source, w_x):     result.sub_scalar(source, w_x)
def sub_fixedview(result, source, w_xs): result.sub_fixedview(source, w_xs)

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
    return [space.int_w(space.len(w_values))] #TODO: handle multi-dimensional arrays...

class ndarray(Wrappable):
    def __init__(self, space, w_values, w_shape=NoneNotWrapped, w_dtype=NoneNotWrapped):
        self.array = None
        self.space = space
        if w_dtype is None and not space.is_w(w_values, space.w_None):
            #TODO: infer type from w_values (better than this)
            w_dtype = space.type(space.fixedview(w_values)[0]) #FIXME: Allocates an entire array and throws it away!

        self.dtype = w_dtype
        shape_w = None
        if w_shape is None:
            try:
                shape_w = infer_shape(space, w_values)
            except OperationError, e:
                if e.match(space, space.w_TypeError): pass
                else: raise
        else:
            shape_w = unpack_shape(space, w_shape)

        if not shape_w is None and not w_dtype is None:
            try:
                if len(shape_w) == 1:
                    length = shape_w[0]
                    self.array = sdresult(space, w_dtype)(space, length)
                else:
                    self.array = mdresult(space, w_dtype)(space, shape_w)
            except KeyError, e:
                raise OperationError(space.w_NotImplementedError,
                        space.wrap("Haven't implemented generic array yet!"))

        if not w_values is None and not space.is_w(w_values, space.w_None):
            self.array.load_iterable(w_values) #TODO: implement loading for multi-dimensional arrays

    def validate_index(self, space, w_i):
        try:
            index_dimensionality = space.int_w(space.len(w_i))
            array_dimensionality = len(self.array.shape)
            if index_dimensionality > array_dimensionality:
                raise OperationError(space.w_IndexError,
                        space.wrap("Index dimensionality (%d) greater than array dimensionality (%d)." % (index_dimensionality, array_dimensionality)))
        except OperationError, e:
            if e.match(space, space.w_TypeError): pass
            else: raise

    def create_math_operation(f):
        def math_operation(self, w_x):
            space = self.space
            if space.type(w_x) in (space.w_list, space.w_tuple):
                raise OperationError(space.w_NotImplementedError,
                                     space.wrap("Haven't implemented array * iterable yet!"))
            else:
                result_t = result_type(space, (space.type(w_x), self.dtype))
                result_array = sdresult(space, result_t)(space, self.array.length) #FIXME: support multi-dimensional array!
                #result_array.mul_scalar(self.array, w_x) #TODO: reverse so that result_array = self.array.mul_scalar(w_x)
                f(result_array, self.array, w_x) #TODO: can i use member function pointers?

                result = ndarray(space, space.w_None, None, None)
                result.array = result_array
                w_result = space.wrap(result)
            return w_result
        math_operation.unwrap_spec = ['self', W_Root]
        return math_operation

    # Math Operations
    descr_mul = create_math_operation(mul_scalar)
    descr_div = create_math_operation(div_scalar)
    descr_add = create_math_operation(add_scalar)
    descr_sub = create_math_operation(sub_scalar)

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

    def descr_str(self, space):
        return space.wrap("[%s]" % self.array.str())
    descr_str.unwrap_spec = ['self', ObjSpace]

    def descr_repr(self, space):
        return space.wrap("array([%s])" % self.array.str())
    descr_repr.unwrap_spec = ['self', ObjSpace]


def descr_new(space, w_cls, w_shape,
              w_buffer=NoneNotWrapped, w_offset=NoneNotWrapped,
              w_strides=NoneNotWrapped, order=NoneNotWrapped):
    result = ndarray(space, w_None, w_shape, None)
    return space.wrap(result)
descr_new.unwrap_spec = [ObjSpace, W_Root, W_Root,
                         W_Root, W_Root, 
                         W_Root, str]

ndarray.typedef = TypeDef(
    'ndarray',
    #__init__ = interp2app(descr_init), #FIXME
    __new__ = interp2app(descr_new),
    __iter__ = interp2app(ndarray.descr_iter),
    __mul__ = interp2app(ndarray.descr_mul),
    __div__ = interp2app(ndarray.descr_div),
    __add__ = interp2app(ndarray.descr_add),
    __sub__ = interp2app(ndarray.descr_sub),
    __str__ = interp2app(ndarray.descr_str),
    __repr__ = interp2app(ndarray.descr_repr),
    __getitem__ = interp2app(ndarray.descr_getitem),
    __setitem__ = interp2app(ndarray.descr_setitem),
    __len__     = interp2app(ndarray.descr_len),
)

def array(space, w_values, w_shape=NoneNotWrapped, w_dtype=NoneNotWrapped):
    return ndarray(space, w_values, w_shape, w_dtype)
array.unwrap_spec = [ObjSpace, W_Root, W_Root, W_Root]

def zeros(space, w_shape, w_dtype=NoneNotWrapped):
    return ndarray(space, None, w_shape, w_dtype)
zeros.unwrap_spec = [ObjSpace, W_Root, W_Root]
