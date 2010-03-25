import ctypes
import sys

from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import cpython_api, PyObject, make_ref, from_ref
from pypy.module.cpyext.state import State

DEBUG_REFCOUNT = False

# XXX Optimize these functions and put them into macro definitions
@cpython_api([PyObject], lltype.Void)
def Py_DECREF(space, obj):
    from pypy.module.cpyext.typeobject import string_dealloc
    obj.c_obj_refcnt -= 1
    if DEBUG_REFCOUNT:
        print >>sys.stderr, "DECREF", obj, obj.c_obj_refcnt
    if obj.c_obj_refcnt == 0:
        state = space.fromcache(State)
        ptr = ctypes.addressof(obj._obj._storage)
        if ptr not in state.py_objects_r2w and \
            space.is_w(from_ref(space, obj.c_obj_type), space.w_str):
            # this is a half-allocated string, lets call the deallocator
            # without modifying the r2w/w2r dicts
            _Py_Dealloc(space, obj)
        else:
            w_obj = state.py_objects_r2w.pop(ptr)
            _Py_Dealloc(space, obj)
            del state.py_objects_w2r[w_obj]
        if ptr in state.borrow_mapping:
            for containee in state.borrow_mapping[ptr]:
                w_containee = state.py_objects_r2w.get(containee)
                if w_containee is not None:
                    containee = state.py_objects_w2r[w_containee]
                    Py_DECREF(space, w_containee)
                    containee_ptr = ctypes.addressof(containee._obj._storage)
                    try:
                        del state.borrowed_objects[containee_ptr]
                    except KeyError:
                        pass
            del state.borrow_mapping[ptr]
    else:
        assert obj.c_obj_refcnt > 0

@cpython_api([PyObject], lltype.Void)
def Py_INCREF(space, obj):
    obj.c_obj_refcnt += 1
    if DEBUG_REFCOUNT:
        print >>sys.stderr, "INCREF", obj, obj.c_obj_refcnt

@cpython_api([PyObject], lltype.Void)
def Py_XDECREF(space, obj):
    if obj:
        Py_DECREF(space, obj)

def _Py_Dealloc(space, obj):
    from pypy.module.cpyext.typeobject import PyTypeObjectPtr
    from pypy.module.cpyext.methodobject import generic_cpy_call
    state = space.fromcache(State)
    pto = obj.c_obj_type
    pto = rffi.cast(PyTypeObjectPtr, pto)
    print >>sys.stderr, "Calling dealloc slot of", obj, \
          "'s type which is", rffi.charp2str(pto.c_tp_name)
    generic_cpy_call(space, pto.c_tp_dealloc, obj, decref_args=False)

