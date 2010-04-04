
from pypy.interpreter.error import OperationError
from pypy.module.cpyext.api import cpython_api, CANNOT_FAIL, Py_ssize_t
from pypy.module.cpyext.pyobject import PyObject, register_container
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.objspace.std import listobject, tupleobject

@cpython_api([PyObject, rffi.CCHARP], PyObject)
def PySequence_Fast(space, w_obj, m):
    """Returns the sequence o as a tuple, unless it is already a tuple or list, in
    which case o is returned.  Use PySequence_Fast_GET_ITEM() to access the
    members of the result.  Returns NULL on failure.  If the object is not a
    sequence, raises TypeError with m as the message text."""
    if (space.is_true(space.isinstance(w_obj, space.w_list)) or
        space.is_true(space.isinstance(w_obj, space.w_tuple))):
        return w_obj
    try:
        return space.newtuple(space.fixedview(w_obj))
    except OperationError:
        raise OperationError(space.w_TypeError, space.wrap(rffi.charp2str(m)))

@cpython_api([PyObject, Py_ssize_t], PyObject, borrowed=True)
def PySequence_Fast_GET_ITEM(space, w_obj, index):
    """Return the ith element of o, assuming that o was returned by
    PySequence_Fast(), o is not NULL, and that i is within bounds.
    """
    if isinstance(w_obj, listobject.W_ListObject):
        w_res = w_obj.wrappeditems[index]
    else:
        assert isinstance(w_obj, tupleobject.W_TupleObject)
        w_res = w_obj.wrappeditems[index]
    register_container(space, w_obj)
    return w_res

@cpython_api([PyObject], Py_ssize_t, error=CANNOT_FAIL)
def PySequence_Fast_GET_SIZE(space, w_obj):
    """Returns the length of o, assuming that o was returned by
    PySequence_Fast() and that o is not NULL.  The size can also be
    gotten by calling PySequence_Size() on o, but
    PySequence_Fast_GET_SIZE() is faster because it can assume o is a list
    or tuple."""
    if isinstance(w_obj, listobject.W_ListObject):
        return len(w_obj.wrappeditems)
    assert isinstance(w_obj, tupleobject.W_TupleObject)
    return len(w_obj.wrappeditems)

@cpython_api([PyObject, Py_ssize_t, Py_ssize_t], PyObject)
def PySequence_GetSlice(space, w_obj, w_start, w_end):
    """Return the slice of sequence object o between i1 and i2, or NULL on
    failure. This is the equivalent of the Python expression o[i1:i2].
    
    This function used an int type for i1 and i2. This might
    require changes in your code for properly supporting 64-bit systems."""
    return space.getslice(w_obj, w_start, w_end)
