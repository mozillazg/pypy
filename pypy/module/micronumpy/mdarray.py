from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app, NoneNotWrapped
from pypy.interpreter.baseobjspace import ObjSpace, W_Root, Wrappable
from pypy.rlib.debug import make_sure_not_resized

from pypy.module.micronumpy.array import BaseNumArray

from pypy.module.micronumpy.dtype import unwrap_int, coerce_int
from pypy.module.micronumpy.dtype import unwrap_float, coerce_float
from pypy.module.micronumpy.dtype import unwrap_float32, coerce_float32, float32

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

def compute_slices(space, slices, dim):
    strides = []
    i = 1
    for d in dim:
        strides.append(i)
        i *= d
    strides.reverse()
    length = i
    shape = []
    sliceout = []
    for v in space.unpackiterable(slices):
        sliceoutnew=[] #FIXME: Not RPYthon - there are no slices.
        if space.is_true(space.isinstance(v, space.w_slice)):
            sl=space.unwrap(v)
            if sl.step<0:
                reverse=True
                sl=slice(sl.stop, sl.start, -sl.step)
            else:
                reverse=False
            stride=strides.pop(0)
            if sl.step == 1:
                newsl = [slice(stride*sl.start, stride*sl.stop)]
            else:
                newsl = []
                for i in range(sl.start, sl.stop, sl.step):
                    newsl.append(slice(stride*i, stride*(i+1)))

            if reverse:
                newsl.reverse()

            shape.append((sl.stop-sl.start)//sl.step)

            #here multiple old slices x new slices.
            for sl in sliceout:
                for sl2 in newsl:
                    pass #I have no time

        else:
            #extract item from slices, without appending to shape

        sliceout = sliceoutnew

    return shape, sliceout

#Was undetectable
class MultiDimArrayAbstract(BaseNumArray):

    def dtype(self, data):
        return self.__class__.data_type(data)

    def unwrap(self, w_data): #XXX: NOT USED
        return self.__class__.data_w(w_data)

    def coerce(self, data):
        return self.__class__.data_coerce(data)

    def __init__(self, space, shape):
        self.shape = shape
        self.space = space
        size = 1
        for dimension in shape:
            size *= dimension
        self.storage = [self.dtype(0.0)] * size
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
        self.storage[pos] = self.coerce(space, w_value)
        return space.w_None #XXX: necessary?

    def len(self):
        space = self.space
        return space.wrap(self.shape[0])

    def load_iterable(self, space, w_values):
        self._load_iter(space, w_values, 0)

    def _load_iter(self, space, w_values, start): #TODO: shape check
        vals=space.unpackiterable(w_values)
        if space.is_true(space.isinstance(vals[0], space.w_tuple) or space.is_true(space.isinstance(vals[0], space.w_list):
            idx=start
            for v in vals:
                add=self._load_iter(space, v, idx)
                idx+=add
            return idx
        else:
            idx=start
            for v in vals:
                self.storage[idx]=self.unwrap(val)
                idx+=1
            return idx
                

mdarraytype=MultiDimArrayAbstract

class MultiDimIntArray(MultiDimArrayAbstact):
    data_type, data_w, data_coerce = int, unwrap_int, coerce_int

MultiDimArray = MultiDimIntArray #XXX: compatibility

class MultiDimFloatArray(MultiDimArrayAbstact):
    data_type, data_w, data_coerce = float, unwrap_float, coerce_float

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
