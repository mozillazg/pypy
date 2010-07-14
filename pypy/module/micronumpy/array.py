from pypy.interpreter.baseobjspace import ObjSpace, W_Root, Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import NoneNotWrapped
from pypy.interpreter.gateway import interp2app

def iterable_type(space, xs):
    raise NotImplementedError("Stub")

def get_dtype(space, t):
    raise NotImplementedError("Stub")

def retrieve_dtype(space, t):
    raise NotImplementedError("Stub")

from pypy.rpython.lltypesystem import lltype

def validate_index(array, space, w_i):
    index_dimensionality = space.int_w(space.len(w_i))
    array_dimensionality = len(array.shape)
    for w_index in space.fixedview(w_i):
        if not ( space.is_true(space.isinstance(w_index, space.w_int)) or
                space.is_true(space.isinstance(w_index, space.w_slice)) or
                space.is_true(space.isinstance(w_index, space.w_list)) or
                space.is_w(w_index, space.w_Ellipsis) ):
            raise OperationError(space.w_ValueError,
                    space.wrap("each subindex must be either a slice, "
                        "an integer, Ellipsis, or newaxis"))
    if index_dimensionality > array_dimensionality:
        raise OperationError(space.w_IndexError,
                space.wrap("invalid index")) # all as in numpy

def infer_shape(space, w_values):
    shape = []
    while True:
        try:
            shape.append(space.int_w(space.len(w_values)))
        except OperationError, e:
            if e.match(space, space.w_TypeError):
                break
            elif e.match(space, space.w_IndexError):
                break #as numpy does
            else:
                raise
        else:
            w_values = space.getitem(w_values, space.wrap(0))
    return shape

def construct_array(space, shape, w_dtype):
    from pypy.module.micronumpy.microarray import MicroArray
    try:
        array = MicroArray(shape, w_dtype)
        return space.wrap(array)
    except KeyError, e:
        raise OperationError(space.w_NotImplementedError,
                space.wrap("Haven't implemented generic array yet!"))

class BaseNumArray(Wrappable):
    pass

BaseNumArray.typedef = TypeDef("ndarray")
ndarray = BaseNumArray
