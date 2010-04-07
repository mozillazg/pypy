from pypy.interpreter.error import OperationError
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import CANNOT_FAIL, cpython_api
from pypy.module.cpyext.pyobject import PyObject, register_container

@cpython_api([rffi.CCHARP], PyObject, borrowed=True, error=CANNOT_FAIL)
def PySys_GetObject(space, name):
    """Return the object name from the sys module or NULL if it does
    not exist, without setting an exception."""
    w_name = rffi.charp2str(name)
    w_dict = space.sys.getdict()
    w_obj = space.finditem_str(w_dict, w_name)
    register_container(space, w_dict)
    return w_obj
