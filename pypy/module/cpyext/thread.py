
from pypy.module.thread import os_thread
from pypy.module.cpyext.api import CANNOT_FAIL, cpython_api
from pypy.rpython.lltypesystem import rffi

@cpython_api([], rffi.LONG, error=CANNOT_FAIL)
def PyThread_get_thread_ident(space):
    return os_thread.get_ident(space)
