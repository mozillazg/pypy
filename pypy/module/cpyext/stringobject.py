from pypy.interpreter.error import OperationError
from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import (
    cpython_api, cpython_struct, bootstrap_function, build_type_checkers3,
    PyVarObjectFields, Py_ssize_t, CONST_STRING, CANNOT_FAIL)
from pypy.module.cpyext.pyerrors import PyErr_BadArgument
from pypy.module.cpyext.pyobject import (
    PyObject, PyObjectP, Py_DecRef, get_pyobj_and_incref, from_pyobj,
    setup_class_for_cpyext, RRC_PERMANENT_LIGHT, new_pyobj)
from pypy.objspace.std.bytesobject import W_BytesObject, W_AbstractBytesObject
from pypy.module.cpyext import support

##
## Implementation of PyStringObject
## ================================
##
## The problem
## -----------
##
## PyString_AsString() must return a (non-movable) pointer to the underlying
## buffer, whereas pypy strings are movable (and also, they are not
## null-terminated at all).  The C code may temporarily store
## this address and use it, as long as it owns a reference to the PyObject.
## There is no "release" function to specify that the pointer is not needed
## any more.
##
## Also, the pointer may be used to fill the initial value of string. This is
## valid only when the string was just allocated, and is not used elsewhere.
##
## Solution
## --------
##
## PyStringObject contains two additional members: the size and a pointer to a
## char buffer; it may be NULL.
##
## - A string allocated by pypy will be converted into a PyStringObject with a
##   NULL buffer.  The first time PyString_AsString() is called, memory is
##   allocated (with flavor='raw') and content is copied.
##
## - A string allocated with PyString_FromStringAndSize(NULL, size) will
##   allocate a PyStringObject structure, and a buffer with the specified
##   size, but the reference won't be stored in the global map; there is no
##   corresponding object in pypy.  When from_ref() or Py_INCREF() is called,
##   the pypy string is created, and added to the global map of tracked
##   objects.  The buffer is then supposed to be immutable.
##
## - _PyString_Resize() works only on not-yet-pypy'd strings, and returns a
##   similar object.
##
## - PyString_Size() doesn't need to force the object.
##
## - There could be an (expensive!) check in from_ref() that the buffer still
##   corresponds to the pypy gc-managed string.
##

PyStringObjectStruct = lltype.ForwardReference()
PyStringObject = lltype.Ptr(PyStringObjectStruct)
PyStringObjectFields = PyVarObjectFields + \
    (("ob_sval_pypy", rffi.CArray(lltype.Char)),)
cpython_struct("PyStringObject", PyStringObjectFields, PyStringObjectStruct)

PyString_Check, PyString_CheckExact, _PyString_Type = (
    build_type_checkers3("String", "w_str"))


@bootstrap_function
def init_stringobject(space):
    "Type description of PyStringObject"
    setup_class_for_cpyext(
        W_AbstractBytesObject,
        basestruct=PyStringObjectStruct,

        # --from a W_BytesObject, we call this function to allocate
        #   a PyStringObject, initially without any data--
        alloc_pyobj=string_alloc_pyobj,

        # --reverse direction: from a PyStringObject, we make a W_BytesObject
        #   by instantiating a custom subclass of W_BytesObject--
        realize_subclass_of=W_BytesObject,

        # --and then we call this function to initialize the W_BytesObject--
        fill_pypy=string_fill_pypy,

        # --in this case, and if PyString_CheckExact() returns True, then
        #   the link can be light, i.e. the original PyStringObject might
        #   be freed with free() by the GC--
        alloc_pypy_light_if=PyString_CheckExact,
        )
    W_BytesObject.typedef.cpyext_basicsize += 1    # includes the final NULL

def _string_fill_pyobj(s, ob):
    rffi.str2chararray(s, ob.c_ob_sval_pypy, len(s))
    ob.c_ob_sval_pypy[len(s)] = '\x00'

def string_alloc_pyobj(space, w_obj):
    """
    Makes a PyStringObject from a W_AbstractBytesObject.
    """
    assert isinstance(w_obj, W_AbstractBytesObject)
    size = w_obj.string_length()
    ob = lltype.malloc(PyStringObjectStruct, size + 1, flavor='raw',
                       track_allocation=False)
    ob.c_ob_size = size
    if size > 8:
        ob.c_ob_sval_pypy[size] = '*'    # not filled yet
    else:
        _string_fill_pyobj(w_obj.str_w(space), ob)
    return ob, RRC_PERMANENT_LIGHT

def string_fill_pypy(space, w_obj, py_obj):
    """
    Creates the string in the interpreter. The PyStringObject buffer must not
    be modified after this call.
    """
    py_str = rffi.cast(PyStringObject, py_obj)
    s = rffi.charpsize2str(rffi.cast(rffi.CCHARP, py_str.c_ob_sval_pypy),
                           py_str.c_ob_size)
    W_BytesObject.__init__(w_obj, s)

#_______________________________________________________________________

def new_empty_str(space, length):
    """
    Allocates an uninitialized PyStringObject.  The string may be mutated
    as long as it has a refcount of 1; notably, until string_fill_pypy() is
    called.
    """
    py_str = new_pyobj(PyStringObjectStruct, _PyString_Type(space), length + 1)
    py_str.c_ob_size = length
    py_str.c_ob_sval_pypy[length] = '\x00'
    return py_str

@cpython_api([CONST_STRING, Py_ssize_t], PyObject)
def PyString_FromStringAndSize(space, char_p, length):
    # XXX move to C
    py_str = new_empty_str(space, length)
    if char_p:
        py_str = rffi.cast(PyStringObject, py_str)    # needed for ll2ctypes
        support.memcpy_fn(py_str.c_ob_sval_pypy, char_p, length)
    return rffi.cast(PyObject, py_str)

@cpython_api([CONST_STRING], PyObject)
def PyString_FromString(space, char_p):
    # is it better to make an RPython object and lazily copy data to
    # the C string, or make a purely C PyStringObject and then usually
    # copy the string again to RPython?  no clue...  ideally, we should
    # measure and adapt dynamically
    s = rffi.charp2str(char_p)
    return space.wrap(s)

@cpython_api([PyObject], rffi.CCHARP, error=0)
def PyString_AsString(space, ref):
    if not PyString_Check(space, ref):
        raise OperationError(space.w_TypeError, space.wrap(
            "PyString_AsString only supports strings"))
    ref_str = rffi.cast(PyStringObject, ref)
    last_char = ref_str.c_ob_sval_pypy[ref_str.c_ob_size]
    if last_char != '\x00':
        assert last_char == '*'
        # copy string buffer
        w_str = from_pyobj(space, ref)
        _string_fill_pyobj(w_str.str_w(space), ref_str)
        ref_str.c_ob_sval_pypy[ref_str.c_ob_size] = '\x00'
    return rffi.cast(rffi.CCHARP, ref_str.c_ob_sval_pypy)

@cpython_api([PyObject, rffi.CCHARPP, rffi.CArrayPtr(Py_ssize_t)], rffi.INT_real, error=-1)
def PyString_AsStringAndSize(space, ref, buffer, length):
    buffer[0] = PyString_AsString(space, ref)
    ref_str = rffi.cast(PyStringObject, ref)
    if length:
        length[0] = ref_str.c_ob_size
    else:
        i = 0
        while ref_str.c_ob_sval_pypy[i] != '\0':
            i += 1
        if i != ref_str.c_ob_size:
            raise OperationError(space.w_TypeError, space.wrap(
                "expected string without null bytes"))
    return 0

@cpython_api([PyObject], Py_ssize_t, error=-1)
def PyString_Size(space, ref):
    if PyString_Check(space, ref):
        ref = rffi.cast(PyStringObject, ref)
        return ref.c_ob_size
    else:
        w_obj = from_pyobj(space, ref)
        return space.len_w(w_obj)

@cpython_api([PyObject, PyObject], rffi.INT, error=CANNOT_FAIL)
def _PyString_Eq(space, w_str1, w_str2):
    return space.eq_w(w_str1, w_str2)

@cpython_api([PyObjectP, PyObject], lltype.Void)
def PyString_Concat(space, ref, w_newpart):
    """Create a new string object in *string containing the contents of newpart
    appended to string; the caller will own the new reference.  The reference to
    the old value of string will be stolen.  If the new string cannot be created,
    the old reference to string will still be discarded and the value of
    *string will be set to NULL; the appropriate exception will be set."""

    if not ref[0]:
        return

    if w_newpart is None or not PyString_Check(space, ref[0]) or \
            not PyString_Check(space, w_newpart):
        Py_DecRef(space, ref[0])
        ref[0] = lltype.nullptr(PyObject.TO)
        return
    w_str = from_pyobj(space, ref[0])
    w_newstr = space.add(w_str, w_newpart)
    Py_DecRef(space, ref[0])
    ref[0] = get_pyobj_and_incref(space, w_newstr)

@cpython_api([PyObjectP, PyObject], lltype.Void)
def PyString_ConcatAndDel(space, ref, newpart):
    """Create a new string object in *string containing the contents of newpart
    appended to string.  This version decrements the reference count of newpart."""
    PyString_Concat(space, ref, newpart)
    Py_DecRef(space, newpart)

@cpython_api([PyObject, PyObject], PyObject)
def PyString_Format(space, w_format, w_args):
    """Return a new string object from format and args. Analogous to format %
    args.  The args argument must be a tuple."""
    return space.mod(w_format, w_args)

@cpython_api([CONST_STRING], PyObject)
def PyString_InternFromString(space, string):
    """A combination of PyString_FromString() and
    PyString_InternInPlace(), returning either a new string object that has
    been interned, or a new ("owned") reference to an earlier interned string
    object with the same value."""
    s = rffi.charp2str(string)
    return space.new_interned_str(s)

@cpython_api([PyObjectP], lltype.Void)
def PyString_InternInPlace(space, string):
    """Intern the argument *string in place.  The argument must be the
    address of a pointer variable pointing to a Python string object.
    If there is an existing interned string that is the same as
    *string, it sets *string to it (decrementing the reference count
    of the old string object and incrementing the reference count of
    the interned string object), otherwise it leaves *string alone and
    interns it (incrementing its reference count).  (Clarification:
    even though there is a lot of talk about reference counts, think
    of this function as reference-count-neutral; you own the object
    after the call if and only if you owned it before the call.)

    This function is not available in 3.x and does not have a PyBytes
    alias."""
    w_str = from_pyobj(space, string[0])
    w_str = space.new_interned_w_str(w_str)
    Py_DecRef(space, string[0])
    string[0] = get_pyobj_and_incref(space, w_str)

@cpython_api([PyObject, CONST_STRING, CONST_STRING], PyObject)
def PyString_AsEncodedObject(space, w_str, encoding, errors):
    """Encode a string object using the codec registered for encoding and return
    the result as Python object. encoding and errors have the same meaning as
    the parameters of the same name in the string encode() method. The codec to
    be used is looked up using the Python codec registry. Return NULL if an
    exception was raised by the codec.

    This function is not available in 3.x and does not have a PyBytes alias."""
    if not PyString_Check(space, w_str):
        PyErr_BadArgument(space)

    w_encoding = w_errors = space.w_None
    if encoding:
        w_encoding = space.wrap(rffi.charp2str(encoding))
    if errors:
        w_errors = space.wrap(rffi.charp2str(errors))
    return space.call_method(w_str, 'encode', w_encoding, w_errors)

@cpython_api([PyObject, CONST_STRING, CONST_STRING], PyObject)
def PyString_AsDecodedObject(space, w_str, encoding, errors):
    """Decode a string object by passing it to the codec registered
    for encoding and return the result as Python object. encoding and
    errors have the same meaning as the parameters of the same name in
    the string encode() method.  The codec to be used is looked up
    using the Python codec registry. Return NULL if an exception was
    raised by the codec.

    This function is not available in 3.x and does not have a PyBytes alias."""
    if not PyString_Check(space, w_str):
        PyErr_BadArgument(space)

    w_encoding = w_errors = space.w_None
    if encoding:
        w_encoding = space.wrap(rffi.charp2str(encoding))
    if errors:
        w_errors = space.wrap(rffi.charp2str(errors))
    return space.call_method(w_str, "decode", w_encoding, w_errors)

@cpython_api([PyObject, PyObject], PyObject)
def _PyString_Join(space, w_sep, w_seq):
    return space.call_method(w_sep, 'join', w_seq)
