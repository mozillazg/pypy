from pypy.interpreter.baseobjspace import ObjSpace, W_Root, Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import NoneNotWrapped
from pypy.interpreter.gateway import interp2app

SQUEEZE_ME = -1

def stride_row(shape, i):
    assert i >= 0
    stride = 1
    ndim = len(shape)
    for s in shape[i + 1:]:
        stride *= s
    return stride

def stride_column(shape, i):
    assert i >= 0
    i -= 1
    stride = 1
    while i >= 0:
        stride *= shape[i]
        i -= 1
    return stride

def size_from_shape(shape):
    size = 1
    if len(shape) > 0:
        for dimension in shape:
            size *= dimension
        return size
    else:
        return 0

def broadcast_shapes(a_shape, a_strides, b_shape, b_strides):
    a_dim = len(a_shape)
    b_dim = len(b_shape)

    smaller_dim = a_dim if a_dim < b_dim else b_dim

    if a_dim > b_dim:
        result = a_shape
        larger_dim = a_dim
        smaller_dim = b_dim
        shorter_strides = b_strides
    else:
        result = b_shape
        larger_dim = b_dim
        smaller_dim = a_dim
        shorter_strides = a_strides

    i_a = a_dim - 1
    i_b = b_dim - 1
    for i in range(smaller_dim):
        assert i_a >= 0
        a = a_shape[i_a]

        assert i_b >= 0
        b = b_shape[i_b]

        if a == b or a == 1 or b == 1:
            i_a -= 1
            i_b -= 1
            result[len(result) - 1 - i] = a if a > b else b
        else:
            raise ValueError("frames are not aligned") # FIXME: applevel?
    
    if a_dim < b_dim:
        i_b += 1
        a_strides = [0] * i_b + a_strides
    else:
        i_a += 1
        b_strides = [0] * i_a + b_strides
    return result, a_strides, b_strides

def normalize_slice_starts(slice_starts, shape):
    for i in range(len(slice_starts)):
        if slice_starts[i] < 0:
            slice_starts[i] += shape[i]
        elif slice_starts[i] >= shape[i]:
            raise IndexError("invalid index")
    return slice_starts

def squeeze_shape(shape):
    "Simple squeeze."
    #return [x for x in shape if x != SQUEEZE_ME]
    return [x for x in shape if x != 1]

def squeeze(starts, shape, step, strides):
    offset = 0
    i = 0
    stop = len(shape)
    while i < stop:
        if shape[i] == SQUEEZE_ME:
            if i == 0:
                offset += starts[i]

            del starts[i]
            del shape[i]
            del step[i]
            del strides[i]
            stop -= 1
        else:
            i += 1
    return offset

def shape_prefix(shape):
    prefix = 0
    try:
        while shape[prefix] == 1: prefix += 1
    except IndexError, e:
        prefix = len(shape)

    return prefix

def shape_suffix(shape):
    suffix = len(shape)
    try:
        while shape[suffix - 1] == 1: suffix -= 1
    except IndexError, e:
        suffix = 0
    return suffix

def unpack_shape(space, w_shape):
    if space.is_true(space.isinstance(w_shape, space.w_int)):
        return [space.int_w(w_shape)]
    shape_w = space.fixedview(w_shape)
    return [space.int_w(w_i) for w_i in shape_w]

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
    try:
        values = space.str_w(w_values)
        return [len(values)]
    except OperationError, e:
        if e.match(space, space.w_TypeError): pass
        else: raise

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
