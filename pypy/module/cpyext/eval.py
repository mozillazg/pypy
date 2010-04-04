
from pypy.module.cpyext.api import cpython_api, PyObject, CANNOT_FAIL

@cpython_api([PyObject, PyObject, PyObject], PyObject)
def PyEval_CallObjectWithKeywords(space, w_obj, w_arg, w_kwds):
    return space.call(w_obj, w_arg, w_kwds)

@cpython_api([PyObject, PyObject], PyObject)
def PyObject_CallObject(space, w_obj, w_arg):
    """
    Call a callable Python object callable_object, with arguments given by the
    tuple args.  If no arguments are needed, then args may be NULL.  Returns
    the result of the call on success, or NULL on failure.  This is the equivalent
    of the Python expression apply(callable_object, args) or
    callable_object(*args)."""
    return space.call(w_obj, w_arg)
