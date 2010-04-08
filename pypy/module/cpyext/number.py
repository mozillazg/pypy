from pypy.interpreter.error import OperationError
from pypy.module.cpyext.api import cpython_api, CANNOT_FAIL, Py_ssize_t
from pypy.module.cpyext.pyobject import PyObject
from pypy.rpython.lltypesystem import rffi, lltype

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyIndex_Check(space, w_obj):
    """Returns True if o is an index integer (has the nb_index slot of the
    tp_as_number structure filled in).
    """
    try:
        space.index(w_obj)
        return 1
    except OperationError:
        return 0

@cpython_api([PyObject, PyObject], Py_ssize_t, error=-1)
def PyNumber_AsSsize_t(space, w_obj, w_exc):
    """Returns o converted to a Py_ssize_t value if o can be interpreted as an
    integer. If o can be converted to a Python int or long but the attempt to
    convert to a Py_ssize_t value would raise an OverflowError, then the
    exc argument is the type of exception that will be raised (usually
    IndexError or OverflowError).  If exc is NULL, then the
    exception is cleared and the value is clipped to PY_SSIZE_T_MIN for a negative
    integer or PY_SSIZE_T_MAX for a positive integer.
    """
    return space.int_w(w_obj) #XXX: this is wrong
