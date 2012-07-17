
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.interpreter.gateway import unwrap_spec, interp2app
from pypy.interpreter.error import operationerrfmt

from pypy.module._numpypy import interp_dtype, strides, interp_ufuncs
from pypy.tool.sourcetools import func_with_new_name

class W_NDArray(Wrappable):
    def __init__(self, impl, dtype):
        self.impl = impl
        self.dtype = dtype

    def descr_get_shape(self, space):
        return space.newtuple([space.wrap(i) for i in self.impl.getshape()])

    def descr_get_dtype(self, space):
        return self.dtype

    def _binop_impl(ufunc_name):
        def impl(self, space, w_other, w_out=None):
            return getattr(interp_ufuncs.get(space), ufunc_name).call(space,
                                                        [self, w_other, w_out])
        return func_with_new_name(impl, "binop_%s_impl" % ufunc_name)

    descr_add = _binop_impl("add")
    descr_sub = _binop_impl("subtract")
    descr_mul = _binop_impl("multiply")
    descr_div = _binop_impl("divide")
    descr_truediv = _binop_impl("true_divide")
    descr_floordiv = _binop_impl("floor_divide")
    descr_mod = _binop_impl("mod")
    descr_pow = _binop_impl("power")
    descr_lshift = _binop_impl("left_shift")
    descr_rshift = _binop_impl("right_shift")
    descr_and = _binop_impl("bitwise_and")
    descr_or = _binop_impl("bitwise_or")
    descr_xor = _binop_impl("bitwise_xor")

    def descr_divmod(self, space, w_other):
        w_quotient = self.descr_div(space, w_other)
        w_remainder = self.descr_mod(space, w_other)
        return space.newtuple([w_quotient, w_remainder])

    descr_eq = _binop_impl("equal")
    descr_ne = _binop_impl("not_equal")
    descr_lt = _binop_impl("less")
    descr_le = _binop_impl("less_equal")
    descr_gt = _binop_impl("greater")
    descr_ge = _binop_impl("greater_equal")

class BaseArrayImpl(object):
    pass

class Scalar(BaseArrayImpl):
    def getshape(self):
        return []

class ConcreteArray(BaseArrayImpl):
    def __init__(self, shape):
        self.shape = shape

    def getshape(self):
        return self.shape

def descr_new_array(space, w_subtype, w_size, w_dtype=None):
    dtype = space.interp_w(interp_dtype.W_Dtype,
              space.call_function(space.gettypefor(interp_dtype.W_Dtype),
                                  w_dtype))
    shape = strides.find_shape_from_scalar(space, w_size)
    return space.wrap(W_NDArray(ConcreteArray(shape), dtype=dtype))

W_NDArray.typedef = TypeDef('ndarray',
    __module__ = 'numpypy',
    __new__ = interp2app(descr_new_array),
    shape = GetSetProperty(W_NDArray.descr_get_shape),
    dtype = GetSetProperty(W_NDArray.descr_get_dtype),

    __add__ = interp2app(W_NDArray.descr_add),
    __sub__ = interp2app(W_NDArray.descr_sub),
    __mul__ = interp2app(W_NDArray.descr_mul),
    __div__ = interp2app(W_NDArray.descr_div),
    __truediv__ = interp2app(W_NDArray.descr_truediv),
    __floordiv__ = interp2app(W_NDArray.descr_floordiv),
    __mod__ = interp2app(W_NDArray.descr_mod),
    __divmod__ = interp2app(W_NDArray.descr_divmod),
    __pow__ = interp2app(W_NDArray.descr_pow),
    __lshift__ = interp2app(W_NDArray.descr_lshift),
    __rshift__ = interp2app(W_NDArray.descr_rshift),
    __and__ = interp2app(W_NDArray.descr_and),
    __or__ = interp2app(W_NDArray.descr_or),
    __xor__ = interp2app(W_NDArray.descr_xor),
)

@unwrap_spec(subok=bool, copy=bool, ownmaskna=bool)
def descr_array(space, w_item_or_iterable, w_dtype=None, copy=True,
                w_order=None, subok=False, w_ndmin=None, w_maskna=None,
                ownmaskna=False):
    # find scalar
    if w_maskna is None:
        w_maskna = space.w_None
    if subok or not space.is_w(w_maskna, space.w_None) or ownmaskna:
        raise operationerrfmt(space.w_NotImplementedError,
                              "Unsupported args")
    if not strides.is_list_or_tuple(space, w_item_or_iterable):
        if w_dtype is None or space.is_w(w_dtype, space.w_None):
            w_dtype = interp_ufuncs.find_dtype_for_scalar(space,
                                                          w_item_or_iterable)
        dtype = space.interp_w(interp_dtype.W_Dtype,
            space.call_function(space.gettypefor(interp_dtype.W_Dtype), w_dtype)
        )
        return scalar_w(space, dtype, w_item_or_iterable)
    if space.is_w(w_order, space.w_None) or w_order is None:
        order = 'C'
    else:
        order = space.str_w(w_order)
        if order != 'C':  # or order != 'F':
            raise operationerrfmt(space.w_ValueError, "Unknown order: %s",
                                  order)
    if isinstance(w_item_or_iterable, W_NDArray):
        if (not space.is_w(w_dtype, space.w_None) and
            w_item_or_iterable.find_dtype() is not w_dtype):
            raise OperationError(space.w_NotImplementedError, space.wrap(
                "copying over different dtypes unsupported"))
        if copy:
            return w_item_or_iterable.copy(space)
        return w_item_or_iterable
    if w_dtype is None or space.is_w(w_dtype, space.w_None):
        dtype = None
    else:
        dtype = space.interp_w(interp_dtype.W_Dtype,
           space.call_function(space.gettypefor(interp_dtype.W_Dtype), w_dtype))
    shape, elems_w = strides.find_shape_and_elems(space, w_item_or_iterable,
                                                  dtype)
    # they come back in C order
    if dtype is None:
        for w_elem in elems_w:
            dtype = interp_ufuncs.find_dtype_for_scalar(space, w_elem,
                                                        dtype)
            if dtype is interp_dtype.get_dtype_cache(space).w_float64dtype:
                break
        if dtype is None:
            dtype = interp_dtype.get_dtype_cache(space).w_float64dtype
    shapelen = len(shape)
    if w_ndmin is not None and not space.is_w(w_ndmin, space.w_None):
        ndmin = space.int_w(w_ndmin)
        if ndmin > shapelen:
            shape = [1] * (ndmin - shapelen) + shape
            shapelen = ndmin
    arr = W_NDArray(ConcreteArray(shape), dtype=dtype)
    #arr_iter = arr.create_iter()
    # XXX we might want to have a jitdriver here
    #for i in range(len(elems_w)):
    #    w_elem = elems_w[i]
    #    dtype.setitem(arr, arr_iter.offset,
    #                  dtype.coerce(space, w_elem))
    #    arr_iter = arr_iter.next(shapelen)
    return arr
