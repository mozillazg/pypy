from pypy.interpreter.error import OperationError
from pypy.module.cpyext.api import cpython_api, CANNOT_FAIL
from pypy.module.cpyext.pyobject import PyObject
from pypy.rpython.lltypesystem import rffi, lltype

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyIndex_Check(space, w_obj):
    """Returns True if o is an index integer (has the nb_index slot of the
    tp_as_number structure filled in).
    """
    try:
        space.index(w_obj)
        return 1
    except OperationError:
        return 0
