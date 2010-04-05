
from pypy.module.cpyext.api import cpython_api, PyObject, CANNOT_FAIL, \
     VA_LIST_P, cpython_api_c
from pypy.module.cpyext import api
from pypy.rpython.lltypesystem import lltype, rffi

@cpython_api_c()
def PyArg_Parse():
    pass

@cpython_api_c()
def PyArg_ParseTuple():
    pass

@cpython_api_c()
def PyArg_UnpackTuple():
    pass

@cpython_api([PyObject, rffi.CCHARP, VA_LIST_P, rffi.INT_real],
             rffi.INT_real, error=0)
def pypy_vgetargs1(space, w_obj, fmt, va_list_p, flags):
    i = 0
    while True:
        c = fmt[i]
        if c == "\x00":
            return 1
        elif c == "i":
            arr = api.va_get_int_star(va_list_p)
            arr[0] = rffi.cast(rffi.INT,
                               space.int_w(space.getitem(w_obj, space.wrap(i))))
        elif c == ':':
            return 1
        else:
            raise Exception("Unsupported parameter: %s" % (c,))
        i += 1
