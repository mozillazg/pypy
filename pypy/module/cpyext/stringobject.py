from pypy.rpython.lltypesystem import rffi
from pypy.module.cpyext.api import cpython_api, PyObject, Py_ssize_t

@cpython_api([rffi.CCHARP, Py_ssize_t], PyObject)
def PyString_FromStringAndSize(space, char_p, length):
    s = rffi.charpsize2str(char_p, length)
    return space.wrap(s)

@cpython_api([rffi.CCHARP], PyObject)
def PyString_FromString(space, char_p):
    s = rffi.charp2str(char_p)
    return space.wrap(s)

@cpython_api([PyObject], Py_ssize_t, error=-1)
def PyString_Size(space, w_obj):
    return space.int_w(space.len(w_obj))
