
from pypy.interpreter.error import OperationError
from pypy.module.cpyext.api import cpython_api, PyObject, CANNOT_FAIL,\
     Py_ssize_t
from pypy.rpython.lltypesystem import rffi, lltype

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
        return space.newtuple(space.unpackiterable(w_obj))
    except OperationError:
        raise OperationError(space.w_TypeError, space.wrap(rffi.charp2str(m)))
