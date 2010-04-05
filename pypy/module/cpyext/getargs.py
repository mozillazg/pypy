from pypy.interpreter.error import OperationError
from pypy.module.cpyext.api import cpython_api, PyObject, CANNOT_FAIL, \
     VA_LIST_P, cpython_api_c
from pypy.module.cpyext import api
from pypy.module.cpyext.pyobject import from_ref, make_ref,\
     add_borrowed_object, register_container
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
    arg_i = 0
    fmt_i = 0
    while True:
        c = fmt[fmt_i]
        if c == "\x00":
            return 1
        elif c == "i":
            arr = api.va_get_int_star(va_list_p)
            arr[0] = rffi.cast(rffi.INT,
                               space.int_w(space.getitem(w_obj, space.wrap(arg_i))))
        elif c == "O":
            w_item = space.getitem(w_obj, space.wrap(arg_i))
            if fmt[fmt_i + 1] == "!":
                fmt_i += 1
                w_type = from_ref(space, api.va_get_PyObject_star(va_list_p))
                if not space.is_true(space.isinstance(w_item, w_type)):
                    raise OperationError(space.w_TypeError,
                                         space.wrap("wrong type"))
            arr = api.va_get_PyObject_star_star(va_list_p)
            arr[0] = make_ref(space, w_item, borrowed=True)
            register_container(space, w_obj)
            add_borrowed_object(space, arr[0])
        elif c == ':':
            return 1
        else:
            raise Exception("Unsupported parameter: %s" % (c,))
        arg_i += 1
        fmt_i += 1
