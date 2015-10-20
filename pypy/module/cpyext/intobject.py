
from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.interpreter.error import OperationError
from pypy.module.cpyext.api import (
    cpython_api, cpython_struct, build_type_checkers3, bootstrap_function,
    PyObject, PyObjectFields, CONST_STRING, CANNOT_FAIL, Py_ssize_t)
from pypy.module.cpyext.pyobject import (setup_class_for_cpyext, new_pyobj,
                                         from_pyobj, get_pyobj_and_incref)
from rpython.rlib.rarithmetic import r_uint, intmask, LONG_TEST, r_ulonglong
from pypy.objspace.std.intobject import W_IntObject
import sys

PyIntObjectStruct = lltype.ForwardReference()
PyIntObject = lltype.Ptr(PyIntObjectStruct)
PyIntObjectFields = PyObjectFields + \
    (("ob_ival", rffi.LONG),)
cpython_struct("PyIntObject", PyIntObjectFields, PyIntObjectStruct)

PyInt_Check, PyInt_CheckExact, _PyInt_Type = build_type_checkers3("Int")


@bootstrap_function
def init_intobject(space):
    "Type description of PyIntObject"
    from pypy.objspace.std.intobject import W_AbstractIntObject, W_IntObject
    setup_class_for_cpyext(
        # --the base class of all 'int' objects inside PyPy--
        W_AbstractIntObject,

        # --the structure type derived from PyObject--
        basestruct=PyIntObjectStruct,

        # --from a W_IntObject, we allocate a PyIntObject and then we
        #   call this function to fill it.  It gets attached as
        #   RRC_PERMANENT_LIGHT by default, which means the
        #   association is permanent (the PyIntObject is alive and
        #   won't appear to move as long as the W_IntObject is alive)
        #   and light (the PyIntObject can be freed with free()).--
        fill_pyobj=int_fill_pyobj,

        # --reverse direction: from a PyIntObject, we make a W_IntObject
        #   by instantiating a custom subclass of W_IntObject--
        realize_subclass_of=W_IntObject,

        # --and then we call this function to initialize the W_IntObject--
        fill_pypy=int_fill_pypy,

        # --in this case, and if PyInt_CheckExact() returns True, then
        #   the link can be light, i.e. the original PyIntObject might
        #   be freed with free() by the GC--
        alloc_pypy_light_if=PyInt_CheckExact,
        )

def int_fill_pyobj(space, w_obj, py_int):
    """
    Fills a newly allocated PyIntObject with the given int object. The
    value must not be modified.
    """
    py_int.c_ob_ival = space.int_w(w_obj)

def int_fill_pypy(space, w_obj, py_obj):
    """
    Fills a W_IntObject from a PyIntObject.
    """
    py_int = rffi.cast(PyIntObject, py_obj)
    intval = rffi.cast(lltype.Signed, py_int.c_ob_ival)
    W_IntObject.__init__(w_obj, intval)


@cpython_api([], lltype.Signed, error=CANNOT_FAIL)
def PyInt_GetMax(space):
    """Return the system's idea of the largest integer it can handle (LONG_MAX,
    as defined in the system header files)."""
    return sys.maxint

def new_pyint(space, ival):
    py_int = new_pyobj(PyIntObjectStruct, _PyInt_Type(space))
    py_int.c_ob_ival = ival
    return rffi.cast(PyObject, py_int)

@cpython_api([lltype.Signed], PyObject)
def PyInt_FromLong(space, ival):
    """Create a new integer object with a value of ival.
    """
    return new_pyint(space, ival)

@cpython_api([PyObject], lltype.Signed, error=-1)
def PyInt_AsLong(space, py_obj):
    """Will first attempt to cast the object to a PyIntObject, if it is not
    already one, and then return its value. If there is an error, -1 is
    returned, and the caller should check PyErr_Occurred() to find out whether
    there was an error, or whether the value just happened to be -1."""
    if not py_obj:
        raise OperationError(space.w_TypeError,
                             space.wrap("an integer is required, got NULL"))
    if PyInt_Check(space, py_obj):
        return _PyInt_AS_LONG(py_obj)
    else:
        w_obj = from_pyobj(space, py_obj)
        return space.int_w(space.int(w_obj))   # XXX win64: check range

@cpython_api([PyObject], lltype.Unsigned, error=-1)
def PyInt_AsUnsignedLong(space, w_obj):
    """Return a C unsigned long representation of the contents of pylong.
    If pylong is greater than ULONG_MAX, an OverflowError is
    raised.  (NOT ON CPYTHON)"""
    if w_obj is None:
        raise OperationError(space.w_TypeError,
                             space.wrap("an integer is required, got NULL"))
    return space.uint_w(space.int(w_obj))


@cpython_api([PyObject], rffi.ULONG, error=-1)
def PyInt_AsUnsignedLongMask(space, py_obj):
    """Will first attempt to cast the object to a PyIntObject or
    PyLongObject, if it is not already one, and then return its value as
    unsigned long.  This function does not check for overflow.
    """
    if not py_obj:
        raise OperationError(space.w_TypeError,
                             space.wrap("an integer is required, got NULL"))
    if PyInt_Check(space, py_obj):
        return rffi.cast(rffi.ULONG, _PyInt_AS_LONG(py_obj))
    else:
        w_obj = from_pyobj(space, py_obj)
        num = space.bigint_w(space.int(w_obj))
        return num.uintmask()


@cpython_api([PyObject], rffi.ULONGLONG, error=-1)
def PyInt_AsUnsignedLongLongMask(space, py_obj):
    """Will first attempt to cast the object to a PyIntObject or
    PyLongObject, if it is not already one, and then return its value as
    unsigned long long, without checking for overflow.
    """
    if not py_obj:
        raise OperationError(space.w_TypeError,
                             space.wrap("an integer is required, got NULL"))
    if PyInt_Check(space, py_obj):
        return rffi.cast(rffi.ULONGLONG, _PyInt_AS_LONG(py_obj))
    else:
        w_obj = from_pyobj(space, py_obj)
        num = space.bigint_w(space.int(w_obj))
        return num.ulonglongmask()


def _PyInt_AS_LONG(py_obj):
    """Return the value of the object w_int. No error checking is performed."""
    py_int = rffi.cast(PyIntObject, py_obj)
    return py_int.c_ob_ival

@cpython_api([PyObject], Py_ssize_t, error=-1)
def PyInt_AsSsize_t(space, py_obj):
    """Will first attempt to cast the object to a PyIntObject or
    PyLongObject, if it is not already one, and then return its value as
    Py_ssize_t.
    """
    if not py_obj:
        raise OperationError(space.w_TypeError,
                             space.wrap("an integer is required, got NULL"))
    if PyInt_Check(space, py_obj):
        return rffi.cast(Py_ssize_t, _PyInt_AS_LONG(py_obj))
    else:
        w_obj = from_pyobj(space, py_obj)
        return space.int_w(space.int(w_obj))

LONG_MAX = int(LONG_TEST - 1)

@cpython_api([rffi.SIZE_T], PyObject)
def PyInt_FromSize_t(space, ival):
    """Create a new integer object with a value of ival. If the value exceeds
    LONG_MAX, a long integer object is returned.
    """
    if ival <= LONG_MAX:
        return new_pyint(rffi.cast(rffi.LONG, ival))
    else:
        return get_pyobj_and_incref(space.wrap(ival))

@cpython_api([Py_ssize_t], PyObject)
def PyInt_FromSsize_t(space, ival):
    """Create a new integer object with a value of ival. If the value is larger
    than LONG_MAX or smaller than LONG_MIN, a long integer object is
    returned.
    """
    # XXX win64
    return new_pyint(ival)

@cpython_api([CONST_STRING, rffi.CCHARPP, rffi.INT_real], PyObject)
def PyInt_FromString(space, str, pend, base):
    """Return a new PyIntObject or PyLongObject based on the string
    value in str, which is interpreted according to the radix in base.  If
    pend is non-NULL, *pend will point to the first character in str which
    follows the representation of the number.  If base is 0, the radix will be
    determined based on the leading characters of str: if str starts with
    '0x' or '0X', radix 16 will be used; if str starts with '0', radix
    8 will be used; otherwise radix 10 will be used.  If base is not 0, it
    must be between 2 and 36, inclusive.  Leading spaces are ignored.  If
    there are no digits, ValueError will be raised.  If the string represents
    a number too large to be contained within the machine's long int type
    and overflow warnings are being suppressed, a PyLongObject will be
    returned.  If overflow warnings are not being suppressed, NULL will be
    returned in this case."""
    s = rffi.charp2str(str)
    w_str = space.wrap(s)
    w_base = space.wrap(rffi.cast(lltype.Signed, base))
    if pend:
        pend[0] = rffi.ptradd(str, len(s))
    return space.call_function(space.w_int, w_str, w_base)
