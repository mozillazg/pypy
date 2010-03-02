from pypy.interpreter.baseobjspace import ObjSpace, W_Root, Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import NoneNotWrapped
from pypy.interpreter.gateway import interp2app

from pypy.module.micronumpy.dtype import iterable_type

from pypy.module.micronumpy.dtype import get_dtype
from pypy.module.micronumpy.dtype import retrieve_dtype #FIXME: ambiguous name?

class BaseNumArray(Wrappable):
    pass

def validate_index(array, space, w_i):
    try:
        index_dimensionality = space.int_w(space.len(w_i))
        array_dimensionality = len(array.shape)
        if index_dimensionality > array_dimensionality:
            raise OperationError(space.w_IndexError,
                    space.wrap("Index dimensionality (%d) "
                        "greater than array dimensionality (%d)."
                        % (index_dimensionality, array_dimensionality)))
    except OperationError, e:
        if e.match(space, space.w_TypeError): pass
        else: raise

def mul_operation():
    def mul(x, y): return x * y
    return mul

def div_operation():
    def div(x, y): return x / y
    return div

def add_operation():
    def add(x, y): return x + y
    return add

def sub_operation():
    def sub(x, y): return x - y
    return sub

def copy_operation():
    def copy(x, y): return x #XXX: I sure hope GCC can optimize this
    return copy

def app_mul_operation():
    def mul(space, x, y):
        return space.mul(x, y)
    return mul

def app_div_operation():
    def div(space, x, y):
        return space.div(x, y)
    return div

def app_add_operation():
    def add(space, x, y):
        return space.add(x, y)
    return add

def app_sub_operation():
    def sub(space, x, y):
        return space.sub(x, y)
    return sub

def unpack_shape(space, w_shape):
    if space.is_true(space.isinstance(w_shape, space.w_int)):
        return [space.int_w(w_shape)]
    shape_w = space.fixedview(w_shape)
    return [space.int_w(w_i) for w_i in shape_w]

def infer_shape(space, w_values):
    shape = []
    while True:
        try:
            shape.append(space.int_w(space.len(w_values)))
        except OperationError, e:
            if e.match(space, space.w_TypeError):
                break
            elif e.match(space, space.IndexError):
                break #as numpy does
            else:
                raise
        else:
            w_values = space.getitem(w_values, space.wrap(0))
    return shape

def construct_array(space, shape, w_dtype):
    from pypy.module.micronumpy.sdarray import sdresult
    from pypy.module.micronumpy.mdarray import mdresult
    try:
        if len(shape) == 1:
            length = shape[0]
            return sdresult(w_dtype.code)(space, length, w_dtype)
        else:
            return mdresult(w_dtype.code)(space, shape, w_dtype)
    except KeyError, e:
        raise OperationError(space.w_NotImplementedError,
                space.wrap("Haven't implemented generic array yet!"))

def descr_new(space, w_cls, w_shape, w_dtype=NoneNotWrapped,
              w_buffer=NoneNotWrapped, w_offset=NoneNotWrapped,
              w_strides=NoneNotWrapped, order='C'):
    shape_w = unpack_shape(space, w_shape)
    dtype_w = get_dtype(space, w_dtype)
    result = construct_array(space, shape_w, dtype_w)
    #TODO: load from buffer?
    return space.wrap(result)
descr_new.unwrap_spec = [ObjSpace, W_Root, W_Root, W_Root,
                         W_Root, W_Root,
                         W_Root, str]

BaseNumArray.typedef = TypeDef("ndarray",
                       __new__ = interp2app(descr_new),
                      )
base_typedef = BaseNumArray.typedef
ndarray = BaseNumArray

def array(space, w_values, w_dtype=NoneNotWrapped,
          copy=True, order='C',
          subok=False, ndim=1):
    shape = infer_shape(space, w_values)

    if w_dtype is None:
        dtype_w = retrieve_dtype(space, iterable_type(space, w_values))
    else:
        dtype_w = get_dtype(space, w_dtype)
    result = construct_array(space, shape, dtype_w)
    result.load_iterable(w_values)
    return space.wrap(result)
array.unwrap_spec = [ObjSpace, W_Root, W_Root,
                     bool, str,
                     bool, int]

def zeros(space, w_shape, w_dtype=NoneNotWrapped, order='C'):
    shape_w = unpack_shape(space, w_shape)
    if w_dtype is None:
        dtype_w = retrieve_dtype(space, 'd')
    else:
        dtype_w = get_dtype(space, w_dtype)
    result = construct_array(space, shape_w, dtype_w)
    return space.wrap(result)
zeros.unwrap_spec = [ObjSpace, W_Root, W_Root, str]
