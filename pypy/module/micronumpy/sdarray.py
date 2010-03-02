from pypy.interpreter.baseobjspace import W_Root, Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.interpreter.gateway import interp2app
from pypy.rlib.debug import make_sure_not_resized

from pypy.module.micronumpy.array import BaseNumArray
from pypy.module.micronumpy.array import base_typedef
from pypy.module.micronumpy.array import \
        mul_operation, div_operation, add_operation, sub_operation

from pypy.module.micronumpy.dtype import unwrap_int, coerce_int
from pypy.module.micronumpy.dtype import unwrap_float, coerce_float
from pypy.module.micronumpy.dtype import\
                            unwrap_float32, coerce_float32, float32
from pypy.module.micronumpy.dtype import result_mapping, iterable_type

from pypy.module.micronumpy.dtype import create_factory

from pypy.module.micronumpy.dtype import get_dtype
from pypy.module.micronumpy.dtype import retrieve_dtype #FIXME: ambiguously named?
from pypy.module.micronumpy.dtype import DynamicType

#TODO: merge unwrap_spec decorator
# from pypy.interpreter.gateway import unwrap_spec

class BaseSingleDimArray(BaseNumArray): pass

def descr_dtype(space, self):
    return space.wrap(self.dtype)

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

    def create_client_math_operation(f):
        def scalar_operation(self, source, x):
            for i in range(len(source.storage)):
                self.storage[i] = f(source.storage[i], x)

        def fixedview_operation(self, a, b):
            for i in range(self.len()):
                self.storage[i] = f(a.storage[i], b.storage[i])
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
                x = coerce(space, w_x)
                result = sdresult(result_t)(space,
                                            self.len(), retrieve_dtype(space, result_t)
                                           )
                client_scalar[opname](result, self, x)
            else:
                operand_length = space.int_w(space.len(w_x))
                if operand_length != self.len():
                    raise OperationError(space.w_ValueError,
                            space.wrap("shape mismatch: objects cannot be"
                                       " broadcast to the same shape"))
                dtype_w = retrieve_dtype(space, iterable_type(space, w_x))
                result_t = result_mapping(space, (dtype_w, self.dtype))
                xs = sdresult(dtype_w.code)(space, operand_length, dtype_w)
                xs.load_iterable(w_x)
                result = sdresult(result_t)(
                                            space, self.len(), retrieve_dtype(space, result_t)
                                           )
                client_fixedview[opname](result, self, xs)

            return space.wrap(result)
        math_operation.unwrap_spec = ['self', W_Root]
        math_operation.__name__ = "%s_descr_%s" % (str(data_type), opname)
        return math_operation

    client_scalar = {}
    client_fixedview = {}

    mul = mul_operation()
    client_scalar['mul'], client_fixedview['mul'] = \
                                        create_client_math_operation(mul)
    div = div_operation()
    client_scalar['div'], client_fixedview['div'] = \
                                        create_client_math_operation(div)
    add = add_operation()
    client_scalar['add'], client_fixedview['add'] = \
                                        create_client_math_operation(add)
    sub = sub_operation()
    client_scalar['sub'], client_fixedview['sub'] = \
                                        create_client_math_operation(sub)

    class NumArray(BaseSingleDimArray):
        def __init__(self, space, length, dtype):
            self.shape = (length,)
            self.space = space
            self.storage = [data_type(0.0)] * length
            assert isinstance(dtype, DynamicType)
            self.dtype = dtype
            make_sure_not_resized(self.storage)

        descr_mul = create_math_operation(mul)
        descr_div = create_math_operation(div)
        descr_add = create_math_operation(add)
        descr_sub = create_math_operation(sub)

        def load_iterable(self, w_values):
            space = self.space
            i = 0
            for x in space.fixedview(w_values, self.len()):
                try:
                    space.iter(x)
                except OperationError, e:
                    if not e.match(space, space.w_TypeError):
                        raise
                else:
                    raise OperationError(space.w_ValueError,
                                           space.wrap('shape mismatch'))

                self.storage[i] = coerce(space, x)
                i += 1

        def descr_iter(self):
            return self.space.wrap(SingleDimIterator(self.space, self, 0))
        descr_iter.unwrap_spec = ['self']

        def descr_getitem(self, w_index):
            space = self.space
            if space.is_true(space.isinstance(w_index, space.w_slice)):
                start, stop, step, slen = w_index.indices4(space, self.len())
                res = sdresult(self.dtype.code)(space, slen, self.dtype)
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

sdresult = create_factory({'i': IntArray, 'd': FloatArray})
