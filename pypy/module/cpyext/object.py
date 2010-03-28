from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import cpython_api, PyObject, make_ref, from_ref, \
        generic_cpy_call, CANNOT_FAIL
from pypy.module.cpyext.state import State
from pypy.module.cpyext.macros import Py_INCREF, Py_DECREF
from pypy.module.cpyext.typeobject import PyTypeObjectPtr, W_PyCTypeObject, W_PyCObject
from pypy.objspace.std.objectobject import W_ObjectObject
import pypy.module.__builtin__.operation as operation

@cpython_api([PyObject], PyObject)
def _PyObject_New(space, w_type):
    if isinstance(w_type, W_PyCTypeObject):
        w_pycobj = space.allocate_instance(W_PyCObject, w_type)
        w_pycobj.__init__(space)
        return w_pycobj
    assert False, "Please add more cases in get_cls_for_type_object!"

@cpython_api([rffi.VOIDP_real], lltype.Void)
def PyObject_Del(space, obj):
    lltype.free(obj, flavor='raw')

@cpython_api([PyObject], lltype.Void)
def PyObject_dealloc(space, obj):
    pto = rffi.cast(PyTypeObjectPtr, obj.c_ob_type)
    obj_voidp = rffi.cast(rffi.VOIDP_real, obj)
    generic_cpy_call(space, pto.c_tp_free, obj_voidp)

@cpython_api([PyObject], rffi.INT_real, error=-1)
def PyObject_IsTrue(space, w_obj):
    return space.is_true(w_obj)

@cpython_api([PyObject], rffi.INT_real, error=-1)
def PyObject_Not(space, w_obj):
    return not space.is_true(w_obj)

@cpython_api([PyObject, PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyObject_HasAttr(space, w_obj, w_name):
    w_res = operation.hasattr(space, w_obj, w_name)
    return space.is_true(w_res)

@cpython_api([PyObject, PyObject, PyObject], rffi.INT_real, error=-1)
def PyObject_SetAttr(space, w_obj, w_name, w_value):
    operation.setattr(space, w_obj, w_name, w_value)
    return 0
