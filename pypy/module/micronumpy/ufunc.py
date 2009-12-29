from pypy.module.micronumpy.ndarray import array, zeros, ndarray
from pypy.module.micronumpy.sdarray import sdarrytype
from pypy.module.micronumpy.mdarray import mdarrytype
from pypy.interpreter.baseobjspace import ObjSpace, W_Root
from pypy.interpreter.error import OperationError

def _assert_both(space, w_a, w_b):
    if not isinstance(w_a, ndarray) or not isinstance(w_b, ndarray):
        raise OperationError(space.w_TypeError,
                             space.wrap("expecting ndarray object"))

def minimum(space, w_a, w_b):
    _assert_both(w_a, w_b)
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

def dot(space, w_a, w_b):
    _assert_both(w_a, w_b)
    if len(w_b.array.shape)==1:
        w_b_new=zeros(space, space.newtuple([space.wrap(1), space.wrap(w_b.array.shape[0])]))
        for idx, value in enumerate(w_b.array.storage):
            w_b_new.array.storage[idx]=value
        w_b=w_b_new
    
    #waiting for slice.


