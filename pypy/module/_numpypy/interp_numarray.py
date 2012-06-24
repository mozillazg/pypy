
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import unwrap_spec
from pypy.interpreter.error import operationerrfmt

class W_NDArray(Wrappable):
    def __init__(self, impl):
        self.impl = impl

class BaseArrayImpl(object):
    pass

class Scalar(BaseArrayImpl):
    pass

class ConcreteArray(BaseArrayImpl):
    def __init__(self, shape):
        self.shape = shape

W_NDArray.typedef = TypeDef('ndarray',
    __module__ = 'numpypy',
)

@unwrap_spec(subok=bool, copy=bool, ownmaskna=bool)
def descr_array(space, w_item_or_iterable, w_dtype=None, copy=True,
                w_order=None, subok=False, ndmin=0, w_maskna=None,
                ownmaskna=False):
    # find scalar
    if w_maskna is None:
        w_maskna = space.w_None
    if subok or not space.is_w(w_maskna, space.w_None) or ownmaskna:
        raise operationerrfmt(space.w_NotImplementedError,
                              "Unsupported args")
    xxx

    
    if not space.issequence_w(w_item_or_iterable):
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
    if isinstance(w_item_or_iterable, BaseArray):
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
    shape, elems_w = find_shape_and_elems(space, w_item_or_iterable, dtype)
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
    arr = W_NDimArray(shape[:], dtype=dtype, order=order)
    arr_iter = arr.create_iter()
    # XXX we might want to have a jitdriver here
    for i in range(len(elems_w)):
        w_elem = elems_w[i]
        dtype.setitem(arr, arr_iter.offset,
                      dtype.coerce(space, w_elem))
        arr_iter = arr_iter.next(shapelen)
    return arr
