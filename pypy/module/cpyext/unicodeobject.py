from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.unicodedata import unicodedb_4_1_0 as unicodedb
from pypy.module.cpyext.api import (CANNOT_FAIL, Py_ssize_t, PyUnicodeObject,
                                    build_type_checkers, cpython_api)
from pypy.module.cpyext.pyobject import PyObject, from_ref
from pypy.objspace.std import unicodeobject

PyUnicode_Check, PyUnicode_CheckExact = build_type_checkers("Unicode", "w_unicode")

# XXX
Py_UNICODE = rffi.UINT

@cpython_api([Py_UNICODE], rffi.INT_real, error=CANNOT_FAIL)
def Py_UNICODE_ISSPACE(space, w_ch):
    """Return 1 or 0 depending on whether ch is a whitespace character."""
    return unicodedb.isspace(w_ch)

@cpython_api([Py_UNICODE], rffi.INT_real, error=CANNOT_FAIL)
def Py_UNICODE_ISALNUM(space, w_ch):
    """Return 1 or 0 depending on whether ch is an alphanumeric character."""
    return unicodedb.isalnum(w_ch)

@cpython_api([Py_UNICODE], rffi.INT_real, error=CANNOT_FAIL)
def Py_UNICODE_ISLINEBREAK(space, w_ch):
    """Return 1 or 0 depending on whether ch is a linebreak character."""
    return unicodedb.islinebreak(w_ch)

@cpython_api([Py_UNICODE], rffi.INT_real, error=CANNOT_FAIL)
def Py_UNICODE_ISSPACE(space, w_ch):
    """Return 1 or 0 depending on whether ch is a whitespace character."""
    return unicodedb.isspace(w_ch)

@cpython_api([Py_UNICODE], rffi.INT_real, error=CANNOT_FAIL)
def Py_UNICODE_ISALNUM(space, w_ch):
    """Return 1 or 0 depending on whether ch is an alphanumeric character."""
    return unicodedb.isalnum(w_ch)

@cpython_api([Py_UNICODE], rffi.INT_real, error=CANNOT_FAIL)
def Py_UNICODE_ISDECIMAL(space, w_ch):
    """Return 1 or 0 depending on whether ch is a decimal character."""
    return unicodedb.isdecimal(w_ch)

@cpython_api([Py_UNICODE], rffi.INT_real, error=CANNOT_FAIL)
def Py_UNICODE_ISLOWER(space, w_ch):
    """Return 1 or 0 depending on whether ch is a lowercase character."""
    return unicodedb.islower(w_ch)

@cpython_api([Py_UNICODE], rffi.INT_real, error=CANNOT_FAIL)
def Py_UNICODE_ISUPPER(space, w_ch):
    """Return 1 or 0 depending on whether ch is an uppercase character."""
    return unicodedb.isupper(w_ch)

@cpython_api([Py_UNICODE], Py_UNICODE, error=CANNOT_FAIL)
def Py_UNICODE_TOLOWER(space, w_ch):
    """Return the character ch converted to lower case."""
    return unicodedb.tolower(w_ch)

@cpython_api([PyObject], rffi.CCHARP, error=CANNOT_FAIL)
def PyUnicode_AS_DATA(space, ref):
    """Return a pointer to the internal buffer of the object. o has to be a
    PyUnicodeObject (not checked)."""
    ref_unicode = rffi.cast(PyUnicodeObject, ref)
    if not ref_unicode.c_buffer:
        # Copy unicode buffer
        w_unicode = from_ref(space, ref)
        u = space.unicode_w(w_unicode)
        ref_unicode.c_buffer = rffi.cast(rffi.VOIDP, rffi.unicode2wcharp(u))
    return rffi.cast(rffi.CCHARP, ref_unicode.c_buffer)

@cpython_api([PyObject], Py_ssize_t, error=CANNOT_FAIL)
def PyUnicode_GET_DATA_SIZE(space, obj):
    """Return the size of the object's internal buffer in bytes.  o has to be a
    PyUnicodeObject (not checked)."""
    return rffi.sizeof(lltype.UniChar) * (PyUnicode_GET_SIZE(space, obj) + 1)

@cpython_api([PyObject], Py_ssize_t, error=CANNOT_FAIL)
def PyUnicode_GET_SIZE(space, w_obj):
    """Return the size of the object.  o has to be a PyUnicodeObject (not
    checked).

    This function returned an int type. This might require changes
    in your code for properly supporting 64-bit systems."""
    assert isinstance(w_obj, unicodeobject.W_UnicodeObject)
    return space.len(w_obj)
