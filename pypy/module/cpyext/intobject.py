
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import cpython_api, PyObject, CANNOT_FAIL
from pypy.module.cpyext.api import general_check

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyInt_Check(space, w_obj):
    """Return true if o is of type PyInt_Type or a subtype of
    PyInt_Type.
    
    Allowed subtypes to be accepted."""
    return general_check(space, w_obj, space.w_int)

@cpython_api([lltype.Signed], PyObject)
def PyInt_FromLong(space, ival):
    """Create a new integer object with a value of ival.
    
    """
    return space.wrap(ival)

@cpython_api([PyObject], lltype.Signed, error=-1)
def PyInt_AsLong(space, w_obj):
    """Will first attempt to cast the object to a PyIntObject, if it is not
    already one, and then return its value. If there is an error, -1 is
    returned, and the caller should check PyErr_Occurred() to find out whether
    there was an error, or whether the value just happened to be -1."""
    return space.int_w(w_obj)
