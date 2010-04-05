import sys

from pypy.interpreter.baseobjspace import W_Root
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import cpython_api, PyObject, PyStringObject, ADDR,\
        Py_TPFLAGS_HEAPTYPE, PyUnicodeObject, PyTypeObjectPtr
from pypy.module.cpyext.state import State
from pypy.objspace.std.stringobject import W_StringObject
from pypy.objspace.std.unicodeobject import W_UnicodeObject
from pypy.rlib.objectmodel import we_are_translated

#________________________________________________________
# refcounted object support

class NullPointerException(Exception):
    pass

class InvalidPointerException(Exception):
    pass

DEBUG_REFCOUNT = False

def debug_refcount(*args, **kwargs):
    frame_stackdepth = kwargs.pop("frame_stackdepth", 2)
    assert not kwargs
    frame = sys._getframe(frame_stackdepth)
    print >>sys.stderr, "%25s" % (frame.f_code.co_name, ),
    for arg in args:
        print >>sys.stderr, arg,
    print >>sys.stderr


def make_ref(space, w_obj, borrowed=False, steal=False):
    from pypy.module.cpyext.typeobject import allocate_type_obj,\
            W_PyCTypeObject, PyOLifeline
    if w_obj is None:
        return lltype.nullptr(PyObject.TO)
    assert isinstance(w_obj, W_Root)
    state = space.fromcache(State)
    py_obj = state.py_objects_w2r.get(w_obj, lltype.nullptr(PyObject.TO))
    if not py_obj:
        assert not steal
        w_type = space.type(w_obj)
        if space.is_w(w_type, space.w_type) or space.is_w(w_type,
                space.gettypeobject(W_PyCTypeObject.typedef)):
            pto = allocate_type_obj(space, w_obj)
            py_obj = rffi.cast(PyObject, pto)
            # c_ob_type and c_ob_refcnt are set by allocate_type_obj
        elif isinstance(w_type, W_PyCTypeObject):
            lifeline = w_obj.get_pyolifeline()
            if lifeline is not None: # make old PyObject ready for use in C code
                py_obj = lifeline.pyo
                assert py_obj.c_ob_refcnt == 0
                Py_IncRef(space, py_obj)
            else:
                w_type_pyo = make_ref(space, w_type)
                pto = rffi.cast(PyTypeObjectPtr, w_type_pyo)
                # Don't increase refcount for non-heaptypes
                if not rffi.cast(lltype.Signed, pto.c_tp_flags) & Py_TPFLAGS_HEAPTYPE:
                    Py_DecRef(space, w_type_pyo)
                basicsize = pto.c_tp_basicsize
                py_obj_pad = lltype.malloc(rffi.VOIDP.TO, basicsize,
                        flavor="raw", zero=True)
                py_obj = rffi.cast(PyObject, py_obj_pad)
                py_obj.c_ob_refcnt = 1
                py_obj.c_ob_type = pto
                w_obj.set_pyolifeline(PyOLifeline(space, py_obj))
        elif isinstance(w_obj, W_StringObject):
            py_obj_str = lltype.malloc(PyStringObject.TO, flavor='raw', zero=True)
            py_obj_str.c_size = len(space.str_w(w_obj))
            py_obj_str.c_buffer = lltype.nullptr(rffi.CCHARP.TO)
            pto = make_ref(space, space.w_str)
            py_obj = rffi.cast(PyObject, py_obj_str)
            py_obj.c_ob_refcnt = 1
            py_obj.c_ob_type = rffi.cast(PyTypeObjectPtr, pto)
        elif isinstance(w_obj, W_UnicodeObject):
            py_obj_unicode = lltype.malloc(PyUnicodeObject.TO, flavor='raw', zero=True)
            py_obj_unicode.c_size = len(space.unicode_w(w_obj))
            py_obj_unicode.c_buffer = lltype.nullptr(rffi.VOIDP.TO)
            pto = make_ref(space, space.w_unicode)
            py_obj = rffi.cast(PyObject, py_obj_unicode)
            py_obj.c_ob_refcnt = 1
            py_obj.c_ob_type = rffi.cast(PyTypeObjectPtr, pto)
        else:
            py_obj = lltype.malloc(PyObject.TO, flavor="raw", zero=True)
            py_obj.c_ob_refcnt = 1
            pto = make_ref(space, space.type(w_obj))
            py_obj.c_ob_type = rffi.cast(PyTypeObjectPtr, pto)
        ptr = rffi.cast(ADDR, py_obj)
        if DEBUG_REFCOUNT:
            debug_refcount("MAKREF", py_obj, w_obj)
        state.py_objects_w2r[w_obj] = py_obj
        state.py_objects_r2w[ptr] = w_obj
        if borrowed and ptr not in state.borrowed_objects:
            state.borrowed_objects[ptr] = None
    elif not steal:
        if borrowed:
            py_obj_addr = rffi.cast(ADDR, py_obj)
            if py_obj_addr not in state.borrowed_objects:
                Py_IncRef(space, py_obj)
                state.borrowed_objects[py_obj_addr] = None
        else:
            Py_IncRef(space, py_obj)
    return py_obj

def force_string(space, ref):
    state = space.fromcache(State)
    ref = rffi.cast(PyStringObject, ref)
    s = rffi.charpsize2str(ref.c_buffer, ref.c_size)
    ref = rffi.cast(PyObject, ref)
    w_str = space.wrap(s)
    state.py_objects_w2r[w_str] = ref
    ptr = rffi.cast(ADDR, ref)
    state.py_objects_r2w[ptr] = w_str
    return w_str


def from_ref(space, ref):
    assert lltype.typeOf(ref) == PyObject
    if not ref:
        return None
    state = space.fromcache(State)
    ptr = rffi.cast(ADDR, ref)
    try:
        w_obj = state.py_objects_r2w[ptr]
    except KeyError:
        ref_type = rffi.cast(PyObject, ref.c_ob_type)
        if ref != ref_type and space.is_w(from_ref(space, ref_type), space.w_str):
            return force_string(space, ref)
        else:
            msg = ""
            if not we_are_translated():
                msg = "Got invalid reference to a PyObject: %r" % (ref, )
            raise InvalidPointerException(msg)
    return w_obj


# XXX Optimize these functions and put them into macro definitions
@cpython_api([PyObject], lltype.Void)
def Py_DecRef(space, obj):
    if not obj:
        return
    assert lltype.typeOf(obj) == PyObject

    from pypy.module.cpyext.typeobject import string_dealloc, W_PyCTypeObject
    obj.c_ob_refcnt -= 1
    if DEBUG_REFCOUNT:
        debug_refcount("DECREF", obj, obj.c_ob_refcnt, frame_stackdepth=3)
    if obj.c_ob_refcnt == 0:
        state = space.fromcache(State)
        ptr = rffi.cast(ADDR, obj)
        if ptr not in state.py_objects_r2w:
            w_type = from_ref(space, rffi.cast(PyObject, obj.c_ob_type))
            if space.is_w(w_type, space.w_str) or space.is_w(w_type, space.w_unicode):
                # this is a half-allocated string, lets call the deallocator
                # without modifying the r2w/w2r dicts
                _Py_Dealloc(space, obj)
        else:
            w_obj = state.py_objects_r2w[ptr]
            del state.py_objects_r2w[ptr]
            w_type = space.type(w_obj)
            w_typetype = space.type(w_type)
            if not space.is_w(w_typetype, space.gettypeobject(W_PyCTypeObject.typedef)):
                _Py_Dealloc(space, obj)
            del state.py_objects_w2r[w_obj]
        if ptr in state.borrow_mapping: # move to lifeline __del__
            for containee in state.borrow_mapping[ptr]:
                w_containee = state.py_objects_r2w.get(containee, None)
                if w_containee is not None:
                    containee = state.py_objects_w2r[w_containee]
                    Py_DecRef(space, w_containee)
                    containee_ptr = rffi.cast(ADDR, containee)
                    try:
                        del state.borrowed_objects[containee_ptr]
                    except KeyError:
                        pass
                else:
                    if DEBUG_REFCOUNT:
                        print >>sys.stderr, "Borrowed object is already gone:", \
                                hex(containee)
            del state.borrow_mapping[ptr]
    else:
        if not we_are_translated() and obj.c_ob_refcnt < 0:
            print >>sys.stderr, "Negative refcount for obj %s with type %s" % (obj, rffi.charp2str(obj.c_ob_type.c_tp_name))
            assert False

@cpython_api([PyObject], lltype.Void)
def Py_IncRef(space, obj):
    if not obj:
        return
    obj.c_ob_refcnt += 1
    assert obj.c_ob_refcnt > 0
    if DEBUG_REFCOUNT:
        debug_refcount("INCREF", obj, obj.c_ob_refcnt, frame_stackdepth=3)

def _Py_Dealloc(space, obj):
    from pypy.module.cpyext.api import generic_cpy_call_dont_decref
    pto = obj.c_ob_type
    #print >>sys.stderr, "Calling dealloc slot", pto.c_tp_dealloc, "of", obj, \
    #      "'s type which is", rffi.charp2str(pto.c_tp_name)
    generic_cpy_call_dont_decref(space, pto.c_tp_dealloc, obj)

#___________________________________________________________
# Support for borrowed references

@cpython_api([PyObject], lltype.Void, external=False)
def register_container(space, container):
    state = space.fromcache(State)
    if not container: # self-managed
        container_ptr = -1
    else:
        container_ptr = rffi.cast(ADDR, container)
    assert not state.last_container, "Last container was not fetched"
    state.last_container = container_ptr

def add_borrowed_object(space, obj):
    state = space.fromcache(State)
    container_ptr = state.last_container
    state.last_container = 0
    if not container_ptr:
        raise NullPointerException
    if container_ptr == -1:
        return
    borrowees = state.borrow_mapping.get(container_ptr, None)
    if borrowees is None:
        state.borrow_mapping[container_ptr] = borrowees = {}
    obj_ptr = rffi.cast(ADDR, obj)
    borrowees[obj_ptr] = None


