
from pypy.module.cpyext.api import cpython_api, PyObject, CANNOT_FAIL, va_list,\
     cpython_api_c
from pypy.module.cpyext import api
from pypy.rpython.lltypesystem import lltype, rffi

@cpython_api_c()
def PyArg_Parse():
    pass

@cpython_api([PyObject, rffi.CCHARP, lltype.Ptr(va_list), rffi.INT_real],
             rffi.INT_real, error=-1)
def pypy_vgetargs1(space, w_obj, fmt, va_list_p, lgt):
    i = 0
    raise Exception("This is broken so far")
    while True:
        c = fmt[i]
        if c == "\x00":
            return 0
        if c == "i":
            pyobj = api.va_get_PyObject(va_list_p);
        i += 1
    return 0
