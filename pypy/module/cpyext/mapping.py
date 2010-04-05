from pypy.module.cpyext.api import cpython_api
from pypy.module.cpyext.pyobject import PyObject


@cpython_api([PyObject], PyObject)
def PyMapping_Keys(space, w_obj):
    """On success, return a list of the keys in object o.  On failure, return NULL.
    This is equivalent to the Python expression o.keys()."""
    return space.call_method(w_obj, "keys")
