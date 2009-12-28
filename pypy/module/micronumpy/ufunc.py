from pypy.module.micronumpy.ndarray import array, zeros, ndarray
from pypy.interpreter.baseobjspace import ObjSpace, W_Root
from pypy.interpreter.error import OperationError

def minimum(space, w_a, w_b):
    if not isinstance(w_a, ndarray) or not isinstance(w_b, ndarray):
        raise OperationError(space.w_TypeError,
                             space.wrap("expecting ndarray object"))
    if w_a.array.length != w_b.array.length:
        raise OperationError(space.w_ValueError,
                             space.wrap("minimum of arrays of different length"))
    res = zeros(space, space.wrap(w_a.array.length), w_a.dtype)
    for i in range(len(w_a.array.storage)):
        one = w_a.array.storage[i]
        two = w_b.array.storage[i]
        if one < two:
            res.array.storage[i] = one
        else:
            res.array.storage[i] = two
    return space.wrap(res)
minimum.unwrap_spec = [ObjSpace, W_Root, W_Root]
