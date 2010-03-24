from pypy.rpython.lltypesystem import rffi, lltype
from pypy.interpreter.error import OperationError
from pypy.module.cpyext.api import cpython_api, PyObject, make_ref
from pypy.module.cpyext.state import State

@cpython_api([PyObject, rffi.CCHARP], lltype.Void)
def PyErr_SetString(space, w_type, message_ptr):
    message = rffi.charp2str(message_ptr)
    state = space.fromcache(State)
    state.exc_type = w_type
    state.exc_value = space.call_function(w_type, space.wrap(message))

@cpython_api([], PyObject)
def PyErr_Occurred(space):
    state = space.fromcache(State)
    return state.exc_value

@cpython_api([], lltype.Void)
def PyErr_Clear(space):
    state = space.fromcache(State)
    state.exc_type = None
    state.exc_value = None

@cpython_api([], lltype.Void)
def PyErr_BadInternalCall(space):
    raise OperationError(space.w_SystemError, space.wrap("Bad internal call!"))

