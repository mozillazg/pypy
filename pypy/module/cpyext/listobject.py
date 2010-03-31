
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import cpython_api, PyObject, CANNOT_FAIL,\
     Py_ssize_t
from pypy.module.cpyext.api import general_check, general_check_exact
from pypy.module.cpyext.pyerrors import PyErr_BadInternalCall
from pypy.module.cpyext.macros import Py_XDECREF
from pypy.objspace.std.listobject import W_ListObject
from pypy.interpreter.error import OperationError

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyList_Check(space, w_obj):
    """Return true if p is a list object or an instance of a subtype of the list
    type.

    Allowed subtypes to be accepted."""
    w_type = space.w_list
    return general_check(space, w_obj, w_type)

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyList_CheckExact(space, w_obj):
    """Return true if p is a list object, but not an instance of a subtype of
    the list type.
    """
    w_type = space.w_list
    return general_check_exact(space, w_obj, w_type)

@cpython_api([Py_ssize_t], PyObject)
def PyList_New(space, len):
    """Return a new list of length len on success, or NULL on failure.
    
    If length is greater than zero, the returned list object's items are
    set to NULL.  Thus you cannot use abstract API functions such as
    PySequence_SetItem()  or expose the object to Python code before
    setting all items to a real object with PyList_SetItem().
    """
    return space.newlist([None] * len)

@cpython_api([PyObject, Py_ssize_t, PyObject], rffi.INT_real, error=-1)
def PyList_SetItem(space, w_list, index, w_item):
    """Set the item at index index in list to item.  Return 0 on success
    or -1 on failure.
    
    This function "steals" a reference to item and discards a reference to
    an item already in the list at the affected position.
    """
    Py_XDECREF(space, w_item)
    if not isinstance(w_list, W_ListObject):
        PyErr_BadInternalCall(space)
    wrappeditems = w_list.wrappeditems
    if index < 0 or index >= len(wrappeditems):
        raise OperationError(space.w_IndexError, space.wrap(
            "list assignment index out of range"))
    wrappeditems[index] = w_item
    return 0

@cpython_api([PyObject, PyObject], rffi.INT_real, error=-1)
def PyList_Append(space, w_list, w_item):
    if not isinstance(w_list, W_ListObject):
        PyErr_BadInternalCall(space)
    w_list.append(w_item)
    return 0
