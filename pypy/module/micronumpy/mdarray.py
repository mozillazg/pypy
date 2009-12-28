from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app, NoneNotWrapped
from pypy.interpreter.baseobjspace import ObjSpace, W_Root, Wrappable
from pypy.rlib.debug import make_sure_not_resized

from pypy.module.micronumpy.array import BaseNumArray

def compute_pos(space, indexes, dim):
    current = 1
    pos = 0
    for i in range(len(indexes)):
        index = indexes[i]
        d = dim[i]
        if index >= d or index <= -d - 1:
            raise OperationError(space.w_IndexError,
                                 space.wrap("invalid index"))
        if index < 0:
            index = d + index
        pos += index * current
        current *= d
    return pos

class MultiDimArray(BaseNumArray):
    def __init__(self, space, shape, dtype):
        self.shape = shape
        self.space = space
        # ignore dtype for now
        size = 1
        for dimension in shape:
            size *= dimension
        self.storage = [0] * size
        make_sure_not_resized(self.storage)

    def _unpack_indexes(self, space, w_index):
        indexes = [space.int_w(w_i) for w_i in space.fixedview(w_index)]
        if len(indexes) != len(self.shape):
            raise OperationError(space.w_IndexError, space.wrap(
                'Wrong index'))
        return indexes

    def getitem(self, w_index):
        space = self.space
        indexes = self._unpack_indexes(space, w_index)
        pos = compute_pos(space, indexes, self.shape)
        return space.wrap(self.storage[pos])

    def setitem(self, w_index, w_value):
        space = self.space
        indexes = self._unpack_indexes(space, w_index)
        pos = compute_pos(space, indexes, self.shape)
        self.storage[pos] = space.int_w(w_value) #FIXME: lets get this thing generalized!
        return space.w_None #XXX: necessary?

    def len(self):
        space = self.space
        return space.wrap(self.shape[0])

def unpack_dtype(space, w_dtype):
    if space.is_w(w_dtype, space.w_int):
        return 'i'
    else:
        raise NotImplementedError
