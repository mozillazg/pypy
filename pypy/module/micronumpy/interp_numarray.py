from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.module.cpyext.api import cpython_api, PyObject
from pypy.module.cpyext.longobject import PyLong_FromLongLong, PyLong_FromUnsignedLongLong
from pypy.module.micronumpy.interp_dtype import Dtype, Float64_num, Int32_num, Float64_dtype, get_dtype, find_scalar_dtype, find_result_dtype, _dtype_list
from pypy.module.micronumpy.interp_support import Signature
from pypy.module.micronumpy import interp_ufuncs
from pypy.objspace.std.floatobject import float2string as float2string_orig
from pypy.objspace.std.objspace import newlong
from pypy.rlib import jit
from pypy.rlib import rbigint
from pypy.rlib.objectmodel import specialize
from pypy.rlib.rarithmetic import LONG_BIT
from pypy.rlib.rfloat import DTSF_STR_PRECISION
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.tool.sourcetools import func_with_new_name
import math

numpy_driver = jit.JitDriver(greens = ['signature'],
                             reds = ['result_size', 'i', 'self', 'result'])
all_driver = jit.JitDriver(greens=['signature'], reds=['i', 'size', 'self'])
any_driver = jit.JitDriver(greens=['signature'], reds=['i', 'size', 'self'])
slice_driver1 = jit.JitDriver(greens=['signature','dtype'], reds=['i', 'j', 'step', 'stop', 'source', 'self'])
slice_driver2 = jit.JitDriver(greens=['signature','dtype'], reds=['i', 'j', 'step', 'stop', 'source', 'self'])

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

    def descr_pos(self, space):
        return self

    descr_neg = _unaryop_impl(interp_ufuncs.negative)
    #descr_abs = _unaryop_impl(interp_ufuncs.absolute)

    def _binop_impl(w_ufunc):
        def impl(self, space, w_other):
            return w_ufunc(space, self, w_other)
        return func_with_new_name(impl, "binop_%s_impl" % w_ufunc.__name__)

    #descr_add = _binop_impl(interp_ufuncs.add)
    #descr_sub = _binop_impl(interp_ufuncs.subtract)
    #descr_mul = _binop_impl(interp_ufuncs.multiply)
    #descr_div = _binop_impl(interp_ufuncs.divide)
    #descr_pow = _binop_impl(interp_ufuncs.power)
    #descr_mod = _binop_impl(interp_ufuncs.mod)

    #def _binop_right_impl(w_ufunc):
    #    def impl(self, space, w_other):
    #        w_other = wrap_scalar(space, w_other, self.dtype)
    #        return w_ufunc(space, w_other, self)
    #    return func_with_new_name(impl, "binop_right_%s_impl" % w_ufunc.__name__)

    """descr_radd = _binop_right_impl(interp_ufuncs.add)
    descr_rsub = _binop_right_impl(interp_ufuncs.subtract)
    descr_rmul = _binop_right_impl(interp_ufuncs.multiply)
    descr_rdiv = _binop_right_impl(interp_ufuncs.divide)
    descr_rpow = _binop_right_impl(interp_ufuncs.power)
    descr_rmod = _binop_right_impl(interp_ufuncs.mod)"""

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

    descr_sum = _reduce_sum_prod_impl(add, 0.0)
    descr_prod = _reduce_sum_prod_impl(mul, 1.0)
    descr_max = _reduce_max_min_impl(maximum)
    descr_min = _reduce_max_min_impl(minimum)
    descr_argmax = _reduce_argmax_argmin_impl(maximum)
    descr_argmin = _reduce_argmax_argmin_impl(minimum)

    def descr_dot(self, space, w_other):
        if isinstance(w_other, BaseArray):
            w_res = self.descr_mul(space, w_other)
            assert isinstance(w_res, BaseArray)
            return w_res.descr_sum(space)
        else:
            return self.descr_mul(space, w_other)

    def _getnums(self, comma):
        d = self.find_dtype()
        kind = d.kind
        if kind == 'f':
            format_func = float2string
        else:
            format_func = str
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
        return space.newtuple([self.descr_shape(space)])

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
            return self.get_concrete().getitem(space, start)
        else:
            raise OperationError(space.w_ValueError, space.wrap("No slices"))
            # Slice
            #res = SingleDimSlice(start, stop, step, slice_length, self, self.signature.transition(SingleDimSlice.static_signature))
            #return space.wrap(res)

    def descr_setitem(self, space, w_idx, w_value):
        # TODO: indexing by tuples and lists
        self.invalidated()
        start, stop, step, slice_length = space.decode_index4(w_idx,
                                                              self.find_size())
        if step == 0:
            # Single index
            self.get_concrete().setitem_w(space, start, w_value)
        else:
            #raise OperationError(space.w_ValueError, space.wrap("No slices"))
            concrete = self.get_concrete()
            #if isinstance(w_value, BaseArray):
                #for now we just copy if setting part of an array from 
                #part of itself. can be improved.
                #need to put in a function that checks all storages of 
                #w_value because it could be a Call2 class (binop)
            #    if (concrete.get_root_storage() ==
            #        w_value.get_concrete().get_root_storage()):
            #        w_value = new_numarray(space, w_value, self.dtype)
            #else:
            w_value = convert_to_array(space, w_value)
            concrete.setslice(start, stop, step, 
                                                slice_length, w_value)

    def descr_mean(self, space):
        return space.wrap(space.float_w(self.descr_sum(space))/self.find_size())

def convert_to_array (space, w_obj):
    if isinstance(w_obj, BaseArray):
        return w_obj
    elif space.issequence_w(w_obj):
        # Convert to array.
        # XXX: Need to fill in the dtype
        return new_numarray(space, w_obj, Float64_dtype)
    else:
        # If it's a scalar
        dtype = find_scalar_dtype(space, w_obj)
        return wrap_scalar(space, w_obj, dtype)

def make_scalarwrapper(_dtype):
    class ScalarWrapper(BaseArray):
        """
        Intermediate class representing a float literal.
        """
        _immutable_fields_ = ["value"]
        signature = Signature()

        def __init__(self, space, value):
            BaseArray.__init__(self)
            self.value = _dtype.valtype(_dtype.unwrap(space, value))
            self.dtype = _dtype

        def find_size(self):
            raise ValueError

        def eval(self, i):
            return self.value

        def find_dtype(self):
            return _dtype
    ScalarWrapper.__name__ = "ScalarWrapper_" + _dtype.name
    return ScalarWrapper

_scalarwrappers = [make_scalarwrapper(d) for d in _dtype_list]

def wrap_scalar(space, scalar, dtype):
    assert isinstance(dtype, Dtype)
    return _scalarwrappers[dtype.num](space, scalar)

# this is really only to simplify the tests. Maybe it should be moved?
FloatWrapper = _scalarwrappers[12]

class VirtualArray(BaseArray):
    """
    Class for representing virtual arrays, such as binary ops or ufuncs
    """
    def __init__(self):
        BaseArray.__init__(self)

    def _del_sources(self):
        # Function for deleting references to source arrays, to allow garbage-collecting them
        raise NotImplementedError

    #def compute(self):
    #    i = 0
    #    signature = self.signature
    #    result_size = self.find_size()
    #    result = create_sdarray(result_size, _dtype)
    #    #storage = result.get_root_storage()
    #    while i < result_size:
    #        #numpy_driver.jit_merge_point(signature=signature,
    #        #                             result_size=result_size, i=i,
    #        #                             self=self, result=result)
    #        #assert isinstance(temp, _dtype.TP.OF)
    #        result.setitem(i, self.eval(i))
    #        i += 1
    #    return result

def make_call1(_dtype):
    class Call1(VirtualArray):
        _immutable_fields_ = ["function", "values"]

        dtype = _dtype
        def __init__(self, function, values, signature):
            VirtualArray.__init__(self)
            self.function = function
            self.values = values
            self.forced_result = None
            self.signature = signature

        def _del_sources(self):
            self.values = None

        def compute(self):
            i = 0
            signature = self.signature
            result_size = self.find_size()
            result = create_sdarray(result_size, _dtype)
            result.setslice(0, result_size, 1, result_size, self)
            #while i < result_size:
            #    #numpy_driver.jit_merge_point(signature=signature,
            #    #                             result_size=result_size, i=i,
            #    #                             self=self, result=result)
            #    result.setitem(i, self.eval(i))
            #    i += 1
            return result

        def _find_size(self):
            return self.values.find_size()

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

        def _eval(self, i):
            return self.function(_dtype.convval(self.values.eval(i)))
    Call1.__name__ = "Call1_" + Call1.dtype.name
    return Call1

_call1_classes = [make_call1(d) for d in _dtype_list]

def pick_call1(dtype):
    return _call1_classes[dtype.num]

def make_call2(_dtype):
    class Call2(VirtualArray):
        """
        Intermediate class for performing binary operations.
        """
        _immutable_fields_ = ["function", "left", "right"]

        dtype = _dtype
        def __init__(self, function, left, right, signature):
            VirtualArray.__init__(self)
            self.left = left
            self.right = right
            dtype1 = self.left.find_dtype()
            dtype2 = self.right.find_dtype()
            self.function = function
            self.forced_result = None
            self.signature = signature
            #if dtype1.num != _dtype.num:
            #    self.cast1 = _dtype.convval
            #else:
            #    self.cast1 = _dtype.nocast
            #if dtype2.num != _dtype.num:
            #    self.cast2 = _dtype.convval
            #else:
            #    self.cast2 = _dtype.nocast
            #if dtype1.num != dtype2.num:
            #    cast = self.dtype.cast
            #    if dtype1.num != _dtype.num:
            #        if dtype2.num != _dtype.num:
            #            self.cast1 = 
            #            self.function = lambda x, y: function(cast(x), cast(y))
            #        else:
            #            self.function = lambda x, y: function(cast(x), y)
            #    else:
            #        self.function = lambda x, y: function(x, cast(y))
            #else:
            #    self.function = function

        def _del_sources(self):
            self.left = None
            self.right = None

        def compute(self):
            i = 0
            signature = self.signature
            result_size = self.find_size()
            result = create_sdarray(result_size, _dtype)
            while i < result_size:
                #numpy_driver.jit_merge_point(signature=signature,
                #                             result_size=result_size, i=i,
                #                             self=self, result=result)
                result.setitem(i, self.eval(i))
                i += 1
            return result

        def _find_size(self):
            try:
                return self.left.find_size()
            except:
                return self.right.find_size()

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



        def _eval(self, i):
            lhs, rhs = _dtype.convval(self.left.eval(i)), _dtype.convval(self.right.eval(i))
            return self.function(lhs, rhs)
    Call2.__name__ = "Call2_" + Call2.dtype.name
    return Call2

_call2_classes = [make_call2(d) for d in _dtype_list]

def pick_call2(dtype1, dtype2):
    if dtype1.num == dtype2.num:
        return _call2_classes[dtype1.num]
    return _call2_classes[find_result_dtype(dtype1, dtype2).num]

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

    def setitem_w(self, space, item, value):
        return self.parent.setitem_w(space, self.calc_index(item), value)

    def setitem(self, item, value):
        return self.parent.setitem(self.calc_index(item), value)

    def getitem(self, space, value):
        return self.parent.getitem(space, self.calc_index(value))

    def descr_len(self, space):
        return space.wrap(self.find_size())

    def descr_shape(self,space):
        return space.wrap(self.find_shape())

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
        self.size = slice_length

    def get_root_storage(self):
        return self.parent.get_root_storage()

    def find_size(self):
        return self.size

    def find_shape(self):
        return self.shape

    def setslice(self, start, stop, step, slice_length, arr):
        start = self.calc_index(start)
        if stop != -1:
            stop = self.calc_index(stop)
        step = self.step * step
        self.parent.setslice(start, stop, step, slice_length, arr)

    def calc_index(self, item):
        return (self.start + item * self.step)

class SingleDimArray(BaseArray):
    def __init__(self):
        BaseArray.__init__(self)

def fromlong(val):
    if val >= 0:
        if val == 0:
            digits = [rbigint.NULLDIGIT]
            sign = 0
        else:
            digits = rbigint.digits_from_nonneg_long(val)
            sign = 1
    else:
        digits = rbigint.digits_from_nonneg_long(-val)
        sign = -1
    return rbigint.rbigint(digits, sign)

def make_class(_dtype):
    class TypedSingleDimArray(BaseArray):
        signature = Signature()
        dtype = _dtype
        def __init__(self, size):
            BaseArray.__init__(self)
            self.size = size
            self.storage = lltype.malloc(_dtype.TP, size, zero=True,
                                     flavor='raw', track_allocation=False,
                                     add_memory_pressure=True)
            # XXX find out why test_zjit explodes with trackign of allocations

        def get_concrete(self):
            return self

        def find_size(self):
            return self.size

        def descr_len(self, space):
            return space.wrap(self.size)

        def descr_shape(self, space):
            return space.wrap(self.shape)

        def get_root_storage(self):
            return self.storage

        def eval(self, i):
            return self.storage[i]

        if _dtype.kind == 'b':
            def getitem(self, space, i):
                return space.wrap(bool(self.storage[i]))
        elif _dtype.kind == 'f':
            def getitem(self, space, i):
                return space.wrap(float(self.storage[i]))
        elif _dtype.num < 8 or (LONG_BIT == 64 and _dtype.num == 9):
            def getitem(self, space, i):
                return space.wrap(rffi.cast(lltype.Signed, self.storage[i]))
        elif LONG_BIT == 64 or _dtype.num == 8:
            def getitem(self, space, i):
                return space.wrap(self.storage[i])
        else: # unsigned longlong and signed longlong for 32-bit
            def getitem(self, space, i):
                return newlong(space, fromlong(self.storage[i]))

        def setitem(self, item, value):
            assert isinstance(value, _dtype.valtype)
            self.storage[item] = value

        #def setitem_cast(self, item, value):
        #    self.storage[item] = rffi.cast(_dtype.TP.OF, value)

        def _sliceloop1(self, start, stop, step, source):
            i = start
            j = 0
            conv = _dtype.convval
            while i < stop:
                #slice_driver1.jit_merge_point(signature=source.signature,
                        #dtype=_dtype,
                        #step=step, stop=stop, i=i, j=j, source=source,
                        #self=self)
                self.storage[i] = _dtype.convval(source.eval(j))
                j += 1
                i += step

        def _sliceloop2(self, start, stop, step, source):
            i = start
            j = 0
            conv = _dtype.convval
            while i > stop:
                #slice_driver2.jit_merge_point(signature=source.signature,
                #        dtype=_dtype,
                #        step=step, stop=stop, i=i, j=j, source=source,
                #        self=self)
                self.storage[i] = _dtype.convval(source.eval(j))
                j += 1
                i += step

        def setslice(self, start, stop, step, slice_length, arr):
            if step > 0:
                self._sliceloop1(start, stop, step, arr)
            else:
                self._sliceloop2(start, stop, step, arr)

        def setitem_w(self, space, item, value):
            self.storage[item] = rffi.cast(_dtype.TP.OF, _dtype.unwrap(space, value))

        def find_dtype(self):
            return self.dtype

        def __del__(self):
            lltype.free(self.storage, flavor='raw', track_allocation=False)

    TypedSingleDimArray.__name__ = 'SingleDimArray_' + _dtype.name
    return TypedSingleDimArray

def make_ndclass(_dtype):
    class TypedNDimArray(BaseArray):
        signature = Signature()
        dtype = _dtype
        def __init__(self, shape):
            BaseArray.__init__(self)
            self.shape = shape
            self.size = 1
            for v in shape:
                self.size *= v
            self.storage = lltype.malloc(_dtype.TP, self.size, zero=True,
                                     flavor='raw', track_allocation=False,
                                     add_memory_pressure=True)
            # XXX find out why test_zjit explodes with trackign of allocations

        def get_concrete(self):
            return self

        def find_size(self):
            return self.size

        def descr_len(self, space):
            return space.wrap(self.size)

        def descr_shape(self, space):
            return space.wrap(self.shape)

        def get_root_storage(self):
            return self.storage

        def eval(self, i):
            return self.storage[i]

        if _dtype.kind == 'b':
            def getitem(self, space, i):
                return space.wrap(bool(self.storage[i]))
        elif _dtype.kind == 'f':
            def getitem(self, space, i):
                return space.wrap(float(self.storage[i]))
        elif _dtype.num < 8 or (LONG_BIT == 64 and _dtype.num == 9):
            def getitem(self, space, i):
                return space.wrap(rffi.cast(lltype.Signed, self.storage[i]))
        elif LONG_BIT == 64 or _dtype.num == 8:
            def getitem(self, space, i):
                return space.wrap(self.storage[i])
        else: # unsigned longlong and signed longlong for 32-bit
            def getitem(self, space, i):
                return newlong(space, fromlong(self.storage[i]))

        def setitem(self, item, value):
            assert isinstance(value, _dtype.valtype)
            if issequence(item):
                assert len(item) == len(self.shape)
                pp = [0]+self.shape
                indx = 0
                for v,p in zip(item,pp):
                    index += indx*p+v
                self.storage[indx]=value
            else:    
                self.storage[item] = value

        #def setitem_cast(self, item, value):
        #    self.storage[item] = rffi.cast(_dtype.TP.OF, value)

        def _sliceloop1(self, start, stop, step, source):
            i = start
            j = 0
            conv = _dtype.convval
            while i < stop:
                #slice_driver1.jit_merge_point(signature=source.signature,
                        #dtype=_dtype,
                        #step=step, stop=stop, i=i, j=j, source=source,
                        #self=self)
                self.storage[i] = _dtype.convval(source.eval(j))
                j += 1
                i += step

        def _sliceloop2(self, start, stop, step, source):
            i = start
            j = 0
            conv = _dtype.convval
            while i > stop:
                #slice_driver2.jit_merge_point(signature=source.signature,
                #        dtype=_dtype,
                #        step=step, stop=stop, i=i, j=j, source=source,
                #        self=self)
                self.storage[i] = _dtype.convval(source.eval(j))
                j += 1
                i += step

        def setslice(self, start, stop, step, slice_length, arr):
            if step > 0:
                self._sliceloop1(start, stop, step, arr)
            else:
                self._sliceloop2(start, stop, step, arr)

        def setitem_w(self, space, item, value):
            if space.issequence_w(item):
                assert len(item) == len(self.shape)
                pp = [0]+self.shape
                indx = 0
                for v,p in zip(item,pp):
                    index += indx*p+v
                self.storage[indx] = rffi.cast(_dtype.TP.OF, _dtype.unwrap(space, value))
            else:    
                self.storage[item] = rffi.cast(_dtype.TP.OF, _dtype.unwrap(space, value))

        def find_dtype(self):
            return self.dtype

        def __del__(self):
            lltype.free(self.storage, flavor='raw', track_allocation=False)

    TypedNDimArray.__name__ = 'NDimArray_' + _dtype.name
    return TypedNDimArray

_array_classes = [make_class(d) for d in _dtype_list]
_ndarray_classes = [make_ndclass(d) for d in _dtype_list]

def create_sdarray(L, dtype):
    arr_type = _array_classes[dtype.num]
    return arr_type(L)
def create_ndarray(L, dtype):
    arr_type = _ndarray_classes[dtype.num]
    return arr_type(L)

def new_numarray(space, iterable, dtype):
    #shape = []
    #while True:
    #   try:
    #       # Try to get the length, a good proxy for iterability.
    #       length = space.len_w(w_input)
    #   except OperationError, e:
           # If it raised a TypeError it's not an iteratble, however if it raises
           # some other error we propogate it, that means __len__ raised something.
    #      if not e.matches(space, space.w_TypeError):
    #        raise
    #    break
    #else:
    #    shape.append(length)
    #    w_input = space.getitem(w_input, space.wrap(0)
    l = space.listview(iterable)
    dtype = get_dtype(space, dtype)
    w_elem = space.getitem(iterable, space.wrap(0))
    if space.issequence_w(w_elem):
        #Determine the size
        shape =[len(l)]
        while space.issequence_w(w_elem):
            shape.append(space.len_w(w_elem))
            w_elem = space.getitem(w_elem, space.wrap(0))
        arr = create_ndarray(shape,dtype)
        depth = 0
        #arr.setitem_w(space,shape,l)
        return arr
    arr = create_sdarray(len(l), dtype)
    i = 0
    for w_elem in l:
        arr.setitem_w(space, i, w_elem)
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
    dtype = _dtype_list[12]
    arr = _array_classes[dtype.num](size)
    one = dtype.cast(1)
    #for i in xrange(size):
    arr.setitem(0, one)
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
    #__abs__ = interp2app(BaseArray.descr_abs),
    #__add__ = interp2app(BaseArray.descr_add),
    #__sub__ = interp2app(BaseArray.descr_sub),
    #__mul__ = interp2app(BaseArray.descr_mul),
    #__div__ = interp2app(BaseArray.descr_div),
    #__pow__ = interp2app(BaseArray.descr_pow),
    #__mod__ = interp2app(BaseArray.descr_mod),
    #__radd__ = interp2app(BaseArray.descr_radd),
    #__rsub__ = interp2app(BaseArray.descr_rsub),
    #__rmul__ = interp2app(BaseArray.descr_rmul),
    #__rdiv__ = interp2app(BaseArray.descr_rdiv),
    #__rpow__ = interp2app(BaseArray.descr_rpow),
    #__rmod__ = interp2app(BaseArray.descr_rmod),
    #__repr__ = interp2app(BaseArray.descr_repr),
    #__str__ = interp2app(BaseArray.descr_str),

    #mean = interp2app(BaseArray.descr_mean),
    #sum = interp2app(BaseArray.descr_sum),
    #prod = interp2app(BaseArray.descr_prod),
    #max = interp2app(BaseArray.descr_max),
    #min = interp2app(BaseArray.descr_min),
    #argmax = interp2app(BaseArray.descr_argmax),
    #argmin = interp2app(BaseArray.descr_argmin),
    #all = interp2app(BaseArray.descr_all),
    #any = interp2app(BaseArray.descr_any),
    #dot = interp2app(BaseArray.descr_dot),
)
