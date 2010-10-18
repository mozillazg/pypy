from pypy.interpreter.baseobjspace import W_Root, Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.interpreter.gateway import interp2app
from pypy.rlib.debug import make_sure_not_resized

from pypy.objspace.std.sliceobject import W_SliceObject
from pypy.objspace.std.tupleobject import W_TupleObject

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

    def operation_name(type, operand_type, opname):
        return '_'.join([type, operand_type, opname])

    def fixedview_operation(opname, self, source, x):
        return getattr(self, operation_name('client', 'fixedview', opname))(source, x)

    def client_operation(opname, self, source, x):
        return getattr(self, operation_name('client', 'scalar', opname))(source, x)

    def create_client_math_operation(f):
        def scalar_operation(self, source, x, inverse):
            for i in range(len(source.storage)):
                y = source.storage[i]
                self.storage[i] = f(x, y) if inverse else f(y, x)

        def fixedview_operation(self, source1, source2, inverse):
            for i in range(self.len()):
                a = source1.storage[i]
                b = source2.storage[i]
                self.storage[i] = f(b, a) if inverse else f(a, b)
        return scalar_operation, fixedview_operation

    def create_math_operation(f):
        opname = f.__name__
        def common_math_operation(self, w_x, reversed):
            space = self.space
            try:
                space.iter(w_x)
            except OperationError, e:
                if not e.match(space, space.w_TypeError):
                    raise
                result_t = result_mapping(space,
                                          (space.type(w_x), self.dtype))
                x = coerce(space, w_x)
                result = sdresult(result_t)(space, self.len(),
                                            retrieve_dtype(space, result_t))
                operation = result.__class__.client_scalar[opname]
            else:
                operand_length = space.int_w(space.len(w_x))
                if operand_length != self.len():
                    raise OperationError(space.w_ValueError,
                            space.wrap("shape mismatch: objects cannot be"
                                       " broadcast to the same shape"))
                dtype_w = retrieve_dtype(space, iterable_type(space, w_x))
                result_t = result_mapping(space, (dtype_w, self.dtype))
                xs = sdresult(result_t)(space, operand_length, 
                                        retrieve_dtype(space, result_t))
                xs.load_iterable(w_x)
                result = sdresult(result_t)(space, self.len(),
                                            retrieve_dtype(space, result_t))
                x = xs
                operation = result.__class__.client_fixedview[opname]

            operation(result, self, x, reversed)

            return space.wrap(result)

        def math_operation(self, w_x):
            return common_math_operation(self, w_x, False)
        math_operation.unwrap_spec = ['self', W_Root]
        math_operation.__name__ = "%s_descr_%s" % (str(data_type), opname)

        def reversed_math_operation(self, w_x):
            return common_math_operation(self, w_x, True)
        reversed_math_operation.unwrap_spec = ['self', W_Root]
        reversed_math_operation.__name__ = "%s_descr_r%s" % (str(data_type), opname)

        return math_operation, reversed_math_operation



    class NumArray(BaseSingleDimArray):
        def __init__(self, space, length, dtype):
            self.shape = (length,)
            self.space = space
            self.storage = [data_type(0.0)] * length
            assert isinstance(dtype, DynamicType)
            self.dtype = dtype
            make_sure_not_resized(self.storage)

        # Since we can't pass dtype to client_*,
        # we must always use ones for *client* dtype, e.g. bound to his class.

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
        descr_mul, descr_rmul = create_math_operation(mul)
        descr_div, descr_rdiv = create_math_operation(div)
        descr_add, descr_radd = create_math_operation(add)
        descr_sub, descr_rsub = create_math_operation(sub)

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
                assert isinstance(w_index, W_SliceObject)
                start, stop, step, slen = w_index.indices4(space, self.len())
                res = NumArray(space, slen, self.dtype)
                if step == 1:
                    res.storage[:] = self.storage[start:stop]
                else:
                    for i in range(slen):
                        res.storage[i] = self.storage[start]
                        start += step
                return space.wrap(res)
            elif space.is_w(w_index, space.w_Ellipsis):
                res = NumArray(space, self.shape[0], self.dtype)
                res.storage[:] = self.storage
                return space.wrap(res)
            else:
                try:
                    index = space.int_w(w_index)
                except OperationError, e:
                    if not e.match(space, space.w_TypeError):
                        raise
                    if isinstance(w_index, W_TupleObject):
                        raise OperationError(space.w_NotImplementedError,
                                space.wrap('multi-indexing single-dimension'
                                           ' arrays are not implemented yet'))
                    raise OperationError(space.w_IndexError,
                                        space.wrap("index must either be an int or a sequence"))
            try:
                return space.wrap(self.storage[index])
            except IndexError:
                raise OperationError(space.w_IndexError,
                                     space.wrap("list index out of range"))
        descr_getitem.unwrap_spec = ['self', W_Root]

        def descr_setitem(self, w_index, w_value):
            space = self.space
            if isinstance(w_index, W_SliceObject):
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
                operand_length = space.int_w(space.len(w_value))
                if operand_length != slen:
                    raise OperationError(space.w_ValueError,
                                        space.wrap('array dimensions are not'
                                                   ' compatible for copy'))
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
                except OperationError, e:
                    if e.match(space, space.w_TypeError):
                        raise OperationError(space.w_ValueError,
                                             space.wrap("can't understand index")) #FIXME: more meaningful message based on type
                try:
                    self.storage[index] = coerce(space, w_value)
                except OperationError, e:
                    if e.match(space, space.w_TypeError):
                        raise OperationError(space.w_ValueError,
                                             space.wrap("can't understand value")) #FIXME: more meaningful message based on type
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
            strings = [str(x) for x in self.storage]
            maxlen = max([len(x) for x in strings])
            return strings, maxlen

        def descr_str(self, space):
            space = self.space
            #beautiful, as in numpy
            strings, maxlen = self.str()
            return space.wrap(
                    "[%s]" % ' '.join(["%-*s"%(maxlen, s) for s in strings]) 
                    )
        descr_str.unwrap_spec = ['self', ObjSpace]

        def descr_repr(self, space):
            space = self.space
            strings, maxlen = self.str()
            return space.wrap(
                    "array([%s])" % ', '.join(["%-*s"%(maxlen, s) for s in strings]) 
                    )
        descr_repr.unwrap_spec = ['self', ObjSpace]

    NumArray.typedef = TypeDef('ndarray', base_typedef,
                               __mul__ = interp2app(NumArray.descr_mul),
                               __div__ = interp2app(NumArray.descr_div),
                               __add__ = interp2app(NumArray.descr_add),
                               __sub__ = interp2app(NumArray.descr_sub),

                               __rmul__ = interp2app(NumArray.descr_rmul),
                               __rdiv__ = interp2app(NumArray.descr_rdiv),
                               __radd__ = interp2app(NumArray.descr_radd),
                               __rsub__ = interp2app(NumArray.descr_rsub),

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
