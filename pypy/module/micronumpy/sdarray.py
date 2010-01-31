from pypy.interpreter.baseobjspace import W_Root, Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.interpreter.gateway import interp2app
from pypy.rlib.debug import make_sure_not_resized

from pypy.module.micronumpy.array import BaseNumArray
from pypy.module.micronumpy.array import base_typedef
from pypy.module.micronumpy.array import \
        mul_operation, div_operation, add_operation, sub_operation
from pypy.module.micronumpy.array import copy_operation

from pypy.module.micronumpy.dtype import unwrap_int, coerce_int
from pypy.module.micronumpy.dtype import unwrap_float, coerce_float
from pypy.module.micronumpy.dtype import\
                            unwrap_float32, coerce_float32, float32
from pypy.module.micronumpy.dtype import result_mapping, iterable_type

#TODO: merge unwrap_spec decorator
# from pypy.interpreter.gateway import unwrap_spec


class BaseSingleDimArray(BaseNumArray): pass

def descr_dtype(space, self):
    return self.dtype

def descr_shape(space, self):
    return space.newtuple([space.wrap(self.len())])

def create_sdarray(data_type, unwrap, coerce):
    class SingleDimIterator(Wrappable):
        def __init__(self, space, array, i):
            self.space = space
            self.array = array
            self.i = i

        def descr_iter(self):
            space = self.space
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

    def create_client_math_operation(f):
        def scalar_operation(self, source, x):
            for i in range(len(source.storage)):
                self.storage[i] = data_type(f(source.storage[i], x))

        def fixedview_operation(self, source1, source2):
            for i in range(self.len()):
                self.storage[i] = \
                    data_type(f(source1.storage[i], source2.storage[i]))
        return scalar_operation, fixedview_operation

    def create_math_operation(f):
        opname = f.__name__
        def math_operation(self, w_x):
            space = self.space
            try:
                space.iter(w_x)
            except OperationError, e:
                if not e.match(space, space.w_TypeError):
                    raise
                result_t = result_mapping(space,
                                            (space.type(w_x), self.dtype))
                op2 = coerce(space, w_x)
                result = sdresult(space, result_t)(
                                                space, self.len(), result_t
                                                )
                operation = result.__class__.client_scalar[opname]
            else:
                lop = space.int_w(space.len(w_x))
                if lop != self.len():
                    raise OperationError(space.w_ValueError,
                            space.wrap("shape mismatch: objects cannot be"
                                " broadcast to the same shape"))
                dtype = iterable_type(space, w_x)
                result_t = result_mapping(space, (dtype, self.dtype))
                op2 = sdresult(space, dtype)(space, lop, dtype)
                op2.load_iterable(w_x)
                result = sdresult(space, result_t)(
                                                space, self.len(), result_t
                                                )
                operation = result.__class__.client_fixedview[opname]

            operation(result, self, op2)

            w_result = space.wrap(result)
            return w_result
        math_operation.unwrap_spec = ['self', W_Root]
        return math_operation


    class NumArray(BaseSingleDimArray):
        def __init__(self, space, length, dtype):
            self.shape = (length,)
            self.space = space
            self.storage = [data_type(0.0)] * length
            self.dtype = dtype
            make_sure_not_resized(self.storage)

        
        client_scalar = {}
        client_fixedview = {}

        client_scalar['mul'], client_fixedview['mul'] = \
                                            create_client_math_operation(mul)
        client_scalar['div'], client_fixedview['div'] = \
                                            create_client_math_operation(div)
        client_scalar['add'], client_fixedview['add'] = \
                                            create_client_math_operation(add)
        client_scalar['sub'], client_fixedview['sub'] = \
                                            create_client_math_operation(sub)


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
            return self.space.wrap(SingleDimIterator(self.space, self, 0))
        descr_iter.unwrap_spec = ['self']

        def descr_getitem(self, w_index):
            space = self.space
            if space.is_true(space.isinstance(w_index, space.w_slice)):
                start, stop, step, slen = w_index.indices4(space, self.len())
                res = sdresult(space, self.dtype)(space, slen, self.dtype)
                if step == 1:
                    res.storage[:] = self.storage[start:stop]
                else:
                    for i in range(slen):
                        res.storage[i] = self.storage[start]
                        start += step
                return space.wrap(res)
            else:
                try:
                    index = space.int_w(w_index)
                except TypeError, e:
                    raise OperationError(space.w_IndexError,
                                        space.wrap('Wrong index'))
            try:
                return space.wrap(self.storage[index])
            except IndexError:
                raise OperationError(space.w_IndexError,
                                     space.wrap("list index out of range"))
        descr_getitem.unwrap_spec = ['self', W_Root]

        def descr_setitem(self, w_index, w_value):
            space = self.space
            if space.is_true(space.isinstance(w_index, space.w_slice)):
                start, stop, step, slen = w_index.indices4(space, self.len())
                try:
                    space.iter(w_value)
                except OperationError, e:
                    if not e.match(space, space.w_TypeError):
                        raise
                    if not slen:
                        return
                    value = coerce(space, w_value)
                    if step == 1:
                        self.storage[start:stop] = [value]*slen
                    else:
                        for i in range(start, stop, step):
                            self.storage[i] = value
                    return
                lop = space.int_w(space.len(w_value))
                if lop != slen:
                    raise OperationError(space.w_TypeError,
                                                space.wrap('shape mismatch'))
                value = space.fixedview(w_value)
                if step == 1:
                    self.storage[start:stop] = \
                                [coerce(space, w_value) for w_value in value]
                else:
                    for i in range(slen):
                        self.storage[start] = coerce(space, value[i])
                        start += step
                return
            else:
                try:
                    index = space.int_w(w_index)
                except TypeError, e:
                    raise OperationError(space.w_IndexError,
                                                    space.wrap('Wrong index'))
            try:
                self.storage[index] = coerce(space, w_value)
            except IndexError:
                raise OperationError(space.w_IndexError,
                                     space.wrap("list index out of range"))
            return space.w_None
        descr_setitem.unwrap_spec = ['self', W_Root, W_Root]

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
            #beautiful, as in numpy
            strs=[str(x) for x in self.storage]
            maxlen=max([len(x) for x in strs])
            return space.wrap(
                    "[%s]" % ' '.join(["%-*s"%(maxlen, s) for s in strs]) 
                    )
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
                               __rmul__ = interp2app(NumArray.descr_mul),
                               __rdiv__ = interp2app(NumArray.descr_div),
                               __radd__ = interp2app(NumArray.descr_add),
                               __rsub__ = interp2app(NumArray.descr_sub),
                               __getitem__ = interp2app(NumArray.descr_getitem),
                               __setitem__ = interp2app(NumArray.descr_setitem),
                               __len__ = interp2app(NumArray.descr_len),
                               __str__ = interp2app(NumArray.descr_str),
                               __repr__ = interp2app(NumArray.descr_repr),
                               dtype = GetSetProperty(descr_dtype,
                                                            cls = NumArray),
                               shape = GetSetProperty(descr_shape,
                                                            cls = NumArray),
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
