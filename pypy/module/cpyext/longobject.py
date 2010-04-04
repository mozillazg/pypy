from pypy.rpython.lltypesystem import lltype, rffi
from pypy.module.cpyext.api import cpython_api, PyObject
from pypy.objspace.std.longobject import W_LongObject
from pypy.interpreter.error import OperationError


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

