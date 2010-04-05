from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import cpython_api, PyObject, build_type_checkers
from pypy.interpreter.error import OperationError

PyFloat_Check, PyFloat_CheckExact = build_type_checkers("Float")

@cpython_api([lltype.Float], PyObject)
def PyFloat_FromDouble(space, value):
    return space.wrap(value)

@cpython_api([PyObject], lltype.Float, error=-1)
def PyFloat_AsDouble(space, w_obj):
    return space.float_w(space.float(w_obj))


@cpython_api([PyObject], PyObject)
def PyNumber_Float(space, w_obj):
    """
    Returns the o converted to a float object on success, or NULL on failure.
    This is the equivalent of the Python expression float(o)."""
    return space.float(w_obj)
