
from pypy.module.cpyext.api import cpython_api, PyObject, CANNOT_FAIL

@cpython_api([PyObject, PyObject, PyObject], PyObject)
def PyEval_CallObjectWithKeywords(space, w_obj, w_arg, w_kwds):
    return space.call(w_obj, w_arg, w_kwds)
