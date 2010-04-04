from pypy.module.cpyext.api import cpython_api
from pypy.module.cpyext.pyobject import PyObject


@cpython_api([PyObject], PyObject)
def PyMapping_Keys(space, w_obj):
    """On success, return a list of the keys in object o.  On failure, return NULL.
    This is equivalent to the Python expression o.keys()."""
    # XXX: Cpython implements this in terms of PyObject_CallMethod, we should
    # do that eventually.
    w_meth = space.getattr(w_obj, space.wrap("keys"))
    return space.call_function(w_meth)
