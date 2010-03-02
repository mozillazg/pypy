from pypy.module.micronumpy.array import array, zeros, ndarray
from pypy.module.micronumpy.array import construct_array
from pypy.module.micronumpy.dtype import result_mapping
from pypy.module.micronumpy.sdarray import sdresult
from pypy.module.micronumpy.mdarray import mdresult, compute_pos

from pypy.module.micronumpy.dtype import retrieve_dtype

from pypy.interpreter.baseobjspace import ObjSpace, W_Root
from pypy.interpreter.error import OperationError
from pypy.rlib.debug import make_sure_not_resized

def minimum(space, w_a, w_b):
    if not isinstance(w_a, ndarray) or not isinstance(w_b, ndarray):
        raise OperationError(space.w_TypeError,
                             space.wrap("expecting ndarray object"))
    if w_a.len()!= w_b.len():
        raise OperationError(space.w_ValueError,
                             space.wrap("minimum of arrays of different length"))
    dtype = result_mapping(space, (w_a.dtype, w_b.dtype))
    res = construct_array(space, w_a.shape, retrieve_dtype(space, dtype))
    for i in range(len(w_a.storage)):
        one = w_a.storage[i]
        two = w_b.storage[i]
        if one < two:
            res.storage[i] = one
        else:
            res.storage[i] = two
    return space.wrap(res)
minimum.unwrap_spec = [ObjSpace, W_Root, W_Root]

def dot(space, w_a, w_b):
    if not isinstance(w_a, ndarray) or not isinstance(w_b, ndarray):
        raise OperationError(space.w_TypeError,
                space.wrap("expecting ndarray object"))

    if len(w_b.shape) == 1:
        the_b = mdresult(space, w_b.dtype)(space, [w_b.shape[0], 1], w_b.dtype)
        the_b.storage[:] = w_b.storage
        w_b = the_b

    if len(w_a.shape)%2:
        the_a = mdresult(space, w_a.dtype)(space, [1]+w_a.shape, w_a.dtype)
        the_a.storage[:] = w_a.storage
        w_a = the_a
    ah, aw = w_a.shape[0], w_a.shape[1]
    als = len(w_a.shape)

    if len(w_b.shape)%2:
        the_b = mdresult(space, w_b.dtype)(space, [1]+w_b.shape, w_b.dtype)
        the_b.storage[:] = w_b.storage
        w_b = the_b
    bh, bw = w_a.shape[0], w_a.shape[1]
    bls = len(w_b.shape)


    if aw == bh == 1:
        return dot(space, w_b, w_a)

    shapemismatch = OperationError(space.w_TypeError,
                             space.wrap('shape mismatch'))

    if aw != bh:
        raise shapemismatch

    if als != bls:
        raise shapemismatch
    

    data = _dotit(space, w_a, w_b, als, [], [])
    if len(data) == 1:
        return space.wrap(data[0])
    shape = make_sure_not_resized([0]*als)
    for i in range(0, als, 2):
        shape[i] = w_a.shape[i]
        shape[i+1] = w_b.shape[i+1]

    dtype = result_mapping(space, (w_a.dtype, w_b.dtype))

    res = construct_array(space, shape, retrieve_dtype(space, dtype))
    res.storage[:] = data
    return space.wrap(res)
dot.unwrap_spec = [ObjSpace, W_Root, W_Root]

def _dotit(space, w_a, w_b, ls, indices1, indices2):
    if len(indices1) == ls:
        return w_a.storage[compute_pos(indices1)] * \
               w_b.storage[compute_pos(indices2)]
    else:
        shift = len(indices1)
        h = w_a.shape[shift]
        w = w_b.shape[shift+1]
        l = w_a.shape[shift+1]
        if l != w_b.shape[shift]:
            raise shapemismatch
        total = []
        for i in range(h):
            for j in range(w):
                #check if numbers on next level
                if shift+2 == als:
                    sum = 0
                    for k in range(l):
                        sum += _dotit(indices1+[i, l], indices2+[l, j])
                    total.append(sum)
                else:
                    sum = None
                    for k in range(l):
                        arg = _dotit(indices1+[i, l], indices2+[l, j])
                        if sum == None:
                            sum = arg
                        else:
                            for idx in range(len(sum)):
                                sum[idx] += arg[idx]
                    total.extend(sum)

        return make_sure_not_resized(total)
