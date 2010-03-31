from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import cpython_api, CANNOT_FAIL
from pypy.module.cpyext.api import general_check, general_check_exact
from pypy.module.cpyext.pyobject import PyObject, register_container
from pypy.module.cpyext.pyerrors import PyErr_BadInternalCall
from pypy.interpreter.error import OperationError

@cpython_api([], PyObject)
def PyDict_New(space):
    return space.newdict()

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyDict_Check(space, w_obj):
    w_type = space.w_dict
    return general_check(space, w_obj, w_type)

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyDict_CheckExact(space, w_obj):
    w_type = space.w_dict
    return general_check_exact(space, w_obj, w_type)

@cpython_api([PyObject, PyObject], PyObject)
def PyDict_GetItem(space, w_dict, w_key):
    if PyDict_Check(space, w_dict):
        return space.getitem(w_dict, w_key)
    else:
        PyErr_BadInternalCall(space)

@cpython_api([PyObject, PyObject, PyObject], rffi.INT_real, error=-1)
def PyDict_SetItem(space, w_dict, w_key, w_obj):
    if PyDict_Check(space, w_dict):
        space.setitem(w_dict, w_key, w_obj)
        return 0
    else:
        PyErr_BadInternalCall(space)

@cpython_api([PyObject, rffi.CCHARP, PyObject], rffi.INT_real, error=-1)
def PyDict_SetItemString(space, w_dict, key_ptr, w_obj):
    if PyDict_Check(space, w_dict):
        key = rffi.charp2str(key_ptr)
        # our dicts dont have a standardized interface, so we need
        # to go through the space
        space.setitem(w_dict, space.wrap(key), w_obj)
        return 0
    else:
        PyErr_BadInternalCall(space)

@cpython_api([PyObject, rffi.CCHARP], PyObject, borrowed=True)
def PyDict_GetItemString(space, w_dict, key):
    """This is the same as PyDict_GetItem(), but key is specified as a
    char*, rather than a PyObject*."""
    if not PyDict_Check(space, w_dict):
        PyErr_BadInternalCall(space)
    w_res = space.finditem_str(w_dict, rffi.charp2str(key))
    if w_res is None:
        raise OperationError(space.w_KeyError, space.wrap("Key not found"))
    register_container(space, w_dict)
    return w_res
