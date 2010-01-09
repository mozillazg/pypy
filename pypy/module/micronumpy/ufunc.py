from pypy.module.micronumpy.array import array, zeros, ndarray
from pypy.interpreter.baseobjspace import ObjSpace, W_Root
from pypy.interpreter.error import OperationError

def minimum(space, w_a, w_b):
    if not isinstance(w_a, ndarray) or not isinstance(w_b, ndarray):
        raise OperationError(space.w_TypeError,
                             space.wrap("expecting ndarray object"))
    if w_a.len()!= w_b.len():
        raise OperationError(space.w_ValueError,
                             space.wrap("minimum of arrays of different length"))
    res = zeros(space, space.wrap(w_a.len()), w_a.dtype)
    for i in range(len(w_a.storage)):
        one = w_a.storage[i]
        two = w_b.storage[i]
        if one < two:
            res.storage[i] = one
        else:
            res.storage[i] = two
    return space.wrap(res)
minimum.unwrap_spec = [ObjSpace, W_Root, W_Root]
