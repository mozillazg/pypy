from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import cpython_api, PyObject, CANNOT_FAIL
from pypy.module.cpyext.api import general_check

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyBool_Check(space, w_obj):
    w_type = space.w_bool
    return general_check(space, w_obj, w_type)

@cpython_api([rffi.LONG], PyObject)
def PyBool_FromLong(space, value):
    if value != 0:
        return space.w_True
    return space.w_False
