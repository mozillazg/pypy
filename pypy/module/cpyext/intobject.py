
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import (cpython_api, PyObject, CANNOT_FAIL,
                                    build_type_checkers)


PyInt_Check, PyInt_CheckExact = build_type_checkers("Int")

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
