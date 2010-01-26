from pypy.interpreter.baseobjspace import ObjSpace, W_Root, Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app, NoneNotWrapped
from pypy.rlib.debug import make_sure_not_resized

from pypy.module.micronumpy.array import BaseNumArray
from pypy.module.micronumpy.array import base_typedef
from pypy.module.micronumpy.array import mul_operation, div_operation, add_operation, sub_operation
from pypy.module.micronumpy.array import copy_operation

from pypy.module.micronumpy.dtype import unwrap_int, coerce_int
from pypy.module.micronumpy.dtype import unwrap_float, coerce_float
from pypy.module.micronumpy.dtype import unwrap_float32, coerce_float32, float32
from pypy.module.micronumpy.dtype import result_mapping

# from pypy.interpreter.gateway import unwrap_spec #TODO: merge unwrap_spec decorator

class BaseSingleDimArray(BaseNumArray): pass

def create_sdarray(data_type, unwrap, coerce):
    class SingleDimIterator(Wrappable):
        def __init__(self, space, array, i):
            self.space = space
            self.array = array
            self.i = i

        def descr_iter(self):
            self.space = space
            return space.wrap(self)
        descr_iter.unwrap_spec = ['self']

        def descr_next(self):
            space = self.space
            try:
                result = self.array.storage[self.i]
                self.i += 1
                return space.wrap(result)
            except IndexError, e:
                raise OperationError(space.w_StopIteration, space.wrap(""))
        descr_iter.unwrap_spec = ['self']

    SingleDimIterator.typedef = TypeDef('iterator',
                                __iter__ = interp2app(SingleDimIterator.descr_iter),
                                next = interp2app(SingleDimIterator.descr_next)
                                )

    mul = mul_operation()
    div = div_operation()
    add = add_operation()
    sub = sub_operation()
    copy = copy_operation()

    class NumArray(BaseSingleDimArray):
        def __init__(self, space, length, dtype):
            self.shape = (length,)
            self.space = space
            self.storage = [data_type()] * length
            self.dtype = dtype
            make_sure_not_resized(self.storage)

        def create_client_math_operation(f):
            def scalar_operation(result, source, w_x):
                space = result.space
                x = coerce(space, w_x)
                for i in range(len(source.storage)):
                    result.storage[i] = f(data_type(source.storage[i]), x)

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
            return scalar_operation, fixedview_operation

        client_mul_scalar, client_mul_fixedview = create_client_math_operation(mul)
        client_div_scalar, client_div_fixedview = create_client_math_operation(div)
        client_add_scalar, client_add_fixedview = create_client_math_operation(add)
        client_sub_scalar, client_sub_fixedview = create_client_math_operation(sub)

        def create_math_operation(f):
            scalar_operation_name = '_'.join(['client', f.__name__, 'scalar'])
            fixedview_operation_name = '_'.join(['client', f.__name__, 'fixedview'])
            def math_operation(self, w_x):
                space = self.space
                if space.type(w_x) in (space.w_list, space.w_tuple):
                    raise OperationError(space.w_NotImplementedError,
                                         space.wrap("Haven't implemented array %s iterable yet!" % f.__name__))
                    result_t = result_mapping(space, (self.dtype, space.w_None))
                else:
                    result_t = result_mapping(space, (space.type(w_x), self.dtype))

                result = sdresult(space, result_t)(space, self.len(), self.dtype)
                getattr(result, scalar_operation_name)(self, w_x)

                w_result = space.wrap(result)
                return w_result
            math_operation.unwrap_spec = ['self', W_Root]
            return math_operation

        descr_mul = create_math_operation(mul)
        descr_mul.__name__ = 'descr_mul'

        descr_div = create_math_operation(div)
        descr_div.__name__ = 'descr_div'

        descr_add = create_math_operation(add)
        descr_add.__name__ = 'descr_add'

        descr_sub = create_math_operation(sub)
        descr_sub.__name__ = 'descr_sub'

        def load_iterable(self, w_values):
            space = self.space
            i = 0
            for x in space.fixedview(w_values, self.len()):
                self.storage[i] = coerce(space, x)
                i += 1

        def descr_iter(self):
            return space.wrap(SingleDimIterator(space, self, 0))
        descr_iter.unwrap_spec = ['self']

        def descr_getitem(self, index):
            space = self.space
            try:
                return space.wrap(self.storage[index])
            except IndexError:
                raise OperationError(space.w_IndexError,
                                     space.wrap("list index out of range"))
        descr_getitem.unwrap_spec = ['self', int]

        def descr_setitem(self, index, w_value):
            space = self.space
            try:
                self.storage[index] = coerce(space, w_value)
            except IndexError:
                raise OperationError(space.w_IndexError,
                                     space.wrap("list index out of range"))
            return space.w_None
        descr_setitem.unwrap_spec = ['self', int, W_Root]

        def len(self):
            return len(self.storage)

        def descr_len(self):
            space = self.space
            return space.wrap(self.len())
        descr_len.unwrap_spec = ['self']

        def str(self):
            return ', '.join([str(x) for x in self.storage])

        def descr_str(self):
            space = self.space
            return space.wrap("[%s]" % self.str())
        descr_str.unwrap_spec = ['self']

        def descr_repr(self):
            space = self.space
            return space.wrap("array([%s])" % self.str())
        descr_repr.unwrap_spec = ['self']

    NumArray.typedef = TypeDef('ndarray', base_typedef,
                               __mul__ = interp2app(NumArray.descr_mul),
                               __div__ = interp2app(NumArray.descr_div),
                               __add__ = interp2app(NumArray.descr_add),
                               __sub__ = interp2app(NumArray.descr_sub),
                               __getitem__ = interp2app(NumArray.descr_getitem),
                               __setitem__ = interp2app(NumArray.descr_setitem),
                               __len__ = interp2app(NumArray.descr_len),
                               __str__ = interp2app(NumArray.descr_str),
                               __repr__ = interp2app(NumArray.descr_repr),
                              )

    return NumArray

IntArray = create_sdarray(int, unwrap_int, coerce_int)
FloatArray = create_sdarray(float, unwrap_float, coerce_float)
Float32Array = create_sdarray(float32, unwrap_float32, coerce_float32)
GenericArray = None

class ResultFactory(object):
    def __init__(self, space):
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
