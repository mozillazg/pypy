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
