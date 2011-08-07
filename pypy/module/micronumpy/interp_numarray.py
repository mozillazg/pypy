from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.module.micronumpy.interp_dtype import Dtype, Float64_num, Int32_num, Float64_dtype, get_dtype, find_scalar_dtype, find_result_dtype, _dtype_list
from pypy.module.micronumpy.interp_support import Signature
from pypy.module.micronumpy import interp_ufuncs
from pypy.objspace.std.floatobject import float2string as float2string_orig
from pypy.rlib import jit
from pypy.rlib.rfloat import DTSF_STR_PRECISION
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.tool.sourcetools import func_with_new_name
import math

TPs = (lltype.Array(lltype.Bool, hints={'nolength': True}), # bool
       lltype.Array(rffi.SIGNEDCHAR, hints={'nolength': True}), # int8
       lltype.Array(rffi.UCHAR, hints={'nolength': True}), # uint8
       lltype.Array(rffi.SHORT, hints={'nolength': True}), # int16
       lltype.Array(rffi.USHORT, hints={'nolength': True}), # uint16
       lltype.Array(rffi.INT, hints={'nolength': True}), #int32
       lltype.Array(rffi.UINT, hints={'nolength': True}), # uint32
       lltype.Array(rffi.LONG, hints={'nolength': True}), # long
       lltype.Array(rffi.ULONG, hints={'nolength': True}), # ulong
       lltype.Array(rffi.LONGLONG, hints={'nolength': True}), # int64
       lltype.Array(rffi.ULONGLONG, hints={'nolength': True}), # uint64
       lltype.Array(lltype.SingleFloat, hints={'nolength': True}), # float32
       lltype.Array(lltype.Float, hints={'nolength': True}), # float64
       lltype.Array(lltype.LongFloat, hints={'nolength': True}), # float96
)

numpy_driver = jit.JitDriver(greens = ['signature'],
                             reds = ['result_size', 'i', 'self', 'result'])
all_driver = jit.JitDriver(greens=['signature'], reds=['i', 'size', 'self'])
any_driver = jit.JitDriver(greens=['signature'], reds=['i', 'size', 'self'])
slice_driver1 = jit.JitDriver(greens=['signature'], reds=['i', 'j', 'step', 'stop', 'source', 'dest'])
slice_driver2 = jit.JitDriver(greens=['signature'], reds=['i', 'j', 'step', 'stop', 'source', 'dest'])

def add(v1, v2):
    return v1 + v2
def mul(v1, v2):
    return v1 * v2
def maximum(v1, v2):
    return max(v1, v2)
def minimum(v1, v2):
    return min(v1, v2)

def float2string(x):
    return float2string_orig(x, 'g', DTSF_STR_PRECISION)

class BaseArray(Wrappable):
    def __init__(self):
        self.invalidates = []

    def invalidated(self):
        if self.invalidates:
            self._invalidated()

    def _invalidated(self):
        for arr in self.invalidates:
            arr.force_if_needed()
        del self.invalidates[:]

    def _unaryop_impl(w_ufunc):
        def impl(self, space):
            return w_ufunc(space, self)
        return func_with_new_name(impl, "unaryop_%s_impl" % w_ufunc.__name__)

    descr_pos = _unaryop_impl(interp_ufuncs.positive)
    descr_neg = _unaryop_impl(interp_ufuncs.negative)
    descr_abs = _unaryop_impl(interp_ufuncs.absolute)

    def _binop_impl(w_ufunc):
        def impl(self, space, w_other):
            return w_ufunc(space, self, w_other)
        return func_with_new_name(impl, "binop_%s_impl" % w_ufunc.__name__)

    descr_add = _binop_impl(interp_ufuncs.add)
    descr_sub = _binop_impl(interp_ufuncs.subtract)
    descr_mul = _binop_impl(interp_ufuncs.multiply)
    descr_div = _binop_impl(interp_ufuncs.divide)
    descr_pow = _binop_impl(interp_ufuncs.power)
    descr_mod = _binop_impl(interp_ufuncs.mod)

    def _binop_right_impl(w_ufunc):
        def impl(self, space, w_other):
            w_other = wrap_scalar(space, w_other, self.dtype)
            return w_ufunc(space, w_other, self)
        return func_with_new_name(impl, "binop_right_%s_impl" % w_ufunc.__name__)

    descr_radd = _binop_right_impl(interp_ufuncs.add)
    descr_rsub = _binop_right_impl(interp_ufuncs.subtract)
    descr_rmul = _binop_right_impl(interp_ufuncs.multiply)
    descr_rdiv = _binop_right_impl(interp_ufuncs.divide)
    descr_rpow = _binop_right_impl(interp_ufuncs.power)
    descr_rmod = _binop_right_impl(interp_ufuncs.mod)

    def _reduce_sum_prod_impl(function, init):
        reduce_driver = jit.JitDriver(greens=['signature'],
                         reds = ['i', 'size', 'self', 'result'])

        def loop(self, result, size):
            i = 0
            while i < size:
                reduce_driver.jit_merge_point(signature=self.signature,
                                              self=self, size=size, i=i,
                                              result=result)
                result = function(result, self.eval(i))
                i += 1
            return result

        def impl(self, space):
            return space.wrap(loop(self, init, self.find_size()))
        return func_with_new_name(impl, "reduce_%s_impl" % function.__name__)

    def _reduce_max_min_impl(function):
        reduce_driver = jit.JitDriver(greens=['signature'],
                         reds = ['i', 'size', 'self', 'result'])
        def loop(self, result, size):
            i = 1
            while i < size:
                reduce_driver.jit_merge_point(signature=self.signature,
                                              self=self, size=size, i=i,
                                              result=result)
                result = function(result, self.eval(i))
                i += 1
            return result

        def impl(self, space):
            size = self.find_size()
            if size == 0:
                raise OperationError(space.w_ValueError,
                    space.wrap("Can't call %s on zero-size arrays" \
                            % function.__name__))
            return space.wrap(loop(self, self.eval(0), size))
        return func_with_new_name(impl, "reduce_%s_impl" % function.__name__)

    def _reduce_argmax_argmin_impl(function):
        reduce_driver = jit.JitDriver(greens=['signature'],
                         reds = ['i', 'size', 'result', 'self', 'cur_best'])
        def loop(self, size):
            result = 0
            cur_best = self.eval(0)
            i = 1
            while i < size:
                reduce_driver.jit_merge_point(signature=self.signature,
                                              self=self, size=size, i=i,
                                              result=result, cur_best=cur_best)
                new_best = function(cur_best, self.eval(i))
                if new_best != cur_best:
                    result = i
                    cur_best = new_best
                i += 1
            return result
        def impl(self, space):
            size = self.find_size()
            if size == 0:
                raise OperationError(space.w_ValueError,
                    space.wrap("Can't call %s on zero-size arrays" \
                            % function.__name__))
            return space.wrap(loop(self, size))
        return func_with_new_name(impl, "reduce_arg%s_impl" % function.__name__)

    def _all(self):
        size = self.find_size()
        i = 0
        while i < size:
            all_driver.jit_merge_point(signature=self.signature, self=self, size=size, i=i)
            if not self.eval(i):
                return False
            i += 1
        return True
    def descr_all(self, space):
        return space.wrap(self._all())

    def _any(self):
        size = self.find_size()
        i = 0
        while i < size:
            any_driver.jit_merge_point(signature=self.signature, self=self, size=size, i=i)
            if self.eval(i):
                return True
            i += 1
        return False
    def descr_any(self, space):
        return space.wrap(self._any())

#    descr_sum = _reduce_sum_prod_impl(add, 0.0)
#    descr_prod = _reduce_sum_prod_impl(mul, 1.0)
#    descr_max = _reduce_max_min_impl(maximum)
#    descr_min = _reduce_max_min_impl(minimum)
#    descr_argmax = _reduce_argmax_argmin_impl(maximum)
#    descr_argmin = _reduce_argmax_argmin_impl(minimum)

    def descr_dot(self, space, w_other):
        if isinstance(w_other, BaseArray):
            w_res = self.descr_mul(space, w_other)
            assert isinstance(w_res, BaseArray)
            return w_res.descr_sum(space)
        else:
            return self.descr_mul(space, w_other)

    def _getnums(self, comma):
        #d = self.find_dtype()
        #kind = d.kind
        #if kind == 'f':
        format_func = float2string
        #else:
        #    format_func = str
        if self.find_size() > 1000:
            nums = [
                format_func(self.eval(index))
                for index in range(3)
            ]
            nums.append("..." + "," * comma)
            nums.extend([
                format_func(self.eval(index))
                for index in range(self.find_size() - 3, self.find_size())
            ])
        else:
            nums = [
                format_func(self.eval(index))
                for index in range(self.find_size())
            ]
        return nums

    def get_concrete(self):
        raise NotImplementedError

    def descr_copy(self, space):
        return new_numarray(space, self, self.dtype)

    def descr_get_dtype(self, space):
        return space.wrap(self.find_dtype())

    def descr_get_shape(self, space):
        return space.newtuple([self.descr_len(space)])

    def descr_len(self, space):
        return self.get_concrete().descr_len(space)

    def descr_repr(self, space):
        # Simple implementation so that we can see the array. Needs work.
        concrete = self.get_concrete()
        return space.wrap("array([" + ", ".join(concrete._getnums(False)) + "])")

    def descr_str(self, space):
        # Simple implementation so that we can see the array. Needs work.
        concrete = self.get_concrete()
        return space.wrap("[" + " ".join(concrete._getnums(True)) + "]")

    def descr_getitem(self, space, w_idx):
        # TODO: indexing by tuples
        start, stop, step, slice_length = space.decode_index4(w_idx, self.find_size())
        if step == 0:
            # Single index
            return space.wrap(self.get_concrete().eval(start))
        else:
            # Slice
            res = SingleDimSlice(start, stop, step, slice_length, self, self.signature.transition(SingleDimSlice.static_signature))
            return space.wrap(res)

    def descr_setitem(self, space, w_idx, w_value):
        # TODO: indexing by tuples and lists
        self.invalidated()
        start, stop, step, slice_length = space.decode_index4(w_idx,
                                                              self.find_size())
        if step == 0:
            # Single index
            self.get_concrete().setitem(start, space.float_w(w_value))
        else:
            concrete = self.get_concrete()
            if isinstance(w_value, BaseArray):
                # for now we just copy if setting part of an array from 
                # part of itself. can be improved.
                if (concrete.get_root_storage() ==
                    w_value.get_concrete().get_root_storage()):
                    w_value = new_numarray(space, w_value, self.dtype)
            else:
                w_value = convert_to_array(space, w_value)
            concrete.setslice(space, start, stop, step, 
                                               slice_length, w_value)

    def descr_mean(self, space):
        return space.wrap(space.float_w(self.descr_sum(space))/self.find_size())

    def _sliceloop1(self, start, stop, step, source, dest):
        i = start
        j = 0
        while i < stop:
            slice_driver1.jit_merge_point(signature=source.signature,
                    step=step, stop=stop, i=i, j=j, source=source,
                    dest=dest)
            dest.storage[i] = source.eval(j)
            j += 1
            i += step

    def _sliceloop2(self, start, stop, step, source, dest):
        i = start
        j = 0
        while i > stop:
            slice_driver2.jit_merge_point(signature=source.signature,
                    step=step, stop=stop, i=i, j=j, source=source,
                    dest=dest)
            dest.storage[i] = source.eval(j)
            j += 1
            i += step

def convert_to_array (space, w_obj):
    if isinstance(w_obj, BaseArray):
        return w_obj
    elif space.issequence_w(w_obj):
        # Convert to array.
        # XXX: Need to fill in the dtype
        return new_numarray(space, w_obj, Float64_dtype)
    else:
        # If it's a scalar
        return wrap_scalar(space, w_obj)

def wrap_scalar(space, scalar, dtype=None):
    if dtype is None:
        dtype = find_scalar_dtype(space, scalar)
    return ScalarWrapper(dtype.unwrap(space, scalar), dtype)

class ScalarWrapper(BaseArray):
    """
    Intermediate class representing a float literal.
    """
    _immutable_fields_ = ["value"]
    signature = Signature()

    def __init__(self, value, dtype):
        BaseArray.__init__(self)
        self.value = value
        self.dtype = dtype

    def find_size(self):
        raise ValueError

    def eval(self, i):
        return self.value

    def find_dtype(self):
        return self.dtype

# this is really only to simplify the tests. Maybe it should be moved?
class FloatWrapper(ScalarWrapper):
    def __init__(self, value):
        ScalarWrapper.__init__(self, value, Float64_dtype)

class VirtualArray(BaseArray):
    """
    Class for representing virtual arrays, such as binary ops or ufuncs
    """
    def __init__(self, signature):
        BaseArray.__init__(self)
        self.forced_result = None
        self.signature = signature

    def _del_sources(self):
        # Function for deleting references to source arrays, to allow garbage-collecting them
        raise NotImplementedError

    def compute(self):
        i = 0
        signature = self.signature
        result_size = self.find_size()
        result = create_sdarray(result_size, self.dtype)
        while i < result_size:
            numpy_driver.jit_merge_point(signature=signature,
                                         result_size=result_size, i=i,
                                         self=self, result=result)
            result.storage[i] = self.eval(i)
            i += 1
        return result

    def force_if_needed(self):
        if self.forced_result is None:
            self.forced_result = self.compute()
            self._del_sources()

    def get_concrete(self):
        self.force_if_needed()
        return self.forced_result

    def eval(self, i):
        if self.forced_result is not None:
            return self.forced_result.eval(i)
        return self._eval(i)

    def find_size(self):
        if self.forced_result is not None:
            # The result has been computed and sources may be unavailable
            return self.forced_result.find_size()
        return self._find_size()

    def find_dtype(self):
        return self.dtype

class Call1(VirtualArray):
    _immutable_fields_ = ["function", "values"]

    def __init__(self, function, values, signature):
        VirtualArray.__init__(self, signature)
        self.function = function
        self.values = values
        self.dtype = self.values.find_dtype()

    def _del_sources(self):
        self.values = None

    def _find_size(self):
        return self.values.find_size()

    def _eval(self, i):
        return self.function(self.values.eval(i))

class Call2(VirtualArray):
    """
    Intermediate class for performing binary operations.
    """
    _immutable_fields_ = ["function", "left", "right"]

    def __init__(self, function, left, right, signature):
        VirtualArray.__init__(self, signature)
        self.left = left
        self.right = right
        dtype = self.left.find_dtype()
        dtype2 = self.right.find_dtype()
        if dtype.num != dtype2.num:
            newdtype = find_result_dtype(dtype, dtype2)
            cast = newdtype.cast
            if dtype.num != newdtype.num:
                if dtype2.num != newdtype.num:
                    self.function = lambda x, y: function(cast(x), cast(y))
                else:
                    self.function = lambda x, y: function(cast(x), y)
            else:
                self.function = lambda x, y: function(x, cast(y))
            self.dtype = newdtype
        else:
            self.dtype = dtype
            self.function = function

    def _del_sources(self):
        self.left = None
        self.right = None

    def _find_size(self):
        try:
            return self.left.find_size()
        except:
            return self.right.find_size()

    def _eval(self, i):
        lhs, rhs = self.left.eval(i), self.right.eval(i)
        return self.function(lhs, rhs)

class ViewArray(BaseArray):
    """
    Class for representing views of arrays, they will reflect changes of parent
    arrays. Example: slices
    """
    _immutable_fields_ = ["parent"]

    def __init__(self, parent, signature):
        BaseArray.__init__(self)
        self.signature = signature
        self.parent = parent
        self.dtype = parent.dtype
        self.invalidates = parent.invalidates

    def get_concrete(self):
        # in fact, ViewArray never gets "concrete" as it never stores data.
        # This implementation is needed for BaseArray getitem/setitem to work,
        # can be refactored.
        self.parent.get_concrete()
        return self

    def eval(self, i):
        return self.parent.eval(self.calc_index(i))

    @unwrap_spec(item=int, value=float)
    def setitem(self, item, value):
        return self.parent.setitem(self.calc_index(item), value)

    def descr_len(self, space):
        return space.wrap(self.find_size())

    def calc_index(self, item):
        raise NotImplementedError

    def find_dtype(self):
        return self.dtype

class SingleDimSlice(ViewArray):
    _immutable_fields_ = ["start", "stop", "step", "size"]
    static_signature = Signature()

    def __init__(self, start, stop, step, slice_length, parent, signature):
        ViewArray.__init__(self, parent, signature)
        if isinstance(parent, SingleDimSlice):
            self.start = parent.calc_index(start)
            self.stop = parent.calc_index(stop)
            self.step = parent.step * step
            self.parent = parent.parent
        else:
            self.start = start
            self.stop = stop
            self.step = step
            self.parent = parent
        self.size = slice_length

    def get_root_storage(self):
        return self.parent.storage

    def find_size(self):
        return self.size

    def setslice(self, space, start, stop, step, slice_length, arr):
        start = self.calc_index(start)
        if stop != -1:
            stop = self.calc_index(stop)
        step = self.step * step
        if step > 0:
            self._sliceloop1(start, stop, step, arr, self.parent)
        else:
            self._sliceloop2(start, stop, step, arr, self.parent)

    def calc_index(self, item):
        return (self.start + item * self.step)

class SingleDimArray(BaseArray):
    signature = Signature()

    def __init__(self):
        BaseArray.__init__(self)

    def get_concrete(self):
        return self

    def find_size(self):
        return self.size

    def descr_len(self, space):
        return space.wrap(self.size)

    def setslice(self, space, start, stop, step, slice_length, arr):
        if step > 0:
            self._sliceloop1(start, stop, step, arr, self)
        else:
            self._sliceloop2(start, stop, step, arr, self)

def make_class(num):
    TP = TPs[num]
    class TypedSingleDimArray(SingleDimArray):
        def __init__(self, size, dtype):
            SingleDimArray.__init__(self)
            self.size = size
            self.dtype = dtype
            self.storage = lltype.malloc(TP, size, zero=True,
                                     flavor='raw', track_allocation=False,
                                     add_memory_pressure=True)
            # XXX find out why test_zjit explodes with trackign of allocations

        def get_root_storage(self):
            return self.storage

        def eval(self, i):
            return self.storage[i]

        def setitem(self, item, value):
            self.invalidated()
            self.storage[item] = value

        def find_dtype(self):
            return self.dtype

        def __del__(self):
            lltype.free(self.storage, flavor='raw', track_allocation=False)

    TypedSingleDimArray.__name__ = 'SingleDimArray' + str(num)
    return TypedSingleDimArray

_array_classes = tuple(make_class(i) for i in xrange(14))

def create_sdarray(L, dtype):
    return _array_classes[dtype.num](L, dtype)

def new_numarray(space, iterable, dtype):
    l = space.listview(iterable)
    dtype = get_dtype(space, dtype)
    arr = create_sdarray(len(l), dtype)
    i = 0
    unwrap = dtype.unwrap
    cast = dtype.cast
    for w_elem in l:
        arr.storage[i] = cast(unwrap(space, w_elem))
        i += 1
    return arr

def descr_new_numarray(space, w_type, __args__):
    # this isn't such a great check. We should improve it including exceptions.
    # Also needs to be able to handle keywords better
    iterable = __args__.arguments_w[0]
    if len(__args__.arguments_w) == 2:
        dtype = __args__.arguments_w[1]
    elif __args__.keywords:
        if __args__.keywords[0] == 'dtype':
            dtype = __args__.keywords_w[0]
        else:
            msg = "array() got unexpected keyword argument"
            raise OperationError(space.w_TypeError, space.wrap(msg))
    else:
        # can just use the dtype for float for now. We need to actually be
        # able to determine the base dtype of an iterable
        dtype = space.wrap('d')
    return space.wrap(new_numarray(space, iterable, dtype))

@unwrap_spec(size=int)
def zeros(space, size):
    return space.wrap(create_sdarray(size, Float64_dtype))

@unwrap_spec(size=int)
def ones(space, size):
    arr = create_sdarray(size, Float64_dtype)
    for i in xrange(size):
        arr.storage[i] = 1.0
    return space.wrap(arr)

BaseArray.typedef = TypeDef(
    'numarray',
    __new__ = interp2app(descr_new_numarray),

    copy = interp2app(BaseArray.descr_copy),
    shape = GetSetProperty(BaseArray.descr_get_shape),
    dtype = GetSetProperty(BaseArray.descr_get_dtype),

    __len__ = interp2app(BaseArray.descr_len),
    __getitem__ = interp2app(BaseArray.descr_getitem),
    __setitem__ = interp2app(BaseArray.descr_setitem),

    __pos__ = interp2app(BaseArray.descr_pos),
    __neg__ = interp2app(BaseArray.descr_neg),
    __abs__ = interp2app(BaseArray.descr_abs),
    __add__ = interp2app(BaseArray.descr_add),
    __sub__ = interp2app(BaseArray.descr_sub),
    __mul__ = interp2app(BaseArray.descr_mul),
    __div__ = interp2app(BaseArray.descr_div),
    __pow__ = interp2app(BaseArray.descr_pow),
    __mod__ = interp2app(BaseArray.descr_mod),
    __radd__ = interp2app(BaseArray.descr_radd),
    __rsub__ = interp2app(BaseArray.descr_rsub),
    __rmul__ = interp2app(BaseArray.descr_rmul),
    __rdiv__ = interp2app(BaseArray.descr_rdiv),
    __rpow__ = interp2app(BaseArray.descr_rpow),
    __rmod__ = interp2app(BaseArray.descr_rmod),
    __repr__ = interp2app(BaseArray.descr_repr),
    __str__ = interp2app(BaseArray.descr_str),

#    mean = interp2app(BaseArray.descr_mean),
#    sum = interp2app(BaseArray.descr_sum),
#    prod = interp2app(BaseArray.descr_prod),
#    max = interp2app(BaseArray.descr_max),
#    min = interp2app(BaseArray.descr_min),
#    argmax = interp2app(BaseArray.descr_argmax),
#    argmin = interp2app(BaseArray.descr_argmin),
#    all = interp2app(BaseArray.descr_all),
#    any = interp2app(BaseArray.descr_any),
#    dot = interp2app(BaseArray.descr_dot),
)
