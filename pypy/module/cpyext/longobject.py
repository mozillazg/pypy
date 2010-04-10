from pypy.rpython.lltypesystem import lltype, rffi
from pypy.module.cpyext.api import cpython_api, PyObject, build_type_checkers
from pypy.objspace.std.longobject import W_LongObject
from pypy.interpreter.error import OperationError


PyLong_Check, PyLong_CheckExact = build_type_checkers("Long")

@cpython_api([lltype.Signed], PyObject)
def PyLong_FromLong(space, val):
    """Return a new PyLongObject object from v, or NULL on failure."""
    return space.wrap(val)

@cpython_api([PyObject], rffi.ULONG, error=0)
def PyLong_AsUnsignedLong(space, w_long):
    """
    Return a C unsigned long representation of the contents of pylong.
    If pylong is greater than ULONG_MAX, an OverflowError is
    raised."""
    return rffi.cast(rffi.ULONG, space.uint_w(w_long))

@cpython_api([rffi.VOIDP], PyObject)
def PyLong_FromVoidPtr(space, p):
    """Create a Python integer or long integer from the pointer p. The pointer value
    can be retrieved from the resulting value using PyLong_AsVoidPtr().

    If the integer is larger than LONG_MAX, a positive long integer is returned."""
    return space.wrap(rffi.cast(rffi.LONG, p))

