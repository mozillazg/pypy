from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import cpython_api, generic_cpy_call, CANNOT_FAIL,\
        Py_ssize_t, PyVarObject, Py_TPFLAGS_HEAPTYPE
from pypy.module.cpyext.pyobject import PyObject, make_ref, from_ref
from pypy.module.cpyext.pyobject import Py_IncRef, Py_DecRef
from pypy.module.cpyext.state import State
from pypy.module.cpyext.typeobject import PyTypeObjectPtr, W_PyCTypeObject
from pypy.module.cpyext.pyerrors import PyErr_NoMemory
from pypy.objspace.std.objectobject import W_ObjectObject
from pypy.objspace.std.typeobject import W_TypeObject
import pypy.module.__builtin__.operation as operation


@cpython_api([PyTypeObjectPtr], PyObject)
def _PyObject_New(space, type):
    return _PyObject_NewVar(space, type, 0)

@cpython_api([PyTypeObjectPtr, Py_ssize_t], PyObject)
def _PyObject_NewVar(space, type, size):
    w_type = from_ref(space, rffi.cast(PyObject, type))
    if isinstance(w_type, W_PyCTypeObject):
        w_obj = space.allocate_instance(W_ObjectObject, w_type)
        return make_ref(space, w_obj, items=size)
    assert False, "Please add more cases in _PyObject_New"

@cpython_api([rffi.VOIDP_real], lltype.Void)
def PyObject_Del(space, obj):
    lltype.free(obj, flavor='raw')

@cpython_api([PyObject], lltype.Void)
def PyObject_dealloc(space, obj):
    pto = rffi.cast(PyTypeObjectPtr, obj.c_ob_type)
    obj_voidp = rffi.cast(rffi.VOIDP_real, obj)
    generic_cpy_call(space, pto.c_tp_free, obj_voidp)
    if pto.c_tp_flags & Py_TPFLAGS_HEAPTYPE:
        Py_DecRef(space, rffi.cast(PyObject, obj.c_ob_type))

@cpython_api([PyObject], rffi.INT_real, error=-1)
def PyObject_IsTrue(space, w_obj):
    return space.is_true(w_obj)

@cpython_api([PyObject], rffi.INT_real, error=-1)
def PyObject_Not(space, w_obj):
    return not space.is_true(w_obj)

@cpython_api([PyObject, rffi.CCHARP], PyObject)
def PyObject_GetAttrString(space, w_obj, name_ptr):
    """Retrieve an attribute named attr_name from object o. Returns the attribute
    value on success, or NULL on failure. This is the equivalent of the Python
    expression o.attr_name."""
    name = rffi.charp2str(name_ptr)
    return space.getattr(w_obj, space.wrap(name))

@cpython_api([PyObject, PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyObject_HasAttr(space, w_obj, w_name):
    w_res = operation.hasattr(space, w_obj, w_name)
    return space.is_true(w_res)

@cpython_api([PyObject, PyObject, PyObject], rffi.INT_real, error=-1)
def PyObject_SetAttr(space, w_obj, w_name, w_value):
    operation.setattr(space, w_obj, w_name, w_value)
    return 0

@cpython_api([PyObject], lltype.Void)
def PyObject_ClearWeakRefs(space, w_object):
    w_object.clear_all_weakrefs()

@cpython_api([PyObject], Py_ssize_t, error=-1)
def PyObject_Size(space, w_obj):
    return space.int_w(space.len(w_obj))

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyCallable_Check(space, w_obj):
    """Determine if the object o is callable.  Return 1 if the object is callable
    and 0 otherwise.  This function always succeeds."""
    return int(space.is_true(space.callable(w_obj)))

@cpython_api([PyObject, PyObject], PyObject)
def PyObject_GetItem(space, w_obj, w_key):
    """Return element of o corresponding to the object key or NULL on failure.
    This is the equivalent of the Python expression o[key]."""
    return space.getitem(w_obj, w_key)

@cpython_api([PyObject, PyTypeObjectPtr], PyObject, borrowed=True)
def PyObject_Init(space, op, type):
    """Initialize a newly-allocated object op with its type and initial
    reference.  Returns the initialized object.  If type indicates that the
    object participates in the cyclic garbage detector, it is added to the
    detector's set of observed objects. Other fields of the object are not
    affected."""
    if not op:
        PyErr_NoMemory(space)
    op.c_ob_type = type
    op.c_ob_refcnt = 1
    return from_ref(space, op) # XXX will give an exception

@cpython_api([PyVarObject, PyTypeObjectPtr, Py_ssize_t], PyObject, borrowed=True)
def PyObject_InitVar(space, op, type, size):
    """This does everything PyObject_Init() does, and also initializes the
    length information for a variable-size object."""
    if not op:
        PyErr_NoMemory(space)
    op.c_ob_size = size
    op.c_ob_type = type
    op.c_ob_refcnt = 1
    return from_ref(space, rffi.cast(PyObject, op)) # XXX likewise

@cpython_api([PyObject], PyObject)
def PyObject_Repr(space, w_obj):
    """Compute a string representation of object o.  Returns the string
    representation on success, NULL on failure.  This is the equivalent of the
    Python expression repr(o).  Called by the repr() built-in function and
    by reverse quotes."""
    return space.repr(w_obj)
