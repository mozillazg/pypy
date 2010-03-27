from pypy.rpython.lltypesystem import rffi, lltype
from pypy.interpreter.error import OperationError
from pypy.module.cpyext.api import cpython_api, PyObject, make_ref,\
        register_container
from pypy.module.cpyext.state import State

@cpython_api([PyObject, rffi.CCHARP], lltype.Void)
def PyErr_SetString(space, w_type, message_ptr):
    message = rffi.charp2str(message_ptr)
    state = space.fromcache(State)
    state.set_exception(w_type, space.wrap(message))

@cpython_api([], PyObject, borrowed=True)
def PyErr_Occurred(space):
    state = space.fromcache(State)
    register_container(space, None)
    return state.exc_value

@cpython_api([], lltype.Void)
def PyErr_Clear(space):
    state = space.fromcache(State)
    state.clear_exception()

@cpython_api([], lltype.Void)
def PyErr_BadInternalCall(space):
    raise OperationError(space.w_SystemError, space.wrap("Bad internal call!"))

