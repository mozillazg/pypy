from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import cpython_api, PyObject, Py_ssize_t, \
        general_check, CANNOT_FAIL
from pypy.module.cpyext.macros import Py_DECREF
from pypy.module.cpyext.pyerrors import PyErr_BadInternalCall
from pypy.objspace.std.tupleobject import W_TupleObject

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyTuple_Check(space, w_obj):
    w_type = space.w_tuple
    return general_check(space, w_obj, w_type)

@cpython_api([Py_ssize_t], PyObject)
def PyTuple_New(space, size):
    return space.newtuple([space.w_None] * size)

@cpython_api([PyObject, Py_ssize_t, PyObject], rffi.INT_real, error=-1)
def PyTuple_SetItem(space, w_t, pos, w_obj):
    if not PyTuple_Check(space, w_t):
        PyErr_BadInternalCall(space)
    assert isinstance(w_t, W_TupleObject)
    w_t.wrappeditems[pos] = w_obj
    Py_DECREF(space, w_obj) # SetItem steals a reference! XXX this needs to go into the wrapper
    return 0

@cpython_api([PyObject, Py_ssize_t], PyObject, borrowed=True)
def PyTuple_GetItem(space, w_t, pos):
    if not PyTuple_Check(space, w_t):
        PyErr_BadInternalCall(space)
    assert isinstance(w_t, W_TupleObject)
    w_obj = w_t.wrappeditems[pos]
    return w_obj
