from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import ObjSpace
from pypy.module.trans import rtrans

def begin(space):
    rtrans.begin()
    return space.w_None

def end(space):
    rtrans.end()
    return space.w_None

def abort(space):
    rtrans.abort()
    return space.w_None

def pause(space):
    rtrans.pause()
    return space.w_None

def unpause(space):
    rtrans.unpause()
    return space.w_None

def verbose(space):
    rtrans.verbose()
    return space.w_None

def is_active(space):
    return space.wrap(rtrans.is_active())

def reset_stats(space):
    rtrans.reset_stats()
    return space.w_None
