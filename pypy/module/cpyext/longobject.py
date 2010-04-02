
from pypy.rpython.lltypesystem import lltype
from pypy.module.cpyext.api import cpython_api, PyObject


@cpython_api([lltype.Signed], PyObject)
def PyLong_FromLong(space, val):
    """Return a new PyLongObject object from v, or NULL on failure."""
    return space.wrap(val)


