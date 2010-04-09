from pypy.module.cpyext.pyobject import PyObject
from pypy.module.cpyext.api import cpython_api, Py_ssize_t, CANNOT_FAIL
from pypy.rpython.lltypesystem import rffi, lltype

@cpython_api([PyObject, PyObject], PyObject)
def PyObject_GenericGetAttr(space, o, name):
    """Generic attribute getter function that is meant to be put into a type
    object's tp_getattro slot.  It looks for a descriptor in the dictionary
    of classes in the object's MRO as well as an attribute in the object's
    __dict__ (if present).  As outlined in descriptors, data
    descriptors take preference over instance attributes, while non-data
    descriptors don't.  Otherwise, an AttributeError is raised."""
    raise NotImplementedError
