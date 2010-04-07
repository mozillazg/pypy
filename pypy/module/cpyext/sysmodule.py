from pypy.interpreter.error import OperationError
from pypy.rpython.lltypesystem import rffi
from pypy.module.cpyext.api import CANNOT_FAIL, cpython_api
from pypy.module.cpyext.pyobject import PyObject

@cpython_api([rffi.CCHARP], PyObject, borrowed=True, error=CANNOT_FAIL)
def PySys_GetObject(space, name):
    """Return the object name from the sys module or NULL if it does
    not exist, without setting an exception."""
    w_name = rffi.charp2str(name)
    try:
        w_obj = space.sys.get(w_name)
    except OperationError, e:
        if not e.match(space, space.w_AttributeError):
            raise
        w_obj = None
    return w_obj
