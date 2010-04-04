from pypy.rpython.lltypesystem import rffi
from pypy.module.unicodedata import unicodedb_4_1_0 as unicodedb
from pypy.module.cpyext.api import CANNOT_FAIL, build_type_checkers, cpython_api

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
