import ctypes

from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import cpython_api, PyObject, make_ref
from pypy.module.cpyext.state import State

# XXX Optimize these functions and put them into macro definitions
@cpython_api([PyObject], lltype.Void)
def Py_DECREF(space, obj):
    obj.c_obj_refcnt -= 1
    if obj.c_obj_refcnt == 0:
        state = space.fromcache(State)
        ptr = ctypes.addressof(obj._obj._storage)
        w_obj = state.py_objects_r2w.pop(ptr)
        _Py_Dealloc(space, obj)
        del state.py_objects_w2r[w_obj]
    else:
        assert obj.c_obj_refcnt > 0

@cpython_api([PyObject], lltype.Void)
def Py_INCREF(space, obj):
    obj.c_obj_refcnt += 1


def _Py_Dealloc(space, obj):
    from pypy.module.cpyext.typeobject import PyTypeObjectPtr
    from pypy.module.cpyext.methodobject import generic_cpy_call
    state = space.fromcache(State)
    pto = obj.c_obj_type
    pto = rffi.cast(PyTypeObjectPtr, pto)
    print "Calling dealloc slot of", obj, \
          "'s type which is", rffi.charp2str(pto.c_tp_name)
    generic_cpy_call(space, pto.c_tp_dealloc, obj, decref_args=False)

