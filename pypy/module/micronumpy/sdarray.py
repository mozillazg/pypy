from pypy.interpreter.baseobjspace import ObjSpace, W_Root, Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app, NoneNotWrapped
from pypy.rlib.debug import make_sure_not_resized
from pypy.objspace.std.typeobject import W_TypeObject

from pypy.module.micronumpy.array import BaseNumArray
from pypy.module.micronumpy.array import mul_operation, div_operation, add_operation, sub_operation
from pypy.module.micronumpy.array import copy_operation
from pypy.module.micronumpy.dtype import unwrap_int, coerce_int
from pypy.module.micronumpy.dtype import unwrap_float, coerce_float
from pypy.module.micronumpy.dtype import unwrap_float32, coerce_float32, float32

def create_sdarray(data_type, unwrap, coerce):
class NumArrayAbstract(BaseNumArray):
    
    def dtype(self, data):
        return self.__class__.data_type(data)

    def unwrap(self, w_data):
        return self.__class__.data_w(w_data)

    def coerce(self, data):
        return self.__class__.data_coerce(data)

    def __init__(self, space, length):
        self.shape = (length,) #As in numpy
        self.length = length
        self.space = space
        self.storage = [self.dtype(0.0)] * length
        make_sure_not_resized(self.storage)

    mul = mul_operation()
    div = div_operation()
    add = add_operation()
    sub = sub_operation()
    copy = copy_operation()

    def create_scalar_op(f):
        def scalar_operation(self, space, source, w_x):
            space = self.space
            x = self.coerce(space, w_x)
            for i in range(source.length):
                self.storage[i] = f(source.storage[i], x)
        return scalar_operation

    mul_scalar = create_scalar_op(mul)
#        div_scalar = create_scalar_op(div)
#        add_scalar = create_scalar_op(add)
#        sub_scalar = create_scalar_op(sub)

    def create_fixedview_op(f):
        def fixedview_operation(self, w_xs):
            space = self.space
            try:
                xs = space.fixedview(w_xs, len(self.storage))
            except UnpackValueError, e:
                # w_xs is of the wrong size
                raise OperationError(space.w_ValueError,
                                     space.wrap("shape mismatch: objects cannot be broadcast to the same shape"))

            i = 0
            for w_x in xs:
                self.storage[i] = f(source.storage[i], self.coerce(w_x)) #TODO: probably shouldn't coerce
                i += 1
            return result
        return fixedview_operation

    copy_iterable = create_fixedview_op(copy)

    def load_iterable(self, space, w_values): #FIXME: less than ideal
        i = 0
        for x in space.fixedview(w_values, self.length):
            self.storage[i] = self.unwrap(space, x)
            i += 1

    def getitem(self, w_index):
        space = self.space
        index = space.int_w(w_index)
        try:
            return space.wrap(self.storage[index])
        except IndexError:
            raise OperationError(space.w_IndexError,
                                 space.wrap("list index out of range"))

    def setitem(self, w_index, w_value):
        space = self.space
        index = space.int_w(w_index)
        try:
            self.storage[index] = self.coerce(space, w_value)
        except IndexError:
            raise OperationError(space.w_IndexError,
                                 space.wrap("list index out of range"))
        return space.w_None

    def len(self):
        space = self.space
        return space.wrap(len(self.storage))

sdarraytype=NumArrayAbstact

class IntArray(NumArrayAbstact):
    data_type, data_w, data_coerce = int, unwrap_int, coerce_int

NumArray = IntArray #XXX: compatibility

class FloatArray(NumArrayAbstact):
    data_type, data_w, data_coerce = float, unwrap_float, coerce_float

class Float32Array(NumArrayAbstract):
    data_type, data_w, data_coerce = float32, unwrap_float32, coerce_float32

GenericArray = None

class ResultFactory(object):
    def __init__(self, space):
        self.space = space

        self.types = {
            space.w_int:   IntArray,
            space.w_float: FloatArray,
                     }

result_factory = None
def sdresult(space, t):
    global result_factory
    if result_factory is None:
        result_factory = ResultFactory(space)
    return result_factory.types[t]
