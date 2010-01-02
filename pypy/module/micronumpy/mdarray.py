from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app, NoneNotWrapped
from pypy.interpreter.baseobjspace import ObjSpace, W_Root, Wrappable
from pypy.rlib.debug import make_sure_not_resized

from pypy.module.micronumpy.array import BaseNumArray

from pypy.module.micronumpy.dtype import unwrap_int, coerce_int
from pypy.module.micronumpy.dtype import unwrap_float, coerce_float

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

class BaseMultiDimArray(BaseNumArray): pass

def create_mdarray(data_type, unwrap, coerce):
    class MultiDimArray(BaseMultiDimArray):
        def __init__(self, space, shape):
            self.shape = shape
            self.space = space
            size = 1
            for dimension in shape:
                size *= dimension
            self.storage = [data_type(0.0)] * size
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
            self.storage[pos] = coerce(space, w_value)

        def load_iterable(self, w_xs):
            space = self.space
            raise OperationError(space.w_NotImplementedError,
                                       space.wrap("Haven't implemented iterable loading yet!"))

        def len(self):
            space = self.space
            return space.wrap(self.shape[0])

    return MultiDimArray

MultiDimIntArray = create_mdarray(int, unwrap_int, coerce_int)
MultiDimArray = MultiDimIntArray #XXX: compatibility
MultiDimFloatArray = create_mdarray(float, unwrap_float, coerce_float)

class ResultFactory(object):
    def __init__(self, space):
        self.space = space

        self.types = {
            space.w_int:   MultiDimIntArray,
            space.w_float: MultiDimFloatArray,
                     }

result_factory = None
def mdresult(space, t):
    global result_factory
    if result_factory is None:
        result_factory = ResultFactory(space)
    return result_factory.types[t]
