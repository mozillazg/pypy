from pypy.rpython.lltypesystem import lltype, rffi
from pypy.module.cpyext.api import cpython_api, CANNOT_FAIL
from pypy.module.cpyext.pyobject import PyObject


@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyMapping_Check(space, w_obj):
    """Return 1 if the object provides mapping protocol, and 0 otherwise.  This
    function always succeeds."""
    return int(space.findattr(w_obj, space.wrap("items")) is not None)

@cpython_api([PyObject], PyObject)
def PyMapping_Keys(space, w_obj):
    """On success, return a list of the keys in object o.  On failure, return NULL.
    This is equivalent to the Python expression o.keys()."""
    return space.call_method(w_obj, "keys")

@cpython_api([PyObject], PyObject)
def PyMapping_Items(space, w_obj):
    """On success, return a list of the items in object o, where each item is a tuple
    containing a key-value pair.  On failure, return NULL. This is equivalent to
    the Python expression o.items()."""
    return space.call_method(w_obj, "items")

