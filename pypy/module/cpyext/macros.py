import ctypes

from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import cpython_api, PyObject, make_ref
from pypy.module.cpyext.state import State

# XXX Optimize these functions and put them into macro definitions
@cpython_api([PyObject], lltype.Void)
def Py_DECREF(space, w_obj):
    print "DECREF", w_obj
    state = space.fromcache(State)
    obj = state.py_objects_w2r[w_obj]
    obj.c_obj_refcnt -= 1
    if obj.c_obj_refcnt == 0:
        ptr = ctypes.addressof(obj._obj._storage)
        _Py_Dealloc(space, w_obj)
        del state.py_objects_w2r[w_obj]
        del state.py_objects_r2w[ptr]
    else:
        assert obj.c_obj_refcnt > 0
    return

@cpython_api([PyObject], lltype.Void)
def Py_INCREF(space, obj):
    obj.c_obj_refcnt += 1


def _Py_Dealloc(space, w_obj):
    from pypy.module.cpyext.typeobject import PyTypeObjectPtr
    from pypy.module.cpyext.methodobject import generic_cpy_call
    state = space.fromcache(State)
    w_type = space.type(w_obj)
    pto = make_ref(space, w_type)
    pto = rffi.cast(PyTypeObjectPtr, pto)
    try:
        print "Calling ", pto.c_tp_dealloc, "of", w_obj, "'s type which is", w_type
        generic_cpy_call(space, pto.c_tp_dealloc, w_obj, decref_args=False)
    finally:
        Py_DECREF(space, w_type) # make_ref bumps refcount

