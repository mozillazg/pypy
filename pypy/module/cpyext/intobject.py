
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import cpython_api, PyObject, CANNOT_FAIL
from pypy.module.cpyext.api import general_check

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyInt_Check(space, w_obj):
    """Return true if o is of type PyInt_Type or a subtype of
    PyInt_Type.
    
    Allowed subtypes to be accepted."""
    return general_check(space, w_obj, space.w_int)
