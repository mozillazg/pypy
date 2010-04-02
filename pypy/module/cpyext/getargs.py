
from pypy.module.cpyext.api import cpython_api, PyObject, CANNOT_FAIL, \
     VA_LIST_P, cpython_api_c
from pypy.module.cpyext import api
from pypy.rpython.lltypesystem import lltype, rffi

@cpython_api_c()
def PyArg_Parse():
    pass

@cpython_api([PyObject, rffi.CCHARP, VA_LIST_P, rffi.INT_real],
             rffi.INT_real, error=-1)
def pypy_vgetargs1(space, w_obj, fmt, va_list_p, lgt):
    i = 0
    while True:
        c = fmt[i]
        if c == "\x00":
            return 0
        if c == "i":
            #pyobj = api.va_get_int_star(va_list_p)
            # XXX processs....
            pass
        i += 1
    return 0
