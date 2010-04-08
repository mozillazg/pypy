
@cpython_api([PyTypeObjectPtr, Py_ssize_t], PyObject)
def _PyObject_NewVar(space, type, size):
    """This function used an int type for size. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject], lltype.Void)
def _PyObject_Del(space, op):
    raise NotImplementedError

@cpython_api([PyObject, PyTypeObjectPtr], PyObject, borrowed=True)
def PyObject_Init(space, op, type):
    """Initialize a newly-allocated object op with its type and initial
    reference.  Returns the initialized object.  If type indicates that the
    object participates in the cyclic garbage detector, it is added to the
    detector's set of observed objects. Other fields of the object are not
    affected."""
    raise NotImplementedError

@cpython_api([PyObject, PyTypeObjectPtr, Py_ssize_t], PyObject, borrowed=True)
def PyObject_InitVar(space, op, type, size):
    """This does everything PyObject_Init() does, and also initializes the
    length information for a variable-size object.
    
    This function used an int type for size. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([{TYPE}, PyTypeObjectPtr], {TYPE*})
def PyObject_New(space, , type):
    """Allocate a new Python object using the C structure type TYPE and the
    Python type object type.  Fields not defined by the Python object header
    are not initialized; the object's reference count will be one.  The size of
    the memory allocation is determined from the tp_basicsize field of
    the type object."""
    raise NotImplementedError

@cpython_api([{TYPE}, PyTypeObjectPtr, Py_ssize_t], {TYPE*})
def PyObject_NewVar(space, , type, size):
    """Allocate a new Python object using the C structure type TYPE and the
    Python type object type.  Fields not defined by the Python object header
    are not initialized.  The allocated memory allows for the TYPE structure
    plus size fields of the size given by the tp_itemsize field of
    type.  This is useful for implementing objects like tuples, which are
    able to determine their size at construction time.  Embedding the array of
    fields into the same allocation decreases the number of allocations,
    improving the memory management efficiency.
    
    This function used an int type for size. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, PyMethodDef], PyObject, borrowed=True)
def Py_InitModule(space, name, methods):
    """Create a new module object based on a name and table of functions,
    returning the new module object.
    
    Older versions of Python did not support NULL as the value for the
    methods argument."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, PyMethodDef, rffi.CCHARP], PyObject, borrowed=True)
def Py_InitModule3(space, name, methods, doc):
    """Create a new module object based on a name and table of functions,
    returning the new module object.  If doc is non-NULL, it will be used
    to define the docstring for the module.
    
    Older versions of Python did not support NULL as the value for the
    methods argument."""
    raise NotImplementedError

@cpython_api([PyObject, rffi.CCHARP, ...], rffi.INT_real)
def PyArg_ParseTuple(space, args, format, ):
    """Parse the parameters of a function that takes only positional parameters
    into local variables.  Returns true on success; on failure, it returns
    false and raises the appropriate exception."""
    raise NotImplementedError

@cpython_api([PyObject, rffi.CCHARP, {va_list}], rffi.INT_real)
def PyArg_VaParse(space, args, format, vargs):
    """Identical to PyArg_ParseTuple(), except that it accepts a va_list
    rather than a variable number of arguments."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject, rffi.CCHARP, rffi.CCHARP, ...], rffi.INT_real)
def PyArg_ParseTupleAndKeywords(space, args, kw, format, keywords[], ):
    """Parse the parameters of a function that takes both positional and keyword
    parameters into local variables.  Returns true on success; on failure, it
    returns false and raises the appropriate exception."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject, rffi.CCHARP, rffi.CCHARP, {va_list}], rffi.INT_real)
def PyArg_VaParseTupleAndKeywords(space, args, kw, format, keywords[], vargs):
    """Identical to PyArg_ParseTupleAndKeywords(), except that it accepts a
    va_list rather than a variable number of arguments."""
    raise NotImplementedError

@cpython_api([PyObject, rffi.CCHARP, ...], rffi.INT_real)
def PyArg_Parse(space, args, format, ):
    """Function used to deconstruct the argument lists of "old-style" functions
    --- these are functions which use the METH_OLDARGS parameter
    parsing method.  This is not recommended for use in parameter parsing in
    new code, and most code in the standard interpreter has been modified to no
    longer use this for that purpose.  It does remain a convenient way to
    decompose other tuples, however, and may continue to be used for that
    purpose."""
    raise NotImplementedError

@cpython_api([PyObject, rffi.CCHARP, Py_ssize_t, Py_ssize_t, ...], rffi.INT_real)
def PyArg_UnpackTuple(space, args, name, min, max, ):
    """A simpler form of parameter retrieval which does not use a format string to
    specify the types of the arguments.  Functions which use this method to
    retrieve their parameters should be declared as METH_VARARGS in
    function or method tables.  The tuple containing the actual parameters
    should be passed as args; it must actually be a tuple.  The length of the
    tuple must be at least min and no more than max; min and max may be
    equal.  Additional arguments must be passed to the function, each of which
    should be a pointer to a PyObject* variable; these will be filled
    in with the values from args; they will contain borrowed references.  The
    variables which correspond to optional parameters not given by args will
    not be filled in; these should be initialized by the caller. This function
    returns true on success and false if args is not a tuple or contains the
    wrong number of elements; an exception will be set if there was a failure.
    
    This is an example of the use of this function, taken from the sources for
    the _weakref helper module for weak references:
    
    static PyObject *
    weakref_ref(PyObject *self, PyObject *args)
    {
        PyObject *object;
        PyObject *callback = NULL;
        PyObject *result = NULL;
    
        if (PyArg_UnpackTuple(args, "ref", 1, 2, &object, &callback)) {
            result = PyWeakref_NewRef(object, callback);
        }
        return result;
    }
    
    The call to PyArg_UnpackTuple() in this example is entirely
    equivalent to this call to PyArg_ParseTuple():
    
    PyArg_ParseTuple(args, "O|O:ref", &object, &callback)
    
    
    
    This function used an int type for min and max. This might
    require changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, ...], PyObject)
def Py_BuildValue(space, format, ):
    """Create a new value based on a format string similar to those accepted by
    the PyArg_Parse*() family of functions and a sequence of values.
    Returns the value or NULL in the case of an error; an exception will be
    raised if NULL is returned.
    
    Py_BuildValue() does not always build a tuple.  It builds a tuple
    only if its format string contains two or more format units.  If the format
    string is empty, it returns None; if it contains exactly one format
    unit, it returns whatever object is described by that format unit.  To
    force it to return a tuple of size 0 or one, parenthesize the format
    string.
    
    When memory buffers are passed as parameters to supply data to build
    objects, as for the s and s# formats, the required data is copied.
    Buffers provided by the caller are never referenced by the objects created
    by Py_BuildValue().  In other words, if your code invokes
    malloc() and passes the allocated memory to Py_BuildValue(),
    your code is responsible for calling free() for that memory once
    Py_BuildValue() returns.
    
    In the following description, the quoted form is the format unit; the entry
    in (round) parentheses is the Python object type that the format unit will
    return; and the entry in [square] brackets is the type of the C value(s) to
    be passed.
    
    The characters space, tab, colon and comma are ignored in format strings
    (but not within format units such as s#).  This can be used to make
    long format strings a tad more readable.
    
    s (string) [char *]
    
    Convert a null-terminated C string to a Python object.  If the C string
    pointer is NULL, None is used.
    
    s# (string) [char *, int]
    
    Convert a C string and its length to a Python object.  If the C string
    pointer is NULL, the length is ignored and None is returned.
    
    z (string or None) [char *]
    
    Same as s.
    
    z# (string or None) [char *, int]
    
    Same as s#.
    
    u (Unicode string) [Py_UNICODE *]
    
    Convert a null-terminated buffer of Unicode (UCS-2 or UCS-4) data to a
    Python Unicode object.  If the Unicode buffer pointer is NULL,
    None is returned.
    
    u# (Unicode string) [Py_UNICODE *, int]
    
    Convert a Unicode (UCS-2 or UCS-4) data buffer and its length to a
    Python Unicode object.   If the Unicode buffer pointer is NULL, the
    length is ignored and None is returned.
    
    i (integer) [int]
    
    Convert a plain C int to a Python integer object.
    
    b (integer) [char]
    
    Convert a plain C char to a Python integer object.
    
    h (integer) [short int]
    
    Convert a plain C short int to a Python integer object.
    
    l (integer) [long int]
    
    Convert a C long int to a Python integer object.
    
    B (integer) [unsigned char]
    
    Convert a C unsigned char to a Python integer object.
    
    H (integer) [unsigned short int]
    
    Convert a C unsigned short int to a Python integer object.
    
    I (integer/long) [unsigned int]
    
    Convert a C unsigned int to a Python integer object or a Python
    long integer object, if it is larger than sys.maxint.
    
    k (integer/long) [unsigned long]
    
    Convert a C unsigned long to a Python integer object or a
    Python long integer object, if it is larger than sys.maxint.
    
    L (long) [PY_LONG_LONG]
    
    Convert a C long long to a Python long integer object. Only
    available on platforms that support long long.
    
    K (long) [unsigned PY_LONG_LONG]
    
    Convert a C unsigned long long to a Python long integer object.
    Only available on platforms that support unsigned long long.
    
    n (int) [Py_ssize_t]
    
    Convert a C Py_ssize_t to a Python integer or long integer.
    
    
    
    c (string of length 1) [char]
    
    Convert a C int representing a character to a Python string of
    length 1.
    
    d (float) [double]
    
    Convert a C double to a Python floating point number.
    
    f (float) [float]
    
    Same as d.
    
    D (complex) [Py_complex *]
    
    Convert a C Py_complex structure to a Python complex number.
    
    O (object) [PyObject *]
    
    Pass a Python object untouched (except for its reference count, which is
    incremented by one).  If the object passed in is a NULL pointer, it is
    assumed that this was caused because the call producing the argument
    found an error and set an exception. Therefore, Py_BuildValue()
    will return NULL but won't raise an exception.  If no exception has
    been raised yet, SystemError is set.
    
    S (object) [PyObject *]
    
    Same as O.
    
    N (object) [PyObject *]
    
    Same as O, except it doesn't increment the reference count on the
    object.  Useful when the object is created by a call to an object
    constructor in the argument list.
    
    O& (object) [converter, anything]
    
    Convert anything to a Python object through a converter function.
    The function is called with anything (which should be compatible with
    void *) as its argument and should return a "new" Python
    object, or NULL if an error occurred.
    
    (items) (tuple) [matching-items]
    
    Convert a sequence of C values to a Python tuple with the same number of
    items.
    
    [items] (list) [matching-items]
    
    Convert a sequence of C values to a Python list with the same number of
    items.
    
    {items} (dictionary) [matching-items]
    
    Convert a sequence of C values to a Python dictionary.  Each pair of
    consecutive C values adds one item to the dictionary, serving as key and
    value, respectively.
    
    If there is an error in the format string, the SystemError exception
    is set and NULL returned."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, {va_list}], PyObject)
def Py_VaBuildValue(space, format, vargs):
    """Identical to Py_BuildValue(), except that it accepts a va_list
    rather than a variable number of arguments."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PyObject_CheckBuffer(space, obj):
    """Return 1 if obj supports the buffer interface otherwise 0."""
    raise NotImplementedError

@cpython_api([PyObject, {Py_buffer*}, rffi.INT_real], rffi.INT_real)
def PyObject_GetBuffer(space, obj, view, flags):
    """Export obj into a Py_buffer, view.  These arguments must
    never be NULL.  The flags argument is a bit field indicating what
    kind of buffer the caller is prepared to deal with and therefore what
    kind of buffer the exporter is allowed to return.  The buffer interface
    allows for complicated memory sharing possibilities, but some caller may
    not be able to handle all the complexity but may want to see if the
    exporter will let them take a simpler view to its memory.
    
    Some exporters may not be able to share memory in every possible way and
    may need to raise errors to signal to some consumers that something is
    just not possible. These errors should be a BufferError unless
    there is another error that is actually causing the problem. The
    exporter can use flags information to simplify how much of the
    Py_buffer structure is filled in with non-default values and/or
    raise an error if the object can't support a simpler view of its memory.
    
    0 is returned on success and -1 on error.
    
    The following table gives possible values to the flags arguments.
    
    
    
    
    
    Flag
    
    Description
    
    PyBUF_SIMPLE
    
    This is the default flag state.  The returned
    buffer may or may not have writable memory.  The
    format of the data will be assumed to be unsigned
    bytes.  This is a "stand-alone" flag constant. It
    never needs to be '|'d to the others. The exporter
    will raise an error if it cannot provide such a
    contiguous buffer of bytes.
    
    PyBUF_WRITABLE
    
    The returned buffer must be writable.  If it is
    not writable, then raise an error.
    
    PyBUF_STRIDES
    
    This implies PyBUF_ND. The returned
    buffer must provide strides information (i.e. the
    strides cannot be NULL). This would be used when
    the consumer can handle strided, discontiguous
    arrays.  Handling strides automatically assumes
    you can handle shape.  The exporter can raise an
    error if a strided representation of the data is
    not possible (i.e. without the suboffsets).
    
    PyBUF_ND
    
    The returned buffer must provide shape
    information. The memory will be assumed C-style
    contiguous (last dimension varies the
    fastest). The exporter may raise an error if it
    cannot provide this kind of contiguous buffer. If
    this is not given then shape will be NULL.
    
    PyBUF_C_CONTIGUOUS
    PyBUF_F_CONTIGUOUS
    PyBUF_ANY_CONTIGUOUS
    
    These flags indicate that the contiguity returned
    buffer must be respectively, C-contiguous (last
    dimension varies the fastest), Fortran contiguous
    (first dimension varies the fastest) or either
    one.  All of these flags imply
    PyBUF_STRIDES and guarantee that the
    strides buffer info structure will be filled in
    correctly.
    
    PyBUF_INDIRECT
    
    This flag indicates the returned buffer must have
    suboffsets information (which can be NULL if no
    suboffsets are needed).  This can be used when
    the consumer can handle indirect array
    referencing implied by these suboffsets. This
    implies PyBUF_STRIDES.
    
    PyBUF_FORMAT
    
    The returned buffer must have true format
    information if this flag is provided. This would
    be used when the consumer is going to be checking
    for what 'kind' of data is actually stored. An
    exporter should always be able to provide this
    information if requested. If format is not
    explicitly requested then the format must be
    returned as NULL (which means 'B', or
    unsigned bytes)
    
    PyBUF_STRIDED
    
    This is equivalent to (PyBUF_STRIDES |
    PyBUF_WRITABLE).
    
    PyBUF_STRIDED_RO
    
    This is equivalent to (PyBUF_STRIDES).
    
    PyBUF_RECORDS
    
    This is equivalent to (PyBUF_STRIDES |
    PyBUF_FORMAT | PyBUF_WRITABLE).
    
    PyBUF_RECORDS_RO
    
    This is equivalent to (PyBUF_STRIDES |
    PyBUF_FORMAT).
    
    PyBUF_FULL
    
    This is equivalent to (PyBUF_INDIRECT |
    PyBUF_FORMAT | PyBUF_WRITABLE).
    
    PyBUF_FULL_RO
    
    This is equivalent to (PyBUF_INDIRECT |
    PyBUF_FORMAT).
    
    PyBUF_CONTIG
    
    This is equivalent to (PyBUF_ND |
    PyBUF_WRITABLE).
    
    PyBUF_CONTIG_RO
    
    This is equivalent to (PyBUF_ND)."""
    raise NotImplementedError

@cpython_api([{Py_buffer*}], lltype.Void)
def PyBuffer_Release(space, view):
    """Release the buffer view.  This should be called when the buffer
    is no longer being used as it may free memory from it."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP], Py_ssize_t)
def PyBuffer_SizeFromFormat(space, ):
    """Return the implied ~Py_buffer.itemsize from the struct-stype
    ~Py_buffer.format."""
    raise NotImplementedError

@cpython_api([PyObject, {void*}, Py_ssize_t, lltype.Char], rffi.INT_real)
def PyObject_CopyToObject(space, obj, buf, len, fortran):
    """Copy len bytes of data pointed to by the contiguous chunk of memory
    pointed to by buf into the buffer exported by obj.  The buffer must of
    course be writable.  Return 0 on success and return -1 and raise an error
    on failure.  If the object does not have a writable buffer, then an error
    is raised.  If fortran is 'F', then if the object is
    multi-dimensional, then the data will be copied into the array in
    Fortran-style (first dimension varies the fastest).  If fortran is
    'C', then the data will be copied into the array in C-style (last
    dimension varies the fastest).  If fortran is 'A', then it does not
    matter and the copy will be made in whatever way is more efficient."""
    raise NotImplementedError

@cpython_api([{Py_buffer*}, lltype.Char], rffi.INT_real)
def PyBuffer_IsContiguous(space, view, fortran):
    """Return 1 if the memory defined by the view is C-style (fortran is
    'C') or Fortran-style (fortran is 'F') contiguous or either one
    (fortran is 'A').  Return 0 otherwise."""
    raise NotImplementedError

@cpython_api([rffi.INT_real, Py_ssize_t, Py_ssize_t, Py_ssize_t, lltype.Char], lltype.Void)
def PyBuffer_FillContiguousStrides(space, ndim, shape, strides, itemsize, fortran):
    """Fill the strides array with byte-strides of a contiguous (C-style if
    fortran is 'C' or Fortran-style if fortran is 'F' array of the
    given shape with the given number of bytes per element."""
    raise NotImplementedError

@cpython_api([{Py_buffer*}, PyObject, {void*}, Py_ssize_t, rffi.INT_real, rffi.INT_real], rffi.INT_real)
def PyBuffer_FillInfo(space, view, obj, buf, len, readonly, infoflags):
    """Fill in a buffer-info structure, view, correctly for an exporter that can
    only share a contiguous chunk of memory of "unsigned bytes" of the given
    length.  Return 0 on success and -1 (with raising an error) on error."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyMemoryView_FromObject(space, obj):
    """Return a memoryview object from an object that defines the buffer interface."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PyBuffer_Check(space, p):
    """Return true if the argument has type PyBuffer_Type."""
    raise NotImplementedError

@cpython_api([PyObject, Py_ssize_t, Py_ssize_t], PyObject)
def PyBuffer_FromObject(space, base, offset, size):
    """Return a new read-only buffer object.  This raises TypeError if
    base doesn't support the read-only buffer protocol or doesn't provide
    exactly one buffer segment, or it raises ValueError if offset is
    less than zero.  The buffer will hold a reference to the base object, and
    the buffer's contents will refer to the base object's buffer interface,
    starting as position offset and extending for size bytes. If size is
    Py_END_OF_BUFFER, then the new buffer's contents extend to the
    length of the base object's exported buffer data.
    
    This function used an int type for offset and size. This
    might require changes in your code for properly supporting 64-bit
    systems."""
    raise NotImplementedError

@cpython_api([PyObject, Py_ssize_t, Py_ssize_t], PyObject)
def PyBuffer_FromReadWriteObject(space, base, offset, size):
    """Return a new writable buffer object.  Parameters and exceptions are similar
    to those for PyBuffer_FromObject().  If the base object does not
    export the writeable buffer protocol, then TypeError is raised.
    
    This function used an int type for offset and size. This
    might require changes in your code for properly supporting 64-bit
    systems."""
    raise NotImplementedError

@cpython_api([{void*}, Py_ssize_t], PyObject)
def PyBuffer_FromMemory(space, ptr, size):
    """Return a new read-only buffer object that reads from a specified location
    in memory, with a specified size.  The caller is responsible for ensuring
    that the memory buffer, passed in as ptr, is not deallocated while the
    returned buffer object exists.  Raises ValueError if size is less
    than zero.  Note that Py_END_OF_BUFFER may not be passed for the
    size parameter; ValueError will be raised in that case.
    
    This function used an int type for size. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([{void*}, Py_ssize_t], PyObject)
def PyBuffer_FromReadWriteMemory(space, ptr, size):
    """Similar to PyBuffer_FromMemory(), but the returned buffer is
    writable.
    
    This function used an int type for size. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([Py_ssize_t], PyObject)
def PyBuffer_New(space, size):
    """Return a new writable buffer object that maintains its own memory buffer of
    size bytes.  ValueError is returned if size is not zero or
    positive.  Note that the memory buffer (as returned by
    PyObject_AsWriteBuffer()) is not specifically aligned.
    
    This function used an int type for size. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PyByteArray_Check(space, o):
    """Return true if the object o is a bytearray object or an instance of a
    subtype of the bytearray type."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PyByteArray_CheckExact(space, o):
    """Return true if the object o is a bytearray object, but not an instance of a
    subtype of the bytearray type."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyByteArray_FromObject(space, o):
    """Return a new bytearray object from any object, o, that implements the
    buffer protocol.
    
    XXX expand about the buffer protocol, at least somewhere"""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, Py_ssize_t], PyObject)
def PyByteArray_FromStringAndSize(space, string, len):
    """Create a new bytearray object from string and its length, len.  On
    failure, NULL is returned."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], PyObject)
def PyByteArray_Concat(space, a, b):
    """Concat bytearrays a and b and return a new bytearray with the result."""
    raise NotImplementedError

@cpython_api([PyObject], Py_ssize_t)
def PyByteArray_Size(space, bytearray):
    """Return the size of bytearray after checking for a NULL pointer."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.CCHARP)
def PyByteArray_AsString(space, bytearray):
    """Return the contents of bytearray as a char array after checking for a
    NULL pointer."""
    raise NotImplementedError

@cpython_api([PyObject, Py_ssize_t], rffi.INT_real)
def PyByteArray_Resize(space, bytearray, len):
    """Resize the internal buffer of bytearray to len."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.CCHARP)
def PyByteArray_AS_STRING(space, bytearray):
    """Macro version of PyByteArray_AsString()."""
    raise NotImplementedError

@cpython_api([PyObject], Py_ssize_t)
def PyByteArray_GET_SIZE(space, bytearray):
    """Macro version of PyByteArray_Size()."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PyCapsule_CheckExact(space, p):
    """Return true if its argument is a PyCapsule."""
    raise NotImplementedError

@cpython_api([{void*}, rffi.CCHARP, {PyCapsule_Destructor}], PyObject)
def PyCapsule_New(space, pointer, name, destructor):
    """Create a PyCapsule encapsulating the pointer.  The pointer
    argument may not be NULL.
    
    On failure, set an exception and return NULL.
    
    The name string may either be NULL or a pointer to a valid C string.  If
    non-NULL, this string must outlive the capsule.  (Though it is permitted to
    free it inside the destructor.)
    
    If the destructor argument is not NULL, it will be called with the
    capsule as its argument when it is destroyed.
    
    If this capsule will be stored as an attribute of a module, the name should
    be specified as modulename.attributename.  This will enable other modules
    to import the capsule using PyCapsule_Import()."""
    raise NotImplementedError

@cpython_api([PyObject, rffi.CCHARP], {void*})
def PyCapsule_GetPointer(space, capsule, name):
    """Retrieve the pointer stored in the capsule.  On failure, set an exception
    and return NULL.
    
    The name parameter must compare exactly to the name stored in the capsule.
    If the name stored in the capsule is NULL, the name passed in must also
    be NULL.  Python uses the C function strcmp() to compare capsule
    names."""
    raise NotImplementedError

@cpython_api([PyObject], {PyCapsule_Destructor})
def PyCapsule_GetDestructor(space, capsule):
    """Return the current destructor stored in the capsule.  On failure, set an
    exception and return NULL.
    
    It is legal for a capsule to have a NULL destructor.  This makes a NULL
    return code somewhat ambiguous; use PyCapsule_IsValid() or
    PyErr_Occurred() to disambiguate."""
    raise NotImplementedError

@cpython_api([PyObject], {void*})
def PyCapsule_GetContext(space, capsule):
    """Return the current context stored in the capsule.  On failure, set an
    exception and return NULL.
    
    It is legal for a capsule to have a NULL context.  This makes a NULL
    return code somewhat ambiguous; use PyCapsule_IsValid() or
    PyErr_Occurred() to disambiguate."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.CCHARP)
def PyCapsule_GetName(space, capsule):
    """Return the current name stored in the capsule.  On failure, set an exception
    and return NULL.
    
    It is legal for a capsule to have a NULL name.  This makes a NULL return
    code somewhat ambiguous; use PyCapsule_IsValid() or
    PyErr_Occurred() to disambiguate."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, rffi.INT_real], {void*})
def PyCapsule_Import(space, name, no_block):
    """Import a pointer to a C object from a capsule attribute in a module.  The
    name parameter should specify the full name to the attribute, as in
    module.attribute.  The name stored in the capsule must match this
    string exactly.  If no_block is true, import the module without blocking
    (using PyImport_ImportModuleNoBlock()).  If no_block is false,
    import the module conventionally (using PyImport_ImportModule()).
    
    Return the capsule's internal pointer on success.  On failure, set an
    exception and return NULL.  However, if PyCapsule_Import() failed to
    import the module, and no_block was true, no exception is set."""
    raise NotImplementedError

@cpython_api([PyObject, rffi.CCHARP], rffi.INT_real)
def PyCapsule_IsValid(space, capsule, name):
    """Determines whether or not capsule is a valid capsule.  A valid capsule is
    non-NULL, passes PyCapsule_CheckExact(), has a non-NULL pointer
    stored in it, and its internal name matches the name parameter.  (See
    PyCapsule_GetPointer() for information on how capsule names are
    compared.)
    
    In other words, if PyCapsule_IsValid() returns a true value, calls to
    any of the accessors (any function starting with PyCapsule_Get()) are
    guaranteed to succeed.
    
    Return a nonzero value if the object is valid and matches the name passed in.
    Return 0 otherwise.  This function will not fail."""
    raise NotImplementedError

@cpython_api([PyObject, {void*}], rffi.INT_real)
def PyCapsule_SetContext(space, capsule, context):
    """Set the context pointer inside capsule to context.
    
    Return 0 on success.  Return nonzero and set an exception on failure."""
    raise NotImplementedError

@cpython_api([PyObject, {PyCapsule_Destructor}], rffi.INT_real)
def PyCapsule_SetDestructor(space, capsule, destructor):
    """Set the destructor inside capsule to destructor.
    
    Return 0 on success.  Return nonzero and set an exception on failure."""
    raise NotImplementedError

@cpython_api([PyObject, rffi.CCHARP], rffi.INT_real)
def PyCapsule_SetName(space, capsule, name):
    """Set the name inside capsule to name.  If non-NULL, the name must
    outlive the capsule.  If the previous name stored in the capsule was not
    NULL, no attempt is made to free it.
    
    Return 0 on success.  Return nonzero and set an exception on failure."""
    raise NotImplementedError

@cpython_api([PyObject, {void*}], rffi.INT_real)
def PyCapsule_SetPointer(space, capsule, pointer):
    """Set the void pointer inside capsule to pointer.  The pointer may not be
    NULL.
    
    Return 0 on success.  Return nonzero and set an exception on failure."""
    raise NotImplementedError

@cpython_api([{ob}], rffi.INT_real)
def PyCell_Check(space, ):
    """Return true if ob is a cell object; ob must not be NULL."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyCell_New(space, ob):
    """Create and return a new cell object containing the value ob. The parameter may
    be NULL."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyCell_Get(space, cell):
    """Return the contents of the cell cell."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject, borrowed=True)
def PyCell_GET(space, cell):
    """Return the contents of the cell cell, but without checking that cell is
    non-NULL and a cell object."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], rffi.INT_real)
def PyCell_Set(space, cell, value):
    """Set the contents of the cell object cell to value.  This releases the
    reference to any current content of the cell. value may be NULL.  cell
    must be non-NULL; if it is not a cell object, -1 will be returned.  On
    success, 0 will be returned."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], lltype.Void)
def PyCell_SET(space, cell, value):
    """Sets the value of the cell object cell to value.  No reference counts are
    adjusted, and no checks are made for safety; cell must be non-NULL and must
    be a cell object."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PyClass_Check(space, o):
    """Return true if the object o is a class object, including instances of types
    derived from the standard class object.  Return false in all other cases."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], rffi.INT_real)
def PyClass_IsSubclass(space, klass, base):
    """Return true if klass is a subclass of base. Return false in all other cases."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PyInstance_Check(space, obj):
    """Return true if obj is an instance."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject, PyObject], PyObject)
def PyInstance_New(space, class, arg, kw):
    """Create a new instance of a specific class.  The parameters arg and kw are
    used as the positional and keyword parameters to the object's constructor."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], PyObject)
def PyInstance_NewRaw(space, class, dict):
    """Create a new instance of a specific class without calling its constructor.
    class is the class of new object.  The dict parameter will be used as the
    object's __dict__; if NULL, a new dictionary will be created for the
    instance."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PyCObject_Check(space, p):
    """Return true if its argument is a PyCObject."""
    raise NotImplementedError

@cpython_api([{void*}, {void (*destr)(void*}], PyObject)
def PyCObject_FromVoidPtr(space, cobj, )):
    """Create a PyCObject from the void * cobj.  The destr function
    will be called when the object is reclaimed, unless it is NULL."""
    raise NotImplementedError

@cpython_api([{void*}, {void*}, {void (*destr)(void*}, {void*}], PyObject)
def PyCObject_FromVoidPtrAndDesc(space, cobj, desc, , )):
    """Create a PyCObject from the void * cobj.  The destr
    function will be called when the object is reclaimed. The desc argument can
    be used to pass extra callback data for the destructor function."""
    raise NotImplementedError

@cpython_api([PyObject], {void*})
def PyCObject_AsVoidPtr(space, self):
    """Return the object void * that the PyCObject self was
    created with."""
    raise NotImplementedError

@cpython_api([PyObject], {void*})
def PyCObject_GetDesc(space, self):
    """Return the description void * that the PyCObject self was
    created with."""
    raise NotImplementedError

@cpython_api([PyObject, {void*}], rffi.INT_real)
def PyCObject_SetVoidPtr(space, self, cobj):
    """Set the void pointer inside self to cobj. The PyCObject must not
    have an associated destructor. Return true on success, false on failure."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PyCode_Check(space, co):
    """Return true if co is a code object"""
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PyCode_GetNumFree(space, co):
    """Return the number of free variables in co."""
    raise NotImplementedError

@cpython_api([rffi.INT_real, rffi.INT_real, rffi.INT_real, rffi.INT_real, PyObject, PyObject, PyObject, PyObject, PyObject, PyObject, PyObject, PyObject, rffi.INT_real, PyObject], {PyCodeObject*})
def PyCode_New(space, argcount, nlocals, stacksize, flags, code, consts, names, varnames, freevars, cellvars, filename, name, firstlineno, lnotab):
    """Return a new code object.  If you need a dummy code object to
    create a frame, use PyCode_NewEmpty() instead.  Calling
    PyCode_New() directly can bind you to a precise Python
    version since the definition of the bytecode changes often."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, rffi.CCHARP, rffi.INT_real], rffi.INT_real)
def PyCode_NewEmpty(space, filename, funcname, firstlineno):
    """Return a new empty code object with the specified filename,
    function name, and first line number.  It is illegal to
    exec or eval() the resulting code object."""
    raise NotImplementedError

@cpython_api([{Py_complex}, {Py_complex}], {Py_complex})
def _Py_c_sum(space, left, right):
    """Return the sum of two complex numbers, using the C Py_complex
    representation."""
    raise NotImplementedError

@cpython_api([{Py_complex}, {Py_complex}], {Py_complex})
def _Py_c_diff(space, left, right):
    """Return the difference between two complex numbers, using the C
    Py_complex representation."""
    raise NotImplementedError

@cpython_api([{Py_complex}], {Py_complex})
def _Py_c_neg(space, complex):
    """Return the negation of the complex number complex, using the C
    Py_complex representation."""
    raise NotImplementedError

@cpython_api([{Py_complex}, {Py_complex}], {Py_complex})
def _Py_c_prod(space, left, right):
    """Return the product of two complex numbers, using the C Py_complex
    representation."""
    raise NotImplementedError

@cpython_api([{Py_complex}, {Py_complex}], {Py_complex})
def _Py_c_quot(space, dividend, divisor):
    """Return the quotient of two complex numbers, using the C Py_complex
    representation."""
    raise NotImplementedError

@cpython_api([{Py_complex}, {Py_complex}], {Py_complex})
def _Py_c_pow(space, num, exp):
    """Return the exponentiation of num by exp, using the C Py_complex
    representation."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PyComplex_Check(space, p):
    """Return true if its argument is a PyComplexObject or a subtype of
    PyComplexObject.
    
    Allowed subtypes to be accepted."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PyComplex_CheckExact(space, p):
    """Return true if its argument is a PyComplexObject, but not a subtype of
    PyComplexObject.
    """
    raise NotImplementedError

@cpython_api([{Py_complex}], PyObject)
def PyComplex_FromCComplex(space, v):
    """Create a new Python complex number object from a C Py_complex value."""
    raise NotImplementedError

@cpython_api([{double}, {double}], PyObject)
def PyComplex_FromDoubles(space, real, imag):
    """Return a new PyComplexObject object from real and imag."""
    raise NotImplementedError

@cpython_api([PyObject], {double})
def PyComplex_RealAsDouble(space, op):
    """Return the real part of op as a C double."""
    raise NotImplementedError

@cpython_api([PyObject], {double})
def PyComplex_ImagAsDouble(space, op):
    """Return the imaginary part of op as a C double."""
    raise NotImplementedError

@cpython_api([PyObject], {Py_complex})
def PyComplex_AsCComplex(space, op):
    """Return the Py_complex value of the complex number op.
    
    If op is not a Python complex number object but has a __complex__()
    method, this method will first be called to convert op to a Python complex
    number object."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, {size_t}, rffi.CCHARP, ...], rffi.INT_real)
def PyOS_snprintf(space, str, size, format, ):
    """Output not more than size bytes to str according to the format string
    format and the extra arguments. See the Unix man page snprintf(2)."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, {size_t}, rffi.CCHARP, {va_list}], rffi.INT_real)
def PyOS_vsnprintf(space, str, size, format, va):
    """Output not more than size bytes to str according to the format string
    format and the variable argument list va. Unix man page
    vsnprintf(2)."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, {char**}, PyObject], {double})
def PyOS_string_to_double(space, s, endptr, overflow_exception):
    """Convert a string s to a double, raising a Python
    exception on failure.  The set of accepted strings corresponds to
    the set of strings accepted by Python's float() constructor,
    except that s must not have leading or trailing whitespace.
    The conversion is independent of the current locale.
    
    If endptr is NULL, convert the whole string.  Raise
    ValueError and return -1.0 if the string is not a valid
    representation of a floating-point number.
    
    If endptr is not NULL, convert as much of the string as
    possible and set *endptr to point to the first unconverted
    character.  If no initial segment of the string is the valid
    representation of a floating-point number, set *endptr to point
    to the beginning of the string, raise ValueError, and return
    -1.0.
    
    If s represents a value that is too large to store in a float
    (for example, "1e500" is such a string on many platforms) then
    if overflow_exception is NULL return Py_HUGE_VAL (with
    an appropriate sign) and don't set any exception.  Otherwise,
    overflow_exception must point to a Python exception object;
    raise that exception and return -1.0.  In both cases, set
    *endptr to point to the first character after the converted value.
    
    If any other error occurs during the conversion (for example an
    out-of-memory error), set the appropriate Python exception and
    return -1.0.
    """
    raise NotImplementedError

@cpython_api([rffi.CCHARP, {char**}], {double})
def PyOS_ascii_strtod(space, nptr, endptr):
    """Convert a string to a double. This function behaves like the Standard C
    function strtod() does in the C locale. It does this without changing the
    current locale, since that would not be thread-safe.
    
    PyOS_ascii_strtod() should typically be used for reading configuration
    files or other non-user input that should be locale independent.
    
    See the Unix man page strtod(2) for details.
    
    
    
    Use PyOS_string_to_double() instead."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, {size_t}, rffi.CCHARP, {double}], rffi.CCHARP)
def PyOS_ascii_formatd(space, buffer, buf_len, format, d):
    """Convert a double to a string using the '.' as the decimal
    separator. format is a printf()-style format string specifying the
    number format. Allowed conversion characters are 'e', 'E', 'f',
    'F', 'g' and 'G'.
    
    The return value is a pointer to buffer with the converted string or NULL if
    the conversion failed.
    
    
    
    This function is removed in Python 2.7 and 3.1.  Use PyOS_double_to_string()
    instead."""
    raise NotImplementedError

@cpython_api([{double}, lltype.Char, rffi.INT_real, rffi.INT_real, {int*}], rffi.CCHARP)
def PyOS_double_to_string(space, val, format_code, precision, flags, ptype):
    """Convert a double val to a string using supplied
    format_code, precision, and flags.
    
    format_code must be one of 'e', 'E', 'f', 'F',
    'g', 'G' or 'r'.  For 'r', the supplied precision
    must be 0 and is ignored.  The 'r' format code specifies the
    standard repr() format.
    
    flags can be zero or more of the values Py_DTSF_SIGN,
    Py_DTSF_ADD_DOT_0, or Py_DTSF_ALT, or-ed together:
    
    Py_DTSF_SIGN means to always precede the returned string with a sign
    character, even if val is non-negative.
    
    Py_DTSF_ADD_DOT_0 means to ensure that the returned string will not look
    like an integer.
    
    Py_DTSF_ALT means to apply "alternate" formatting rules.  See the
    documentation for the PyOS_snprintf() '#' specifier for
    details.
    
    If ptype is non-NULL, then the value it points to will be set to one of
    Py_DTST_FINITE, Py_DTST_INFINITE, or Py_DTST_NAN, signifying that
    val is a finite number, an infinite number, or not a number, respectively.
    
    The return value is a pointer to buffer with the converted string or
    NULL if the conversion failed. The caller is responsible for freeing the
    returned string by calling PyMem_Free().
    """
    raise NotImplementedError

@cpython_api([rffi.CCHARP], {double})
def PyOS_ascii_atof(space, nptr):
    """Convert a string to a double in a locale-independent way.
    
    See the Unix man page atof(2) for details.
    
    
    
    Use PyOS_string_to_double() instead."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, rffi.CCHARP], rffi.CCHARP)
def PyOS_stricmp(space, s1, s2):
    """Case insensitive comparison of strings. The function works almost
    identically to strcmp() except that it ignores the case.
    """
    raise NotImplementedError

@cpython_api([rffi.CCHARP, rffi.CCHARP, {Py_ssize_t }], rffi.CCHARP)
def PyOS_strnicmp(space, s1, s2, size):
    """Case insensitive comparison of strings. The function works almost
    identically to strncmp() except that it ignores the case.
    """
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PyDate_Check(space, ob):
    """Return true if ob is of type PyDateTime_DateType or a subtype of
    PyDateTime_DateType.  ob must not be NULL.
    """
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PyDate_CheckExact(space, ob):
    """Return true if ob is of type PyDateTime_DateType. ob must not be
    NULL.
    """
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PyDateTime_Check(space, ob):
    """Return true if ob is of type PyDateTime_DateTimeType or a subtype of
    PyDateTime_DateTimeType.  ob must not be NULL.
    """
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PyDateTime_CheckExact(space, ob):
    """Return true if ob is of type PyDateTime_DateTimeType. ob must not
    be NULL.
    """
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PyTime_Check(space, ob):
    """Return true if ob is of type PyDateTime_TimeType or a subtype of
    PyDateTime_TimeType.  ob must not be NULL.
    """
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PyTime_CheckExact(space, ob):
    """Return true if ob is of type PyDateTime_TimeType. ob must not be
    NULL.
    """
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PyDelta_Check(space, ob):
    """Return true if ob is of type PyDateTime_DeltaType or a subtype of
    PyDateTime_DeltaType.  ob must not be NULL.
    """
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PyDelta_CheckExact(space, ob):
    """Return true if ob is of type PyDateTime_DeltaType. ob must not be
    NULL.
    """
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PyTZInfo_Check(space, ob):
    """Return true if ob is of type PyDateTime_TZInfoType or a subtype of
    PyDateTime_TZInfoType.  ob must not be NULL.
    """
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PyTZInfo_CheckExact(space, ob):
    """Return true if ob is of type PyDateTime_TZInfoType. ob must not be
    NULL.
    """
    raise NotImplementedError

@cpython_api([rffi.INT_real, rffi.INT_real, rffi.INT_real], PyObject)
def PyDate_FromDate(space, year, month, day):
    """Return a datetime.date object with the specified year, month and day.
    """
    raise NotImplementedError

@cpython_api([rffi.INT_real, rffi.INT_real, rffi.INT_real, rffi.INT_real, rffi.INT_real, rffi.INT_real, rffi.INT_real], PyObject)
def PyDateTime_FromDateAndTime(space, year, month, day, hour, minute, second, usecond):
    """Return a datetime.datetime object with the specified year, month, day, hour,
    minute, second and microsecond.
    """
    raise NotImplementedError

@cpython_api([rffi.INT_real, rffi.INT_real, rffi.INT_real, rffi.INT_real], PyObject)
def PyTime_FromTime(space, hour, minute, second, usecond):
    """Return a datetime.time object with the specified hour, minute, second and
    microsecond.
    """
    raise NotImplementedError

@cpython_api([rffi.INT_real, rffi.INT_real, rffi.INT_real], PyObject)
def PyDelta_FromDSU(space, days, seconds, useconds):
    """Return a datetime.timedelta object representing the given number of days,
    seconds and microseconds.  Normalization is performed so that the resulting
    number of microseconds and seconds lie in the ranges documented for
    datetime.timedelta objects.
    """
    raise NotImplementedError

@cpython_api([{PyDateTime_Date*}], rffi.INT_real)
def PyDateTime_GET_YEAR(space, o):
    """Return the year, as a positive int.
    """
    raise NotImplementedError

@cpython_api([{PyDateTime_Date*}], rffi.INT_real)
def PyDateTime_GET_MONTH(space, o):
    """Return the month, as an int from 1 through 12.
    """
    raise NotImplementedError

@cpython_api([{PyDateTime_Date*}], rffi.INT_real)
def PyDateTime_GET_DAY(space, o):
    """Return the day, as an int from 1 through 31.
    """
    raise NotImplementedError

@cpython_api([{PyDateTime_DateTime*}], rffi.INT_real)
def PyDateTime_DATE_GET_HOUR(space, o):
    """Return the hour, as an int from 0 through 23.
    """
    raise NotImplementedError

@cpython_api([{PyDateTime_DateTime*}], rffi.INT_real)
def PyDateTime_DATE_GET_MINUTE(space, o):
    """Return the minute, as an int from 0 through 59.
    """
    raise NotImplementedError

@cpython_api([{PyDateTime_DateTime*}], rffi.INT_real)
def PyDateTime_DATE_GET_SECOND(space, o):
    """Return the second, as an int from 0 through 59.
    """
    raise NotImplementedError

@cpython_api([{PyDateTime_DateTime*}], rffi.INT_real)
def PyDateTime_DATE_GET_MICROSECOND(space, o):
    """Return the microsecond, as an int from 0 through 999999.
    """
    raise NotImplementedError

@cpython_api([{PyDateTime_Time*}], rffi.INT_real)
def PyDateTime_TIME_GET_HOUR(space, o):
    """Return the hour, as an int from 0 through 23.
    """
    raise NotImplementedError

@cpython_api([{PyDateTime_Time*}], rffi.INT_real)
def PyDateTime_TIME_GET_MINUTE(space, o):
    """Return the minute, as an int from 0 through 59.
    """
    raise NotImplementedError

@cpython_api([{PyDateTime_Time*}], rffi.INT_real)
def PyDateTime_TIME_GET_SECOND(space, o):
    """Return the second, as an int from 0 through 59.
    """
    raise NotImplementedError

@cpython_api([{PyDateTime_Time*}], rffi.INT_real)
def PyDateTime_TIME_GET_MICROSECOND(space, o):
    """Return the microsecond, as an int from 0 through 999999.
    """
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyDateTime_FromTimestamp(space, args):
    """Create and return a new datetime.datetime object given an argument tuple
    suitable for passing to datetime.datetime.fromtimestamp().
    """
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyDate_FromTimestamp(space, args):
    """Create and return a new datetime.date object given an argument tuple
    suitable for passing to datetime.date.fromtimestamp().
    """
    raise NotImplementedError

@cpython_api([PyTypeObjectPtr, {struct PyGetSetDef*}], PyObject)
def PyDescr_NewGetSet(space, type, getset):
    raise NotImplementedError

@cpython_api([PyTypeObjectPtr, {struct PyMemberDef*}], PyObject)
def PyDescr_NewMember(space, type, meth):
    raise NotImplementedError

@cpython_api([PyTypeObjectPtr, {struct PyMethodDef*}], PyObject)
def PyDescr_NewMethod(space, type, meth):
    raise NotImplementedError

@cpython_api([PyTypeObjectPtr, {struct wrapperbase*}, {void*}], PyObject)
def PyDescr_NewWrapper(space, type, wrapper, wrapped):
    raise NotImplementedError

@cpython_api([PyTypeObjectPtr, PyMethodDef], PyObject)
def PyDescr_NewClassMethod(space, type, method):
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PyDescr_IsData(space, descr):
    """Return true if the descriptor objects descr describes a data attribute, or
    false if it describes a method.  descr must be a descriptor object; there is
    no error checking.
    """
    raise NotImplementedError

@cpython_api([PyObject, PyObject], PyObject)
def PyWrapper_New(space, , ):
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyDictProxy_New(space, dict):
    """Return a proxy object for a mapping which enforces read-only behavior.
    This is normally used to create a proxy to prevent modification of the
    dictionary for non-dynamic class types.
    """
    raise NotImplementedError

@cpython_api([PyObject], lltype.Void)
def PyDict_Clear(space, p):
    """Empty an existing dictionary of all key-value pairs."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], rffi.INT_real)
def PyDict_Contains(space, p, key):
    """Determine if dictionary p contains key.  If an item in p is matches
    key, return 1, otherwise return 0.  On error, return -1.
    This is equivalent to the Python expression key in p.
    """
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyDict_Copy(space, p):
    """Return a new dictionary that contains the same key-value pairs as p.
    """
    raise NotImplementedError

@cpython_api([PyObject, PyObject], rffi.INT_real)
def PyDict_DelItem(space, p, key):
    """Remove the entry in dictionary p with key key. key must be hashable;
    if it isn't, TypeError is raised.  Return 0 on success or -1
    on failure."""
    raise NotImplementedError

@cpython_api([PyObject, rffi.CCHARP], rffi.INT_real)
def PyDict_DelItemString(space, p, key):
    """Remove the entry in dictionary p which has a key specified by the string
    key.  Return 0 on success or -1 on failure."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyDict_Items(space, p):
    """Return a PyListObject containing all the items from the
    dictionary, as in the dictionary method dict.items()."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyDict_Keys(space, p):
    """Return a PyListObject containing all the keys from the dictionary,
    as in the dictionary method dict.keys()."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyDict_Values(space, p):
    """Return a PyListObject containing all the values from the
    dictionary p, as in the dictionary method dict.values()."""
    raise NotImplementedError

@cpython_api([PyObject], Py_ssize_t)
def PyDict_Size(space, p):
    """
    
    
    
    Return the number of items in the dictionary.  This is equivalent to
    len(p) on a dictionary.
    
    This function returned an int type.  This might require changes
    in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject, Py_ssize_t, PyObjectP, PyObjectP], rffi.INT_real)
def PyDict_Next(space, p, ppos, pkey, pvalue):
    """Iterate over all key-value pairs in the dictionary p.  The
    Py_ssize_t referred to by ppos must be initialized to 0
    prior to the first call to this function to start the iteration; the
    function returns true for each pair in the dictionary, and false once all
    pairs have been reported.  The parameters pkey and pvalue should either
    point to PyObject* variables that will be filled in with each key
    and value, respectively, or may be NULL.  Any references returned through
    them are borrowed.  ppos should not be altered during iteration. Its
    value represents offsets within the internal dictionary structure, and
    since the structure is sparse, the offsets are not consecutive.
    
    For example:
    
    PyObject *key, *value;
    Py_ssize_t pos = 0;
    
    while (PyDict_Next(self->dict, &pos, &key, &value)) {
        /* do something interesting with the values... */
        ...
    }
    
    The dictionary p should not be mutated during iteration.  It is safe
    (since Python 2.1) to modify the values of the keys as you iterate over the
    dictionary, but only so long as the set of keys does not change.  For
    example:
    
    PyObject *key, *value;
    Py_ssize_t pos = 0;
    
    while (PyDict_Next(self->dict, &pos, &key, &value)) {
        int i = PyInt_AS_LONG(value) + 1;
        PyObject *o = PyInt_FromLong(i);
        if (o == NULL)
            return -1;
        if (PyDict_SetItem(self->dict, key, o) < 0) {
            Py_DECREF(o);
            return -1;
        }
        Py_DECREF(o);
    }
    
    This function used an int * type for ppos. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject, rffi.INT_real], rffi.INT_real)
def PyDict_Merge(space, a, b, override):
    """Iterate over mapping object b adding key-value pairs to dictionary a.
    b may be a dictionary, or any object supporting PyMapping_Keys()
    and PyObject_GetItem(). If override is true, existing pairs in a
    will be replaced if a matching key is found in b, otherwise pairs will
    only be added if there is not a matching key in a. Return 0 on
    success or -1 if an exception was raised.
    """
    raise NotImplementedError

@cpython_api([PyObject, PyObject], rffi.INT_real)
def PyDict_Update(space, a, b):
    """This is the same as PyDict_Merge(a, b, 1) in C, or a.update(b) in
    Python.  Return 0 on success or -1 if an exception was raised.
    """
    raise NotImplementedError

@cpython_api([PyObject, PyObject, rffi.INT_real], rffi.INT_real)
def PyDict_MergeFromSeq2(space, a, seq2, override):
    """Update or merge into dictionary a, from the key-value pairs in seq2.
    seq2 must be an iterable object producing iterable objects of length 2,
    viewed as key-value pairs.  In case of duplicate keys, the last wins if
    override is true, else the first wins. Return 0 on success or -1
    if an exception was raised. Equivalent Python (except for the return
    value):
    
    def PyDict_MergeFromSeq2(a, seq2, override):
        for key, value in seq2:
            if override or key not in a:
                a[key] = value
    """
    raise NotImplementedError

@cpython_api([rffi.INT_real], lltype.Void)
def PyErr_PrintEx(space, set_sys_last_vars):
    """Print a standard traceback to sys.stderr and clear the error indicator.
    Call this function only when the error indicator is set.  (Otherwise it will
    cause a fatal error!)
    
    If set_sys_last_vars is nonzero, the variables sys.last_type,
    sys.last_value and sys.last_traceback will be set to the
    type, value and traceback of the printed exception, respectively."""
    raise NotImplementedError

@cpython_api([], lltype.Void)
def PyErr_Print(space, ):
    """Alias for PyErr_PrintEx(1)."""
    raise NotImplementedError

@cpython_api([{PyObject**exc}, {PyObject**val}, {PyObject**tb}], lltype.Void)
def PyErr_NormalizeException(space, , , ):
    """Under certain circumstances, the values returned by PyErr_Fetch() below
    can be "unnormalized", meaning that *exc is a class object but *val is
    not an instance of the  same class.  This function can be used to instantiate
    the class in that case.  If the values are already normalized, nothing happens.
    The delayed normalization is implemented to improve performance."""
    raise NotImplementedError

@cpython_api([PyObjectP, PyObjectP, PyObjectP], lltype.Void)
def PyErr_Fetch(space, ptype, pvalue, ptraceback):
    """Retrieve the error indicator into three variables whose addresses are passed.
    If the error indicator is not set, set all three variables to NULL.  If it is
    set, it will be cleared and you own a reference to each object retrieved.  The
    value and traceback object may be NULL even when the type object is not.
    
    This function is normally only used by code that needs to handle exceptions or
    by code that needs to save and restore the error indicator temporarily."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject, PyObject], lltype.Void)
def PyErr_Restore(space, type, value, traceback):
    """Set  the error indicator from the three objects.  If the error indicator is
    already set, it is cleared first.  If the objects are NULL, the error
    indicator is cleared.  Do not pass a NULL type and non-NULL value or
    traceback.  The exception type should be a class.  Do not pass an invalid
    exception type or value. (Violating these rules will cause subtle problems
    later.)  This call takes away a reference to each object: you must own a
    reference to each object before the call and after the call you no longer own
    these references.  (If you don't understand this, don't use this function.  I
    warned you.)
    
    This function is normally only used by code that needs to save and restore the
    error indicator temporarily; use PyErr_Fetch() to save the current
    exception state."""
    raise NotImplementedError

@cpython_api([PyObject, rffi.CCHARP, ...], PyObject)
def PyErr_Format(space, exception, format, ):
    """This function sets the error indicator and returns NULL. exception should be
    a Python exception (class, not an instance).  format should be a string,
    containing format codes, similar to printf(). The width.precision
    before a format code is parsed, but the width part is ignored.
    
    % This should be exactly the same as the table in PyString_FromFormat.
    
    % One should just refer to the other.
    
    % The descriptions for %zd and %zu are wrong, but the truth is complicated
    
    % because not all compilers support the %z width modifier -- we fake it
    
    % when necessary via interpolating PY_FORMAT_SIZE_T.
    
    % Similar comments apply to the %ll width modifier and
    
    % PY_FORMAT_LONG_LONG.
    
    % %u, %lu, %zu should have "new in Python 2.5" blurbs.
    
    
    
    
    
    
    
    Format Characters
    
    Type
    
    Comment
    
    %%
    
    n/a
    
    The literal % character.
    
    %c
    
    int
    
    A single character,
    represented as an C int.
    
    %d
    
    int
    
    Exactly equivalent to
    printf("%d").
    
    %u
    
    unsigned int
    
    Exactly equivalent to
    printf("%u").
    
    %ld
    
    long
    
    Exactly equivalent to
    printf("%ld").
    
    %lu
    
    unsigned long
    
    Exactly equivalent to
    printf("%lu").
    
    %lld
    
    long long
    
    Exactly equivalent to
    printf("%lld").
    
    %llu
    
    unsigned
    long long
    
    Exactly equivalent to
    printf("%llu").
    
    %zd
    
    Py_ssize_t
    
    Exactly equivalent to
    printf("%zd").
    
    %zu
    
    size_t
    
    Exactly equivalent to
    printf("%zu").
    
    %i
    
    int
    
    Exactly equivalent to
    printf("%i").
    
    %x
    
    int
    
    Exactly equivalent to
    printf("%x").
    
    %s
    
    char*
    
    A null-terminated C character
    array.
    
    %p
    
    void*
    
    The hex representation of a C
    pointer. Mostly equivalent to
    printf("%p") except that
    it is guaranteed to start with
    the literal 0x regardless
    of what the platform's
    printf yields.
    
    An unrecognized format character causes all the rest of the format string to be
    copied as-is to the result string, and any extra arguments discarded.
    
    The "%lld" and "%llu" format specifiers are only available
    when HAVE_LONG_LONG is defined.
    
    Support for "%lld" and "%llu" added.
    Return value: always NULL."""
    raise NotImplementedError

@cpython_api([], rffi.INT_real)
def PyErr_BadArgument(space, ):
    """This is a shorthand for PyErr_SetString(PyExc_TypeError, message), where
    message indicates that a built-in operation was invoked with an illegal
    argument.  It is mostly for internal use."""
    raise NotImplementedError

@cpython_api([PyObject, rffi.CCHARP], PyObject)
def PyErr_SetFromErrnoWithFilename(space, type, filename):
    """Similar to PyErr_SetFromErrno(), with the additional behavior that if
    filename is not NULL, it is passed to the constructor of type as a third
    parameter.  In the case of exceptions such as IOError and OSError,
    this is used to define the filename attribute of the exception instance.
    Return value: always NULL."""
    raise NotImplementedError

@cpython_api([rffi.INT_real], PyObject)
def PyErr_SetFromWindowsErr(space, ierr):
    """This is a convenience function to raise WindowsError. If called with
    ierr of 0, the error code returned by a call to GetLastError()
    is used instead.  It calls the Win32 function FormatMessage() to retrieve
    the Windows description of error code given by ierr or GetLastError(),
    then it constructs a tuple object whose first item is the ierr value and whose
    second item is the corresponding error message (gotten from
    FormatMessage()), and then calls PyErr_SetObject(PyExc_WindowsError,
    object). This function always returns NULL. Availability: Windows.
    Return value: always NULL."""
    raise NotImplementedError

@cpython_api([PyObject, rffi.INT_real], PyObject)
def PyErr_SetExcFromWindowsErr(space, type, ierr):
    """Similar to PyErr_SetFromWindowsErr(), with an additional parameter
    specifying the exception type to be raised. Availability: Windows.
    
    
    Return value: always NULL."""
    raise NotImplementedError

@cpython_api([rffi.INT_real, rffi.CCHARP], PyObject)
def PyErr_SetFromWindowsErrWithFilename(space, ierr, filename):
    """Similar to PyErr_SetFromWindowsErr(), with the additional behavior that
    if filename is not NULL, it is passed to the constructor of
    WindowsError as a third parameter. Availability: Windows.
    Return value: always NULL."""
    raise NotImplementedError

@cpython_api([PyObject, rffi.INT_real, rffi.CCHARP], PyObject)
def PyErr_SetExcFromWindowsErrWithFilename(space, type, ierr, filename):
    """Similar to PyErr_SetFromWindowsErrWithFilename(), with an additional
    parameter specifying the exception type to be raised. Availability: Windows.
    
    
    Return value: always NULL."""
    raise NotImplementedError

@cpython_api([PyObject, rffi.CCHARP, rffi.INT_real], rffi.INT_real)
def PyErr_WarnEx(space, category, message, stacklevel):
    """Issue a warning message.  The category argument is a warning category (see
    below) or NULL; the message argument is a message string.  stacklevel is a
    positive number giving a number of stack frames; the warning will be issued from
    the  currently executing line of code in that stack frame.  A stacklevel of 1
    is the function calling PyErr_WarnEx(), 2 is  the function above that,
    and so forth.
    
    This function normally prints a warning message to sys.stderr; however, it is
    also possible that the user has specified that warnings are to be turned into
    errors, and in that case this will raise an exception.  It is also possible that
    the function raises an exception because of a problem with the warning machinery
    (the implementation imports the warnings module to do the heavy lifting).
    The return value is 0 if no exception is raised, or -1 if an exception
    is raised.  (It is not possible to determine whether a warning message is
    actually printed, nor what the reason is for the exception; this is
    intentional.)  If an exception is raised, the caller should do its normal
    exception handling (for example, Py_DECREF() owned references and return
    an error value).
    
    Warning categories must be subclasses of Warning; the default warning
    category is RuntimeWarning.  The standard Python warning categories are
    available as global variables whose names are PyExc_ followed by the Python
    exception name. These have the type PyObject*; they are all class
    objects. Their names are PyExc_Warning, PyExc_UserWarning,
    PyExc_UnicodeWarning, PyExc_DeprecationWarning,
    PyExc_SyntaxWarning, PyExc_RuntimeWarning, and
    PyExc_FutureWarning.  PyExc_Warning is a subclass of
    PyExc_Exception; the other warning categories are subclasses of
    PyExc_Warning.
    
    For information about warning control, see the documentation for the
    warnings module and the -W option in the command line
    documentation.  There is no C API for warning control."""
    raise NotImplementedError

@cpython_api([PyObject, rffi.CCHARP], rffi.INT_real)
def PyErr_Warn(space, category, message):
    """Issue a warning message.  The category argument is a warning category (see
    below) or NULL; the message argument is a message string.  The warning will
    appear to be issued from the function calling PyErr_Warn(), equivalent to
    calling PyErr_WarnEx() with a stacklevel of 1.
    
    Deprecated; use PyErr_WarnEx() instead."""
    raise NotImplementedError

@cpython_api([PyObject, rffi.CCHARP, rffi.CCHARP, rffi.INT_real, rffi.CCHARP, PyObject], rffi.INT_real)
def PyErr_WarnExplicit(space, category, message, filename, lineno, module, registry):
    """Issue a warning message with explicit control over all warning attributes.  This
    is a straightforward wrapper around the Python function
    warnings.warn_explicit(), see there for more information.  The module
    and registry arguments may be set to NULL to get the default effect
    described there."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, rffi.INT_real], rffi.INT_real)
def PyErr_WarnPy3k(space, message, stacklevel):
    """Issue a DeprecationWarning with the given message and stacklevel
    if the Py_Py3kWarningFlag flag is enabled.
    """
    raise NotImplementedError

@cpython_api([], lltype.Void)
def PyErr_SetInterrupt(space, ):
    """
    
    
    
    This function simulates the effect of a SIGINT signal arriving --- the
    next time PyErr_CheckSignals() is called,  KeyboardInterrupt will
    be raised.  It may be called without holding the interpreter lock.
    
    % XXX This was described as obsolete, but is used in
    
    % thread.interrupt_main() (used from IDLE), so it's still needed."""
    raise NotImplementedError

@cpython_api([rffi.INT_real], rffi.INT_real)
def PySignal_SetWakeupFd(space, fd):
    """This utility function specifies a file descriptor to which a '\0' byte will
    be written whenever a signal is received.  It returns the previous such file
    descriptor.  The value -1 disables the feature; this is the initial state.
    This is equivalent to signal.set_wakeup_fd() in Python, but without any
    error checking.  fd should be a valid file descriptor.  The function should
    only be called from the main thread."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, PyObject, PyObject], PyObject)
def PyErr_NewException(space, name, base, dict):
    """This utility function creates and returns a new exception object. The name
    argument must be the name of the new exception, a C string of the form
    module.class.  The base and dict arguments are normally NULL.  This
    creates a class object derived from Exception (accessible in C as
    PyExc_Exception).
    
    The __module__ attribute of the new class is set to the first part (up
    to the last dot) of the name argument, and the class name is set to the last
    part (after the last dot).  The base argument can be used to specify alternate
    base classes; it can either be only one class or a tuple of classes. The dict
    argument can be used to specify a dictionary of class variables and methods."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, rffi.CCHARP, PyObject, PyObject], PyObject)
def PyErr_NewExceptionWithDoc(space, name, doc, base, dict):
    """Same as PyErr_NewException(), except that the new exception class can
    easily be given a docstring: If doc is non-NULL, it will be used as the
    docstring for the exception class.
    """
    raise NotImplementedError

@cpython_api([PyObject], lltype.Void)
def PyErr_WriteUnraisable(space, obj):
    """This utility function prints a warning message to sys.stderr when an
    exception has been set but it is impossible for the interpreter to actually
    raise the exception.  It is used, for example, when an exception occurs in an
    __del__() method.
    
    The function is called with a single argument obj that identifies the context
    in which the unraisable exception occurred. The repr of obj will be printed in
    the warning message."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP], rffi.INT_real)
def Py_EnterRecursiveCall(space, where):
    """Marks a point where a recursive C-level call is about to be performed.
    
    If USE_STACKCHECK is defined, this function checks if the the OS
    stack overflowed using PyOS_CheckStack().  In this is the case, it
    sets a MemoryError and returns a nonzero value.
    
    The function then checks if the recursion limit is reached.  If this is the
    case, a RuntimeError is set and a nonzero value is returned.
    Otherwise, zero is returned.
    
    where should be a string such as " in instance check" to be
    concatenated to the RuntimeError message caused by the recursion depth
    limit."""
    raise NotImplementedError

@cpython_api([], lltype.Void)
def Py_LeaveRecursiveCall(space, ):
    """Ends a Py_EnterRecursiveCall().  Must be called once for each
    successful invocation of Py_EnterRecursiveCall()."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PyFile_Check(space, p):
    """Return true if its argument is a PyFileObject or a subtype of
    PyFileObject.
    
    Allowed subtypes to be accepted."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PyFile_CheckExact(space, p):
    """Return true if its argument is a PyFileObject, but not a subtype of
    PyFileObject.
    """
    raise NotImplementedError

@cpython_api([rffi.CCHARP, rffi.CCHARP], PyObject)
def PyFile_FromString(space, filename, mode):
    """
    
    
    
    On success, return a new file object that is opened on the file given by
    filename, with a file mode given by mode, where mode has the same
    semantics as the standard C routine fopen().  On failure, return NULL."""
    raise NotImplementedError

@cpython_api([{FILE*}, rffi.CCHARP, rffi.CCHARP, rffi.INT_real], PyObject)
def PyFile_FromFile(space, fp, name, mode, (*close)(FILE*)):
    """Create a new PyFileObject from the already-open standard C file
    pointer, fp.  The function close will be called when the file should be
    closed.  Return NULL on failure."""
    raise NotImplementedError

@cpython_api([PyObject], {FILE*})
def PyFile_AsFile(space, p):
    """Return the file object associated with p as a FILE*.
    
    If the caller will ever use the returned FILE* object while
    the GIL is released it must also call the PyFile_IncUseCount() and
    PyFile_DecUseCount() functions described below as appropriate."""
    raise NotImplementedError

@cpython_api([{PyFileObject*}], lltype.Void)
def PyFile_IncUseCount(space, p):
    """Increments the PyFileObject's internal use count to indicate
    that the underlying FILE* is being used.
    This prevents Python from calling f_close() on it from another thread.
    Callers of this must call PyFile_DecUseCount() when they are
    finished with the FILE*.  Otherwise the file object will
    never be closed by Python.
    
    The GIL must be held while calling this function.
    
    The suggested use is to call this after PyFile_AsFile() just before
    you release the GIL.
    """
    raise NotImplementedError

@cpython_api([{PyFileObject*}], lltype.Void)
def PyFile_DecUseCount(space, p):
    """Decrements the PyFileObject's internal unlocked_count member to
    indicate that the caller is done with its own use of the FILE*.
    This may only be called to undo a prior call to PyFile_IncUseCount().
    
    The GIL must be held while calling this function.
    """
    raise NotImplementedError

@cpython_api([PyObject, rffi.INT_real], PyObject)
def PyFile_GetLine(space, p, n):
    """
    
    
    
    Equivalent to p.readline([n]), this function reads one line from the
    object p.  p may be a file object or any object with a readline()
    method.  If n is 0, exactly one line is read, regardless of the length of
    the line.  If n is greater than 0, no more than n bytes will be read
    from the file; a partial line can be returned.  In both cases, an empty string
    is returned if the end of the file is reached immediately.  If n is less than
    0, however, one line is read regardless of length, but EOFError is
    raised if the end of the file is reached immediately."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject, borrowed=True)
def PyFile_Name(space, p):
    """Return the name of the file specified by p as a string object."""
    raise NotImplementedError

@cpython_api([{PyFileObject*}, rffi.INT_real], lltype.Void)
def PyFile_SetBufSize(space, p, n):
    """
    
    
    
    Available on systems with setvbuf() only.  This should only be called
    immediately after file object creation."""
    raise NotImplementedError

@cpython_api([{PyFileObject*}, rffi.CCHARP], rffi.INT_real)
def PyFile_SetEncoding(space, p, enc):
    """Set the file's encoding for Unicode output to enc. Return 1 on success and 0
    on failure.
    """
    raise NotImplementedError

@cpython_api([{PyFileObject*}, rffi.CCHARP, {*errors}], rffi.INT_real)
def PyFile_SetEncodingAndErrors(space, p, enc, ):
    """Set the file's encoding for Unicode output to enc, and its error
    mode to err. Return 1 on success and 0 on failure.
    """
    raise NotImplementedError

@cpython_api([PyObject, rffi.INT_real], rffi.INT_real)
def PyFile_SoftSpace(space, p, newflag):
    """
    
    
    
    This function exists for internal use by the interpreter.  Set the
    softspace attribute of p to newflag and return the previous value.
    p does not have to be a file object for this function to work properly; any
    object is supported (thought its only interesting if the softspace
    attribute can be set).  This function clears any errors, and will return 0
    as the previous value if the attribute either does not exist or if there were
    errors in retrieving it.  There is no way to detect errors from this function,
    but doing so should not be needed."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject, rffi.INT_real], rffi.INT_real)
def PyFile_WriteObject(space, obj, p, flags):
    """
    
    
    
    Write object obj to file object p.  The only supported flag for flags is
    Py_PRINT_RAW; if given, the str() of the object is written
    instead of the repr().  Return 0 on success or -1 on failure; the
    appropriate exception will be set."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, PyObject], rffi.INT_real)
def PyFile_WriteString(space, s, p):
    """Write string s to file object p.  Return 0 on success or -1 on
    failure; the appropriate exception will be set."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PyFloat_Check(space, p):
    """Return true if its argument is a PyFloatObject or a subtype of
    PyFloatObject.
    
    Allowed subtypes to be accepted."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PyFloat_CheckExact(space, p):
    """Return true if its argument is a PyFloatObject, but not a subtype of
    PyFloatObject.
    """
    raise NotImplementedError

@cpython_api([PyObject, {char**}], PyObject)
def PyFloat_FromString(space, str, pend):
    """Create a PyFloatObject object based on the string value in str, or
    NULL on failure.  The pend argument is ignored.  It remains only for
    backward compatibility."""
    raise NotImplementedError

@cpython_api([PyObject], {double})
def PyFloat_AS_DOUBLE(space, pyfloat):
    """Return a C double representation of the contents of pyfloat, but
    without error checking."""
    raise NotImplementedError

@cpython_api([rffi.VOIDP_real], PyObject)
def PyFloat_GetInfo(space, ):
    """Return a structseq instance which contains information about the
    precision, minimum and maximum values of a float. It's a thin wrapper
    around the header file float.h.
    """
    raise NotImplementedError

@cpython_api([], {double})
def PyFloat_GetMax(space, ):
    """Return the maximum representable finite float DBL_MAX as C double.
    """
    raise NotImplementedError

@cpython_api([], {double})
def PyFloat_GetMin(space, ):
    """Return the minimum normalized positive float DBL_MIN as C double.
    """
    raise NotImplementedError

@cpython_api([], rffi.INT_real)
def PyFloat_ClearFreeList(space, ):
    """Clear the float free list. Return the number of items that could not
    be freed.
    """
    raise NotImplementedError

@cpython_api([rffi.CCHARP, {PyFloatObject*}], lltype.Void)
def PyFloat_AsString(space, buf, v):
    """Convert the argument v to a string, using the same rules as
    str(). The length of buf should be at least 100.
    
    This function is unsafe to call because it writes to a buffer whose
    length it does not know.
    
    Use PyObject_Str() or PyOS_double_to_string() instead."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, {PyFloatObject*}], lltype.Void)
def PyFloat_AsReprString(space, buf, v):
    """Same as PyFloat_AsString, except uses the same rules as
    repr().  The length of buf should be at least 100.
    
    This function is unsafe to call because it writes to a buffer whose
    length it does not know.
    
    Use PyObject_Repr() or PyOS_double_to_string() instead."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PyFunction_Check(space, o):
    """Return true if o is a function object (has type PyFunction_Type).
    The parameter must not be NULL."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], PyObject)
def PyFunction_New(space, code, globals):
    """Return a new function object associated with the code object code. globals
    must be a dictionary with the global variables accessible to the function.
    
    The function's docstring, name and __module__ are retrieved from the code
    object, the argument defaults and closure are set to NULL."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject, borrowed=True)
def PyFunction_GetCode(space, op):
    """Return the code object associated with the function object op."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject, borrowed=True)
def PyFunction_GetGlobals(space, op):
    """Return the globals dictionary associated with the function object op."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject, borrowed=True)
def PyFunction_GetModule(space, op):
    """Return the __module__ attribute of the function object op. This is normally
    a string containing the module name, but can be set to any other object by
    Python code."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject, borrowed=True)
def PyFunction_GetDefaults(space, op):
    """Return the argument default values of the function object op. This can be a
    tuple of arguments or NULL."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], rffi.INT_real)
def PyFunction_SetDefaults(space, op, defaults):
    """Set the argument default values for the function object op. defaults must be
    Py_None or a tuple.
    
    Raises SystemError and returns -1 on failure."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject, borrowed=True)
def PyFunction_GetClosure(space, op):
    """Return the closure associated with the function object op. This can be NULL
    or a tuple of cell objects."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], rffi.INT_real)
def PyFunction_SetClosure(space, op, closure):
    """Set the closure associated with the function object op. closure must be
    Py_None or a tuple of cell objects.
    
    Raises SystemError and returns -1 on failure."""
    raise NotImplementedError

@cpython_api([{TYPE}, PyTypeObjectPtr], {TYPE*})
def PyObject_GC_New(space, , type):
    """Analogous to PyObject_New() but for container objects with the
    Py_TPFLAGS_HAVE_GC flag set."""
    raise NotImplementedError

@cpython_api([{TYPE}, PyTypeObjectPtr, Py_ssize_t], {TYPE*})
def PyObject_GC_NewVar(space, , type, size):
    """Analogous to PyObject_NewVar() but for container objects with the
    Py_TPFLAGS_HAVE_GC flag set.
    
    This function used an int type for size. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([{TYPE}, PyObject, Py_ssize_t], {TYPE*})
def PyObject_GC_Resize(space, , op, newsize):
    """Resize an object allocated by PyObject_NewVar().  Returns the
    resized object or NULL on failure.
    
    This function used an int type for newsize. This might
    require changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject], lltype.Void)
def PyObject_GC_Track(space, op):
    """Adds the object op to the set of container objects tracked by the
    collector.  The collector can run at unexpected times so objects must be
    valid while being tracked.  This should be called once all the fields
    followed by the tp_traverse handler become valid, usually near the
    end of the constructor."""
    raise NotImplementedError

@cpython_api([PyObject], lltype.Void)
def _PyObject_GC_TRACK(space, op):
    """A macro version of PyObject_GC_Track().  It should not be used for
    extension modules."""
    raise NotImplementedError

@cpython_api([{void*}], lltype.Void)
def PyObject_GC_Del(space, op):
    """Releases memory allocated to an object using PyObject_GC_New() or
    PyObject_GC_NewVar()."""
    raise NotImplementedError

@cpython_api([{void*}], lltype.Void)
def PyObject_GC_UnTrack(space, op):
    """Remove the object op from the set of container objects tracked by the
    collector.  Note that PyObject_GC_Track() can be called again on
    this object to add it back to the set of tracked objects.  The deallocator
    (tp_dealloc handler) should call this for the object before any of
    the fields used by the tp_traverse handler become invalid."""
    raise NotImplementedError

@cpython_api([PyObject], lltype.Void)
def _PyObject_GC_UNTRACK(space, op):
    """A macro version of PyObject_GC_UnTrack().  It should not be used for
    extension modules."""
    raise NotImplementedError

@cpython_api([PyObject], lltype.Void)
def Py_VISIT(space, o):
    """Call the visit callback, with arguments o and arg. If visit returns
    a non-zero value, then return it.  Using this macro, tp_traverse
    handlers look like:
    
    static int
    my_traverse(Noddy *self, visitproc visit, void *arg)
    {
        Py_VISIT(self->foo);
        Py_VISIT(self->bar);
        return 0;
    }
    """
    raise NotImplementedError

@cpython_api([{ob}], rffi.INT_real)
def PyGen_Check(space, ):
    """Return true if ob is a generator object; ob must not be NULL."""
    raise NotImplementedError

@cpython_api([{ob}], rffi.INT_real)
def PyGen_CheckExact(space, ):
    """Return true if ob's type is PyGen_Type is a generator object; ob must not
    be NULL."""
    raise NotImplementedError

@cpython_api([{PyFrameObject*}], PyObject)
def PyGen_New(space, frame):
    """Create and return a new generator object based on the frame object. A
    reference to frame is stolen by this function. The parameter must not be
    NULL."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP], PyObject)
def PyImport_ImportModule(space, name):
    """
    
    
    
    This is a simplified interface to PyImport_ImportModuleEx() below,
    leaving the globals and locals arguments set to NULL and level set
    to 0.  When the name
    argument contains a dot (when it specifies a submodule of a package), the
    fromlist argument is set to the list ['*'] so that the return value is the
    named module rather than the top-level package containing it as would otherwise
    be the case.  (Unfortunately, this has an additional side effect when name in
    fact specifies a subpackage instead of a submodule: the submodules specified in
    the package's __all__ variable are  loaded.)  Return a new reference to the
    imported module, or NULL with an exception set on failure.  Before Python 2.4,
    the module may still be created in the failure case --- examine sys.modules
    to find out.  Starting with Python 2.4, a failing import of a module no longer
    leaves the module in sys.modules.
    
    Failing imports remove incomplete module objects.
    
    Always uses absolute imports."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP], PyObject)
def PyImport_ImportModuleNoBlock(space, name):
    """This version of PyImport_ImportModule() does not block. It's intended
    to be used in C functions that import other modules to execute a function.
    The import may block if another thread holds the import lock. The function
    PyImport_ImportModuleNoBlock() never blocks. It first tries to fetch
    the module from sys.modules and falls back to PyImport_ImportModule()
    unless the lock is held, in which case the function will raise an
    ImportError.
    """
    raise NotImplementedError

@cpython_api([rffi.CCHARP, PyObject, PyObject, PyObject], PyObject)
def PyImport_ImportModuleEx(space, name, globals, locals, fromlist):
    """
    
    
    
    Import a module.  This is best described by referring to the built-in Python
    function __import__(), as the standard __import__() function calls
    this function directly.
    
    The return value is a new reference to the imported module or top-level package,
    or NULL with an exception set on failure (before Python 2.4, the module may
    still be created in this case).  Like for __import__(), the return value
    when a submodule of a package was requested is normally the top-level package,
    unless a non-empty fromlist was given.
    
    Failing imports remove incomplete module objects.
    
    The function is an alias for PyImport_ImportModuleLevel() with
    -1 as level, meaning relative import."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, PyObject, PyObject, PyObject, rffi.INT_real], PyObject)
def PyImport_ImportModuleLevel(space, name, globals, locals, fromlist, level):
    """Import a module.  This is best described by referring to the built-in Python
    function __import__(), as the standard __import__() function calls
    this function directly.
    
    The return value is a new reference to the imported module or top-level package,
    or NULL with an exception set on failure.  Like for __import__(),
    the return value when a submodule of a package was requested is normally the
    top-level package, unless a non-empty fromlist was given.
    """
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyImport_Import(space, name):
    """
    
    
    
    This is a higher-level interface that calls the current "import hook function".
    It invokes the __import__() function from the __builtins__ of the
    current globals.  This means that the import is done using whatever import hooks
    are installed in the current environment, e.g. by rexec or ihooks.
    
    Always uses absolute imports."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyImport_ReloadModule(space, m):
    """
    
    
    
    Reload a module.  This is best described by referring to the built-in Python
    function reload(), as the standard reload() function calls this
    function directly.  Return a new reference to the reloaded module, or NULL
    with an exception set on failure (the module still exists in this case)."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP], PyObject, borrowed=True)
def PyImport_AddModule(space, name):
    """Return the module object corresponding to a module name.  The name argument
    may be of the form package.module. First check the modules dictionary if
    there's one there, and if not, create a new one and insert it in the modules
    dictionary. Return NULL with an exception set on failure.
    
    This function does not load or import the module; if the module wasn't already
    loaded, you will get an empty module object. Use PyImport_ImportModule()
    or one of its variants to import a module.  Package structures implied by a
    dotted name for name are not created if not already present."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, PyObject], PyObject)
def PyImport_ExecCodeModule(space, name, co):
    """
    
    
    
    Given a module name (possibly of the form package.module) and a code object
    read from a Python bytecode file or obtained from the built-in function
    compile(), load the module.  Return a new reference to the module object,
    or NULL with an exception set if an error occurred.  Before Python 2.4, the
    module could still be created in error cases.  Starting with Python 2.4, name
    is removed from sys.modules in error cases, and even if name was already
    in sys.modules on entry to PyImport_ExecCodeModule().  Leaving
    incompletely initialized modules in sys.modules is dangerous, as imports of
    such modules have no way to know that the module object is an unknown (and
    probably damaged with respect to the module author's intents) state.
    
    This function will reload the module if it was already imported.  See
    PyImport_ReloadModule() for the intended way to reload a module.
    
    If name points to a dotted name of the form package.module, any package
    structures not already created will still not be created.
    
    name is removed from sys.modules in error cases."""
    raise NotImplementedError

@cpython_api([], lltype.Signed)
def PyImport_GetMagicNumber(space, ):
    """Return the magic number for Python bytecode files (a.k.a. .pyc and
    .pyo files).  The magic number should be present in the first four bytes
    of the bytecode file, in little-endian byte order."""
    raise NotImplementedError

@cpython_api([], PyObject, borrowed=True)
def PyImport_GetModuleDict(space, ):
    """Return the dictionary used for the module administration (a.k.a.
    sys.modules).  Note that this is a per-interpreter variable."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyImport_GetImporter(space, path):
    """Return an importer object for a sys.path/pkg.__path__ item
    path, possibly by fetching it from the sys.path_importer_cache
    dict.  If it wasn't yet cached, traverse sys.path_hooks until a hook
    is found that can handle the path item.  Return None if no hook could;
    this tells our caller it should fall back to the built-in import mechanism.
    Cache the result in sys.path_importer_cache.  Return a new reference
    to the importer object.
    """
    raise NotImplementedError

@cpython_api([], lltype.Void)
def _PyImport_Init(space, ):
    """Initialize the import mechanism.  For internal use only."""
    raise NotImplementedError

@cpython_api([], lltype.Void)
def PyImport_Cleanup(space, ):
    """Empty the module table.  For internal use only."""
    raise NotImplementedError

@cpython_api([], lltype.Void)
def _PyImport_Fini(space, ):
    """Finalize the import mechanism.  For internal use only."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, rffi.CCHARP], PyObject)
def _PyImport_FindExtension(space, , ):
    """For internal use only."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, rffi.CCHARP], PyObject)
def _PyImport_FixupExtension(space, , ):
    """For internal use only."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP], rffi.INT_real)
def PyImport_ImportFrozenModule(space, name):
    """Load a frozen module named name.  Return 1 for success, 0 if the
    module is not found, and -1 with an exception set if the initialization
    failed.  To access the imported module on a successful load, use
    PyImport_ImportModule().  (Note the misnomer --- this function would
    reload the module if it was already imported.)"""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, rffi.VOIDP_real], rffi.INT_real)
def PyImport_AppendInittab(space, name, (*initfunc)(void)):
    """Add a single module to the existing table of built-in modules.  This is a
    convenience wrapper around PyImport_ExtendInittab(), returning -1 if
    the table could not be extended.  The new module can be imported by the name
    name, and uses the function initfunc as the initialization function called
    on the first attempted import.  This should be called before
    Py_Initialize()."""
    raise NotImplementedError

@cpython_api([{struct _inittab*}], rffi.INT_real)
def PyImport_ExtendInittab(space, newtab):
    """Add a collection of modules to the table of built-in modules.  The newtab
    array must end with a sentinel entry which contains NULL for the name
    field; failure to provide the sentinel value can result in a memory fault.
    Returns 0 on success or -1 if insufficient memory could be allocated to
    extend the internal table.  In the event of failure, no modules are added to the
    internal table.  This should be called before Py_Initialize()."""
    raise NotImplementedError

@cpython_api([], lltype.Void)
def Py_Initialize(space, ):
    """
    
    
    
    Initialize the Python interpreter.  In an application embedding  Python, this
    should be called before using any other Python/C API functions; with the
    exception of Py_SetProgramName(), PyEval_InitThreads(),
    PyEval_ReleaseLock(), and PyEval_AcquireLock(). This initializes
    the table of loaded modules (sys.modules), and creates the fundamental
    modules __builtin__, __main__ and sys.  It also initializes
    the module search path (sys.path). It does not set sys.argv; use
    PySys_SetArgv() for that.  This is a no-op when called for a second time
    (without calling Py_Finalize() first).  There is no return value; it is a
    fatal error if the initialization fails."""
    raise NotImplementedError

@cpython_api([rffi.INT_real], lltype.Void)
def Py_InitializeEx(space, initsigs):
    """This function works like Py_Initialize() if initsigs is 1. If
    initsigs is 0, it skips initialization registration of signal handlers, which
    might be useful when Python is embedded.
    """
    raise NotImplementedError

@cpython_api([], lltype.Void)
def Py_Finalize(space, ):
    """Undo all initializations made by Py_Initialize() and subsequent use of
    Python/C API functions, and destroy all sub-interpreters (see
    Py_NewInterpreter() below) that were created and not yet destroyed since
    the last call to Py_Initialize().  Ideally, this frees all memory
    allocated by the Python interpreter.  This is a no-op when called for a second
    time (without calling Py_Initialize() again first).  There is no return
    value; errors during finalization are ignored.
    
    This function is provided for a number of reasons.  An embedding application
    might want to restart Python without having to restart the application itself.
    An application that has loaded the Python interpreter from a dynamically
    loadable library (or DLL) might want to free all memory allocated by Python
    before unloading the DLL. During a hunt for memory leaks in an application a
    developer might want to free all memory allocated by Python before exiting from
    the application.
    
    Bugs and caveats: The destruction of modules and objects in modules is done
    in random order; this may cause destructors (__del__() methods) to fail
    when they depend on other objects (even functions) or modules.  Dynamically
    loaded extension modules loaded by Python are not unloaded.  Small amounts of
    memory allocated by the Python interpreter may not be freed (if you find a leak,
    please report it).  Memory tied up in circular references between objects is not
    freed.  Some memory allocated by extension modules may not be freed.  Some
    extensions may not work properly if their initialization routine is called more
    than once; this can happen if an application calls Py_Initialize() and
    Py_Finalize() more than once."""
    raise NotImplementedError

@cpython_api([], {PyThreadState*})
def Py_NewInterpreter(space, ):
    """
    
    
    
    Create a new sub-interpreter.  This is an (almost) totally separate environment
    for the execution of Python code.  In particular, the new interpreter has
    separate, independent versions of all imported modules, including the
    fundamental modules __builtin__, __main__ and sys.  The
    table of loaded modules (sys.modules) and the module search path
    (sys.path) are also separate.  The new environment has no sys.argv
    variable.  It has new standard I/O stream file objects sys.stdin,
    sys.stdout and sys.stderr (however these refer to the same underlying
    FILE structures in the C library).
    
    The return value points to the first thread state created in the new
    sub-interpreter.  This thread state is made in the current thread state.
    Note that no actual thread is created; see the discussion of thread states
    below.  If creation of the new interpreter is unsuccessful, NULL is
    returned; no exception is set since the exception state is stored in the
    current thread state and there may not be a current thread state.  (Like all
    other Python/C API functions, the global interpreter lock must be held before
    calling this function and is still held when it returns; however, unlike most
    other Python/C API functions, there needn't be a current thread state on
    entry.)
    
    
    
    
    
    Extension modules are shared between (sub-)interpreters as follows: the first
    time a particular extension is imported, it is initialized normally, and a
    (shallow) copy of its module's dictionary is squirreled away.  When the same
    extension is imported by another (sub-)interpreter, a new module is initialized
    and filled with the contents of this copy; the extension's init function is
    not called.  Note that this is different from what happens when an extension is
    imported after the interpreter has been completely re-initialized by calling
    Py_Finalize() and Py_Initialize(); in that case, the extension's
    initmodule function is called again.
    
    
    
    
    
    Bugs and caveats: Because sub-interpreters (and the main interpreter) are
    part of the same process, the insulation between them isn't perfect --- for
    example, using low-level file operations like  os.close() they can
    (accidentally or maliciously) affect each other's open files.  Because of the
    way extensions are shared between (sub-)interpreters, some extensions may not
    work properly; this is especially likely when the extension makes use of
    (static) global variables, or when the extension manipulates its module's
    dictionary after its initialization.  It is possible to insert objects created
    in one sub-interpreter into a namespace of another sub-interpreter; this should
    be done with great care to avoid sharing user-defined functions, methods,
    instances or classes between sub-interpreters, since import operations executed
    by such objects may affect the wrong (sub-)interpreter's dictionary of loaded
    modules.  (XXX This is a hard-to-fix bug that will be addressed in a future
    release.)
    
    Also note that the use of this functionality is incompatible with extension
    modules such as PyObjC and ctypes that use the PyGILState_*() APIs (and
    this is inherent in the way the PyGILState_*() functions work).  Simple
    things may work, but confusing behavior will always be near."""
    raise NotImplementedError

@cpython_api([{PyThreadState*}], lltype.Void)
def Py_EndInterpreter(space, tstate):
    """
    
    
    
    Destroy the (sub-)interpreter represented by the given thread state. The given
    thread state must be the current thread state.  See the discussion of thread
    states below.  When the call returns, the current thread state is NULL.  All
    thread states associated with this interpreter are destroyed.  (The global
    interpreter lock must be held before calling this function and is still held
    when it returns.)  Py_Finalize() will destroy all sub-interpreters that
    haven't been explicitly destroyed at that point."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP], lltype.Void)
def Py_SetProgramName(space, name):
    """
    
    
    
    This function should be called before Py_Initialize() is called for
    the first time, if it is called at all.  It tells the interpreter the value
    of the argv[0] argument to the main() function of the program.
    This is used by Py_GetPath() and some other functions below to find
    the Python run-time libraries relative to the interpreter executable.  The
    default value is 'python'.  The argument should point to a
    zero-terminated character string in static storage whose contents will not
    change for the duration of the program's execution.  No code in the Python
    interpreter will change the contents of this storage."""
    raise NotImplementedError

@cpython_api([], rffi.CCHARP)
def Py_GetProgramName(space, ):
    """
    
    
    
    Return the program name set with Py_SetProgramName(), or the default.
    The returned string points into static storage; the caller should not modify its
    value."""
    raise NotImplementedError

@cpython_api([], rffi.CCHARP)
def Py_GetPrefix(space, ):
    """Return the prefix for installed platform-independent files. This is derived
    through a number of complicated rules from the program name set with
    Py_SetProgramName() and some environment variables; for example, if the
    program name is '/usr/local/bin/python', the prefix is '/usr/local'. The
    returned string points into static storage; the caller should not modify its
    value.  This corresponds to the prefix variable in the top-level
    Makefile and the --prefix argument to the configure
    script at build time.  The value is available to Python code as sys.prefix.
    It is only useful on Unix.  See also the next function."""
    raise NotImplementedError

@cpython_api([], rffi.CCHARP)
def Py_GetExecPrefix(space, ):
    """Return the exec-prefix for installed platform-dependent files.  This is
    derived through a number of complicated rules from the program name set with
    Py_SetProgramName() and some environment variables; for example, if the
    program name is '/usr/local/bin/python', the exec-prefix is
    '/usr/local'.  The returned string points into static storage; the caller
    should not modify its value.  This corresponds to the exec_prefix
    variable in the top-level Makefile and the --exec-prefix
    argument to the configure script at build  time.  The value is
    available to Python code as sys.exec_prefix.  It is only useful on Unix.
    
    Background: The exec-prefix differs from the prefix when platform dependent
    files (such as executables and shared libraries) are installed in a different
    directory tree.  In a typical installation, platform dependent files may be
    installed in the /usr/local/plat subtree while platform independent may
    be installed in /usr/local.
    
    Generally speaking, a platform is a combination of hardware and software
    families, e.g.  Sparc machines running the Solaris 2.x operating system are
    considered the same platform, but Intel machines running Solaris 2.x are another
    platform, and Intel machines running Linux are yet another platform.  Different
    major revisions of the same operating system generally also form different
    platforms.  Non-Unix operating systems are a different story; the installation
    strategies on those systems are so different that the prefix and exec-prefix are
    meaningless, and set to the empty string. Note that compiled Python bytecode
    files are platform independent (but not independent from the Python version by
    which they were compiled!).
    
    System administrators will know how to configure the mount or
    automount programs to share /usr/local between platforms
    while having /usr/local/plat be a different filesystem for each
    platform."""
    raise NotImplementedError

@cpython_api([], rffi.CCHARP)
def Py_GetProgramFullPath(space, ):
    """
    
    
    
    Return the full program name of the Python executable; this is  computed as a
    side-effect of deriving the default module search path  from the program name
    (set by Py_SetProgramName() above). The returned string points into
    static storage; the caller should not modify its value.  The value is available
    to Python code as sys.executable."""
    raise NotImplementedError

@cpython_api([], rffi.CCHARP)
def Py_GetPath(space, ):
    """
    
    
    
    Return the default module search path; this is computed from the program name
    (set by Py_SetProgramName() above) and some environment variables.
    The returned string consists of a series of directory names separated by a
    platform dependent delimiter character.  The delimiter character is ':'
    on Unix and Mac OS X, ';' on Windows.  The returned string points into
    static storage; the caller should not modify its value.  The list
    sys.path is initialized with this value on interpreter startup; it
    can be (and usually is) modified later to change the search path for loading
    modules.
    
    XXX should give the exact rules"""
    raise NotImplementedError

@cpython_api([], rffi.CCHARP)
def Py_GetVersion(space, ):
    """Return the version of this Python interpreter.  This is a string that looks
    something like
    
    "1.5 (#67, Dec 31 1997, 22:34:28) [GCC 2.7.2.2]"
    
    
    
    
    
    The first word (up to the first space character) is the current Python version;
    the first three characters are the major and minor version separated by a
    period.  The returned string points into static storage; the caller should not
    modify its value.  The value is available to Python code as sys.version."""
    raise NotImplementedError

@cpython_api([], rffi.CCHARP)
def Py_GetPlatform(space, ):
    """
    
    
    
    Return the platform identifier for the current platform.  On Unix, this is
    formed from the "official" name of the operating system, converted to lower
    case, followed by the major revision number; e.g., for Solaris 2.x, which is
    also known as SunOS 5.x, the value is 'sunos5'.  On Mac OS X, it is
    'darwin'.  On Windows, it is 'win'.  The returned string points into
    static storage; the caller should not modify its value.  The value is available
    to Python code as sys.platform."""
    raise NotImplementedError

@cpython_api([], rffi.CCHARP)
def Py_GetCopyright(space, ):
    """Return the official copyright string for the current Python version, for example
    
    'Copyright 1991-1995 Stichting Mathematisch Centrum, Amsterdam'
    
    
    
    
    
    The returned string points into static storage; the caller should not modify its
    value.  The value is available to Python code as sys.copyright."""
    raise NotImplementedError

@cpython_api([], rffi.CCHARP)
def Py_GetCompiler(space, ):
    """Return an indication of the compiler used to build the current Python version,
    in square brackets, for example:
    
    "[GCC 2.7.2.2]"
    
    
    
    
    
    The returned string points into static storage; the caller should not modify its
    value.  The value is available to Python code as part of the variable
    sys.version."""
    raise NotImplementedError

@cpython_api([], rffi.CCHARP)
def Py_GetBuildInfo(space, ):
    """Return information about the sequence number and build date and time  of the
    current Python interpreter instance, for example
    
    "#67, Aug  1 1997, 22:34:28"
    
    
    
    
    
    The returned string points into static storage; the caller should not modify its
    value.  The value is available to Python code as part of the variable
    sys.version."""
    raise NotImplementedError

@cpython_api([rffi.INT_real, {char**}], lltype.Void)
def PySys_SetArgv(space, argc, argv):
    """
    
    
    
    Set sys.argv based on argc and argv.  These parameters are
    similar to those passed to the program's main() function with the
    difference that the first entry should refer to the script file to be
    executed rather than the executable hosting the Python interpreter.  If there
    isn't a script that will be run, the first entry in argv can be an empty
    string.  If this function fails to initialize sys.argv, a fatal
    condition is signalled using Py_FatalError().
    
    This function also prepends the executed script's path to sys.path.
    If no script is executed (in the case of calling python -c or just the
    interactive interpreter), the empty string is used instead.
    
    XXX impl. doesn't seem consistent in allowing 0/NULL for the params;
    check w/ Guido."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP], lltype.Void)
def Py_SetPythonHome(space, home):
    """Set the default "home" directory, that is, the location of the standard
    Python libraries.  The libraries are searched in
    home/lib/pythonversion and home/lib/pythonversion.
    The argument should point to a zero-terminated character string in static
    storage whose contents will not change for the duration of the program's
    execution.  No code in the Python interpreter will change the contents of
    this storage."""
    raise NotImplementedError

@cpython_api([], rffi.CCHARP)
def Py_GetPythonHome(space, ):
    """Return the default "home", that is, the value set by a previous call to
    Py_SetPythonHome(), or the value of the PYTHONHOME
    environment variable if it is set."""
    raise NotImplementedError

@cpython_api([], lltype.Void)
def PyEval_InitThreads(space, ):
    """
    
    
    
    Initialize and acquire the global interpreter lock.  It should be called in the
    main thread before creating a second thread or engaging in any other thread
    operations such as PyEval_ReleaseLock() or
    PyEval_ReleaseThread(tstate). It is not needed before calling
    PyEval_SaveThread() or PyEval_RestoreThread().
    
    
    
    
    
    This is a no-op when called for a second time.  It is safe to call this function
    before calling Py_Initialize().
    
    
    
    
    
    When only the main thread exists, no GIL operations are needed. This is a
    common situation (most Python programs do not use threads), and the lock
    operations slow the interpreter down a bit. Therefore, the lock is not
    created initially.  This situation is equivalent to having acquired the lock:
    when there is only a single thread, all object accesses are safe.  Therefore,
    when this function initializes the global interpreter lock, it also acquires
    it.  Before the Python thread module creates a new thread, knowing
    that either it has the lock or the lock hasn't been created yet, it calls
    PyEval_InitThreads().  When this call returns, it is guaranteed that
    the lock has been created and that the calling thread has acquired it.
    
    It is not safe to call this function when it is unknown which thread (if
    any) currently has the global interpreter lock.
    
    This function is not available when thread support is disabled at compile time."""
    raise NotImplementedError

@cpython_api([], rffi.INT_real)
def PyEval_ThreadsInitialized(space, ):
    """Returns a non-zero value if PyEval_InitThreads() has been called.  This
    function can be called without holding the GIL, and therefore can be used to
    avoid calls to the locking API when running single-threaded.  This function is
    not available when thread support is disabled at compile time.
    """
    raise NotImplementedError

@cpython_api([], lltype.Void)
def PyEval_AcquireLock(space, ):
    """Acquire the global interpreter lock.  The lock must have been created earlier.
    If this thread already has the lock, a deadlock ensues.  This function is not
    available when thread support is disabled at compile time."""
    raise NotImplementedError

@cpython_api([], lltype.Void)
def PyEval_ReleaseLock(space, ):
    """Release the global interpreter lock.  The lock must have been created earlier.
    This function is not available when thread support is disabled at compile time."""
    raise NotImplementedError

@cpython_api([{PyThreadState*}], lltype.Void)
def PyEval_AcquireThread(space, tstate):
    """Acquire the global interpreter lock and set the current thread state to
    tstate, which should not be NULL.  The lock must have been created earlier.
    If this thread already has the lock, deadlock ensues.  This function is not
    available when thread support is disabled at compile time."""
    raise NotImplementedError

@cpython_api([{PyThreadState*}], lltype.Void)
def PyEval_ReleaseThread(space, tstate):
    """Reset the current thread state to NULL and release the global interpreter
    lock.  The lock must have been created earlier and must be held by the current
    thread.  The tstate argument, which must not be NULL, is only used to check
    that it represents the current thread state --- if it isn't, a fatal error is
    reported. This function is not available when thread support is disabled at
    compile time."""
    raise NotImplementedError

@cpython_api([], {PyThreadState*})
def PyEval_SaveThread(space, ):
    """Release the global interpreter lock (if it has been created and thread
    support is enabled) and reset the thread state to NULL, returning the
    previous thread state (which is not NULL).  If the lock has been created,
    the current thread must have acquired it.  (This function is available even
    when thread support is disabled at compile time.)"""
    raise NotImplementedError

@cpython_api([{PyThreadState*}], lltype.Void)
def PyEval_RestoreThread(space, tstate):
    """Acquire the global interpreter lock (if it has been created and thread
    support is enabled) and set the thread state to tstate, which must not be
    NULL.  If the lock has been created, the current thread must not have
    acquired it, otherwise deadlock ensues.  (This function is available even
    when thread support is disabled at compile time.)"""
    raise NotImplementedError

@cpython_api([], lltype.Void)
def PyEval_ReInitThreads(space, ):
    """This function is called from PyOS_AfterFork() to ensure that newly
    created child processes don't hold locks referring to threads which
    are not running in the child process."""
    raise NotImplementedError

@cpython_api([], {PyInterpreterState*})
def PyInterpreterState_New(space, ):
    """Create a new interpreter state object.  The global interpreter lock need not
    be held, but may be held if it is necessary to serialize calls to this
    function."""
    raise NotImplementedError

@cpython_api([{PyInterpreterState*}], lltype.Void)
def PyInterpreterState_Clear(space, interp):
    """Reset all information in an interpreter state object.  The global interpreter
    lock must be held."""
    raise NotImplementedError

@cpython_api([{PyInterpreterState*}], lltype.Void)
def PyInterpreterState_Delete(space, interp):
    """Destroy an interpreter state object.  The global interpreter lock need not be
    held.  The interpreter state must have been reset with a previous call to
    PyInterpreterState_Clear()."""
    raise NotImplementedError

@cpython_api([{PyInterpreterState*}], {PyThreadState*})
def PyThreadState_New(space, interp):
    """Create a new thread state object belonging to the given interpreter object.
    The global interpreter lock need not be held, but may be held if it is
    necessary to serialize calls to this function."""
    raise NotImplementedError

@cpython_api([{PyThreadState*}], lltype.Void)
def PyThreadState_Clear(space, tstate):
    """Reset all information in a thread state object.  The global interpreter lock
    must be held."""
    raise NotImplementedError

@cpython_api([{PyThreadState*}], lltype.Void)
def PyThreadState_Delete(space, tstate):
    """Destroy a thread state object.  The global interpreter lock need not be held.
    The thread state must have been reset with a previous call to
    PyThreadState_Clear()."""
    raise NotImplementedError

@cpython_api([], {PyThreadState*})
def PyThreadState_Get(space, ):
    """Return the current thread state.  The global interpreter lock must be held.
    When the current thread state is NULL, this issues a fatal error (so that
    the caller needn't check for NULL)."""
    raise NotImplementedError

@cpython_api([{PyThreadState*}], {PyThreadState*})
def PyThreadState_Swap(space, tstate):
    """Swap the current thread state with the thread state given by the argument
    tstate, which may be NULL.  The global interpreter lock must be held."""
    raise NotImplementedError

@cpython_api([], PyObject, borrowed=True)
def PyThreadState_GetDict(space, ):
    """Return a dictionary in which extensions can store thread-specific state
    information.  Each extension should use a unique key to use to store state in
    the dictionary.  It is okay to call this function when no current thread state
    is available. If this function returns NULL, no exception has been raised and
    the caller should assume no current thread state is available.
    
    Previously this could only be called when a current thread is active, and NULL
    meant that an exception was raised."""
    raise NotImplementedError

@cpython_api([lltype.Signed, PyObject], rffi.INT_real)
def PyThreadState_SetAsyncExc(space, id, exc):
    """Asynchronously raise an exception in a thread. The id argument is the thread
    id of the target thread; exc is the exception object to be raised. This
    function does not steal any references to exc. To prevent naive misuse, you
    must write your own C extension to call this.  Must be called with the GIL held.
    Returns the number of thread states modified; this is normally one, but will be
    zero if the thread id isn't found.  If exc is NULL, the pending
    exception (if any) for the thread is cleared. This raises no exceptions.
    """
    raise NotImplementedError

@cpython_api([], {PyGILState_STATE})
def PyGILState_Ensure(space, ):
    """Ensure that the current thread is ready to call the Python C API regardless
    of the current state of Python, or of the global interpreter lock. This may
    be called as many times as desired by a thread as long as each call is
    matched with a call to PyGILState_Release(). In general, other
    thread-related APIs may be used between PyGILState_Ensure() and
    PyGILState_Release() calls as long as the thread state is restored to
    its previous state before the Release().  For example, normal usage of the
    Py_BEGIN_ALLOW_THREADS and Py_END_ALLOW_THREADS macros is
    acceptable.
    
    The return value is an opaque "handle" to the thread state when
    PyGILState_Ensure() was called, and must be passed to
    PyGILState_Release() to ensure Python is left in the same state. Even
    though recursive calls are allowed, these handles cannot be shared - each
    unique call to PyGILState_Ensure() must save the handle for its call
    to PyGILState_Release().
    
    When the function returns, the current thread will hold the GIL. Failure is a
    fatal error.
    """
    raise NotImplementedError

@cpython_api([{PyGILState_STATE}], lltype.Void)
def PyGILState_Release(space, ):
    """Release any resources previously acquired.  After this call, Python's state will
    be the same as it was prior to the corresponding PyGILState_Ensure() call
    (but generally this state will be unknown to the caller, hence the use of the
    GILState API.)
    
    Every call to PyGILState_Ensure() must be matched by a call to
    PyGILState_Release() on the same thread.
    """
    raise NotImplementedError

@cpython_api([{int (*func)(void*}, {void*}], lltype.Void)
def Py_AddPendingCall(space, , arg)):
    """
    
    
    
    Post a notification to the Python main thread.  If successful, func will be
    called with the argument arg at the earliest convenience.  func will be
    called having the global interpreter lock held and can thus use the full
    Python API and can take any action such as setting object attributes to
    signal IO completion.  It must return 0 on success, or -1 signalling an
    exception.  The notification function won't be interrupted to perform another
    asynchronous notification recursively, but it can still be interrupted to
    switch threads if the global interpreter lock is released, for example, if it
    calls back into Python code.
    
    This function returns 0 on success in which case the notification has been
    scheduled.  Otherwise, for example if the notification buffer is full, it
    returns -1 without setting any exception.
    
    This function can be called on any thread, be it a Python thread or some
    other system thread.  If it is a Python thread, it doesn't matter if it holds
    the global interpreter lock or not.
    """
    raise NotImplementedError

@cpython_api([{Py_tracefunc}, PyObject], lltype.Void)
def PyEval_SetProfile(space, func, obj):
    """Set the profiler function to func.  The obj parameter is passed to the
    function as its first parameter, and may be any Python object, or NULL.  If
    the profile function needs to maintain state, using a different value for obj
    for each thread provides a convenient and thread-safe place to store it.  The
    profile function is called for all monitored events except the line-number
    events."""
    raise NotImplementedError

@cpython_api([{Py_tracefunc}, PyObject], lltype.Void)
def PyEval_SetTrace(space, func, obj):
    """Set the tracing function to func.  This is similar to
    PyEval_SetProfile(), except the tracing function does receive line-number
    events."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyEval_GetCallStats(space, self):
    """Return a tuple of function call counts.  There are constants defined for the
    positions within the tuple:
    
    
    
    
    
    Name
    
    Value
    
    PCALL_ALL
    
    0
    
    PCALL_FUNCTION
    
    1
    
    PCALL_FAST_FUNCTION
    
    2
    
    PCALL_FASTER_FUNCTION
    
    3
    
    PCALL_METHOD
    
    4
    
    PCALL_BOUND_METHOD
    
    5
    
    PCALL_CFUNCTION
    
    6
    
    PCALL_TYPE
    
    7
    
    PCALL_GENERATOR
    
    8
    
    PCALL_OTHER
    
    9
    
    PCALL_POP
    
    10
    
    PCALL_FAST_FUNCTION means no argument tuple needs to be created.
    PCALL_FASTER_FUNCTION means that the fast-path frame setup code is used.
    
    If there is a method call where the call can be optimized by changing
    the argument tuple and calling the function directly, it gets recorded
    twice.
    
    This function is only present if Python is compiled with CALL_PROFILE
    defined."""
    raise NotImplementedError

@cpython_api([], {PyInterpreterState*})
def PyInterpreterState_Head(space, ):
    """Return the interpreter state object at the head of the list of all such objects.
    """
    raise NotImplementedError

@cpython_api([{PyInterpreterState*}], {PyInterpreterState*})
def PyInterpreterState_Next(space, interp):
    """Return the next interpreter state object after interp from the list of all
    such objects.
    """
    raise NotImplementedError

@cpython_api([{PyInterpreterState*}], {PyThreadState* })
def PyInterpreterState_ThreadHead(space, interp):
    """Return the a pointer to the first PyThreadState object in the list of
    threads associated with the interpreter interp.
    """
    raise NotImplementedError

@cpython_api([{PyThreadState*}], {PyThreadState*})
def PyThreadState_Next(space, tstate):
    """Return the next thread state object after tstate from the list of all such
    objects belonging to the same PyInterpreterState object.
    """
    raise NotImplementedError

@cpython_api([rffi.CCHARP, {char**}, rffi.INT_real], PyObject)
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
    raise NotImplementedError

@cpython_api([Py_ssize_t], PyObject)
def PyInt_FromSsize_t(space, ival):
    """Create a new integer object with a value of ival. If the value is larger
    than LONG_MAX or smaller than LONG_MIN, a long integer object is
    returned.
    """
    raise NotImplementedError

@cpython_api([{size_t}], PyObject)
def PyInt_FromSize_t(space, ival):
    """Create a new integer object with a value of ival. If the value exceeds
    LONG_MAX, a long integer object is returned.
    """
    raise NotImplementedError

@cpython_api([PyObject], lltype.Signed)
def PyInt_AS_LONG(space, io):
    """Return the value of the object io.  No error checking is performed."""
    raise NotImplementedError

@cpython_api([PyObject], {unsigned long})
def PyInt_AsUnsignedLongMask(space, io):
    """Will first attempt to cast the object to a PyIntObject or
    PyLongObject, if it is not already one, and then return its value as
    unsigned long.  This function does not check for overflow.
    """
    raise NotImplementedError

@cpython_api([PyObject], {unsigned PY_LONG_LONG})
def PyInt_AsUnsignedLongLongMask(space, io):
    """Will first attempt to cast the object to a PyIntObject or
    PyLongObject, if it is not already one, and then return its value as
    unsigned long long, without checking for overflow.
    """
    raise NotImplementedError

@cpython_api([PyObject], Py_ssize_t)
def PyInt_AsSsize_t(space, io):
    """Will first attempt to cast the object to a PyIntObject or
    PyLongObject, if it is not already one, and then return its value as
    Py_ssize_t.
    """
    raise NotImplementedError

@cpython_api([], lltype.Signed)
def PyInt_GetMax(space, ):
    """
    
    
    
    Return the system's idea of the largest integer it can handle
    (LONG_MAX, as defined in the system header files)."""
    raise NotImplementedError

@cpython_api([], rffi.INT_real)
def PyInt_ClearFreeList(space, ):
    """Clear the integer free list. Return the number of items that could not
    be freed.
    """
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PyIter_Check(space, o):
    """Return true if the object o supports the iterator protocol."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyIter_Next(space, o):
    """Return the next value from the iteration o.  If the object is an iterator,
    this retrieves the next value from the iteration, and returns NULL with no
    exception set if there are no remaining items.  If the object is not an
    iterator, TypeError is raised, or if there is an error in retrieving the
    item, returns NULL and passes along the exception."""
    raise NotImplementedError

@cpython_api([{op}], rffi.INT_real)
def PySeqIter_Check(space, ):
    """Return true if the type of op is PySeqIter_Type.
    """
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PySeqIter_New(space, seq):
    """Return an iterator that works with a general sequence object, seq.  The
    iteration ends when the sequence raises IndexError for the subscripting
    operation.
    """
    raise NotImplementedError

@cpython_api([{op}], rffi.INT_real)
def PyCallIter_Check(space, ):
    """Return true if the type of op is PyCallIter_Type.
    """
    raise NotImplementedError

@cpython_api([PyObject, PyObject], PyObject)
def PyCallIter_New(space, callable, sentinel):
    """Return a new iterator.  The first parameter, callable, can be any Python
    callable object that can be called with no parameters; each call to it should
    return the next item in the iteration.  When callable returns a value equal to
    sentinel, the iteration will be terminated.
    """
    raise NotImplementedError

@cpython_api([PyObject], Py_ssize_t)
def PyList_Size(space, list):
    """
    
    
    
    Return the length of the list object in list; this is equivalent to
    len(list) on a list object.
    
    This function returned an int. This might require changes in
    your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject, Py_ssize_t], PyObject, borrowed=True)
def PyList_GetItem(space, list, index):
    """Return the object at position pos in the list pointed to by p.  The
    position must be positive, indexing from the end of the list is not
    supported.  If pos is out of bounds, return NULL and set an
    IndexError exception.
    
    This function used an int for index. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject, Py_ssize_t], PyObject, borrowed=True)
def PyList_GET_ITEM(space, list, i):
    """Macro form of PyList_GetItem() without error checking.
    
    This macro used an int for i. This might require changes in
    your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject, Py_ssize_t, PyObject], lltype.Void)
def PyList_SET_ITEM(space, list, i, o):
    """Macro form of PyList_SetItem() without error checking. This is
    normally only used to fill in new lists where there is no previous content.
    
    This macro "steals" a reference to item, and, unlike
    PyList_SetItem(), does not discard a reference to any item that
    it being replaced; any reference in list at position i will be
    leaked.
    
    This macro used an int for i. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject, Py_ssize_t, PyObject], rffi.INT_real)
def PyList_Insert(space, list, index, item):
    """Insert the item item into list list in front of index index.  Return
    0 if successful; return -1 and set an exception if unsuccessful.
    Analogous to list.insert(index, item).
    
    This function used an int for index. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject, Py_ssize_t, Py_ssize_t], PyObject)
def PyList_GetSlice(space, list, low, high):
    """Return a list of the objects in list containing the objects between low
    and high.  Return NULL and set an exception if unsuccessful.  Analogous
    to list[low:high].  Negative indices, as when slicing from Python, are not
    supported.
    
    This function used an int for low and high. This might
    require changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject, Py_ssize_t, Py_ssize_t, PyObject], rffi.INT_real)
def PyList_SetSlice(space, list, low, high, itemlist):
    """Set the slice of list between low and high to the contents of
    itemlist.  Analogous to list[low:high] = itemlist. The itemlist may
    be NULL, indicating the assignment of an empty list (slice deletion).
    Return 0 on success, -1 on failure.  Negative indices, as when
    slicing from Python, are not supported.
    
    This function used an int for low and high. This might
    require changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PyList_Sort(space, list):
    """Sort the items of list in place.  Return 0 on success, -1 on
    failure.  This is equivalent to list.sort()."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PyList_Reverse(space, list):
    """Reverse the items of list in place.  Return 0 on success, -1 on
    failure.  This is the equivalent of list.reverse()."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyList_AsTuple(space, list):
    """
    
    
    
    Return a new tuple object containing the contents of list; equivalent to
    tuple(list)."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PyLong_Check(space, p):
    """Return true if its argument is a PyLongObject or a subtype of
    PyLongObject.
    
    Allowed subtypes to be accepted."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PyLong_CheckExact(space, p):
    """Return true if its argument is a PyLongObject, but not a subtype of
    PyLongObject.
    """
    raise NotImplementedError

@cpython_api([{unsigned long}], PyObject)
def PyLong_FromUnsignedLong(space, v):
    """Return a new PyLongObject object from a C unsigned long, or
    NULL on failure."""
    raise NotImplementedError

@cpython_api([Py_ssize_t], PyObject)
def PyLong_FromSsize_t(space, v):
    """Return a new PyLongObject object from a C Py_ssize_t, or
    NULL on failure.
    """
    raise NotImplementedError

@cpython_api([{size_t}], PyObject)
def PyLong_FromSize_t(space, v):
    """Return a new PyLongObject object from a C size_t, or
    NULL on failure.
    """
    raise NotImplementedError

@cpython_api([{PY_LONG_LONG}], PyObject)
def PyLong_FromLongLong(space, v):
    """Return a new PyLongObject object from a C long long, or NULL
    on failure."""
    raise NotImplementedError

@cpython_api([{unsigned PY_LONG_LONG}], PyObject)
def PyLong_FromUnsignedLongLong(space, v):
    """Return a new PyLongObject object from a C unsigned long long,
    or NULL on failure."""
    raise NotImplementedError

@cpython_api([{double}], PyObject)
def PyLong_FromDouble(space, v):
    """Return a new PyLongObject object from the integer part of v, or
    NULL on failure."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, {char**}, rffi.INT_real], PyObject)
def PyLong_FromString(space, str, pend, base):
    """Return a new PyLongObject based on the string value in str, which is
    interpreted according to the radix in base.  If pend is non-NULL,
    *pend will point to the first character in str which follows the
    representation of the number.  If base is 0, the radix will be determined
    based on the leading characters of str: if str starts with '0x' or
    '0X', radix 16 will be used; if str starts with '0', radix 8 will be
    used; otherwise radix 10 will be used.  If base is not 0, it must be
    between 2 and 36, inclusive.  Leading spaces are ignored.  If there are
    no digits, ValueError will be raised."""
    raise NotImplementedError

@cpython_api([{Py_UNICODE*}, Py_ssize_t, rffi.INT_real], PyObject)
def PyLong_FromUnicode(space, u, length, base):
    """Convert a sequence of Unicode digits to a Python long integer value.  The first
    parameter, u, points to the first character of the Unicode string, length
    gives the number of characters, and base is the radix for the conversion.  The
    radix must be in the range [2, 36]; if it is out of range, ValueError
    will be raised.
    
    
    
    This function used an int for length. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([{void*}], PyObject)
def PyLong_FromVoidPtr(space, p):
    """Create a Python integer or long integer from the pointer p. The pointer value
    can be retrieved from the resulting value using PyLong_AsVoidPtr().
    
    
    
    If the integer is larger than LONG_MAX, a positive long integer is returned."""
    raise NotImplementedError

@cpython_api([PyObject], lltype.Signed)
def PyLong_AsLong(space, pylong):
    """
    
    
    
    Return a C long representation of the contents of pylong.  If
    pylong is greater than LONG_MAX, an OverflowError is raised
    and -1 will be returned."""
    raise NotImplementedError

@cpython_api([PyObject, {int*}], lltype.Signed)
def PyLong_AsLongAndOverflow(space, pylong, overflow):
    """Return a C long representation of the contents of
    pylong.  If pylong is greater than LONG_MAX or less
    than LONG_MIN, set *overflow to 1 or -1,
    respectively, and return -1; otherwise, set *overflow to
    0.  If any other exception occurs (for example a TypeError or
    MemoryError), then -1 will be returned and *overflow will
    be 0.
    """
    raise NotImplementedError

@cpython_api([PyObject, {int*}], {PY_LONG_LONG})
def PyLong_AsLongLongAndOverflow(space, pylong, overflow):
    """Return a C long long representation of the contents of
    pylong.  If pylong is greater than PY_LLONG_MAX or less
    than PY_LLONG_MIN, set *overflow to 1 or -1,
    respectively, and return -1; otherwise, set *overflow to
    0.  If any other exception occurs (for example a TypeError or
    MemoryError), then -1 will be returned and *overflow will
    be 0.
    """
    raise NotImplementedError

@cpython_api([PyObject], Py_ssize_t)
def PyLong_AsSsize_t(space, pylong):
    """
    
    
    
    Return a C Py_ssize_t representation of the contents of pylong.  If
    pylong is greater than PY_SSIZE_T_MAX, an OverflowError is raised
    and -1 will be returned.
    """
    raise NotImplementedError

@cpython_api([PyObject], {unsigned long})
def PyLong_AsUnsignedLong(space, pylong):
    """
    
    
    
    Return a C unsigned long representation of the contents of pylong.
    If pylong is greater than ULONG_MAX, an OverflowError is
    raised."""
    raise NotImplementedError

@cpython_api([PyObject], {PY_LONG_LONG})
def PyLong_AsLongLong(space, pylong):
    """
    
    
    
    Return a C long long from a Python long integer.  If
    pylong cannot be represented as a long long, an
    OverflowError is raised and -1 is returned.
    """
    raise NotImplementedError

@cpython_api([PyObject], {unsigned PY_LONG_LONG})
def PyLong_AsUnsignedLongLong(space, pylong):
    """
    
    
    
    Return a C unsigned long long from a Python long integer. If
    pylong cannot be represented as an unsigned long long, an
    OverflowError is raised and (unsigned long long)-1 is
    returned.
    
    
    
    A negative pylong now raises OverflowError, not
    TypeError."""
    raise NotImplementedError

@cpython_api([PyObject], {unsigned long})
def PyLong_AsUnsignedLongMask(space, io):
    """Return a C unsigned long from a Python long integer, without checking
    for overflow.
    """
    raise NotImplementedError

@cpython_api([PyObject], {unsigned PY_LONG_LONG})
def PyLong_AsUnsignedLongLongMask(space, io):
    """Return a C unsigned long long from a Python long integer, without
    checking for overflow.
    """
    raise NotImplementedError

@cpython_api([PyObject], {double})
def PyLong_AsDouble(space, pylong):
    """Return a C double representation of the contents of pylong.  If
    pylong cannot be approximately represented as a double, an
    OverflowError exception is raised and -1.0 will be returned."""
    raise NotImplementedError

@cpython_api([PyObject], {void*})
def PyLong_AsVoidPtr(space, pylong):
    """Convert a Python integer or long integer pylong to a C void pointer.
    If pylong cannot be converted, an OverflowError will be raised.  This
    is only assured to produce a usable void pointer for values created
    with PyLong_FromVoidPtr().
    
    
    
    For values outside 0..LONG_MAX, both signed and unsigned integers are accepted."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PyMapping_Check(space, o):
    """Return 1 if the object provides mapping protocol, and 0 otherwise.  This
    function always succeeds."""
    raise NotImplementedError

@cpython_api([PyObject], Py_ssize_t)
def PyMapping_Size(space, o):
    """
    
    
    
    Returns the number of keys in object o on success, and -1 on failure.  For
    objects that do not provide mapping protocol, this is equivalent to the Python
    expression len(o).
    
    These functions returned an int type. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject, rffi.CCHARP], rffi.INT_real)
def PyMapping_DelItemString(space, o, key):
    """Remove the mapping for object key from the object o. Return -1 on
    failure.  This is equivalent to the Python statement del o[key]."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], rffi.INT_real)
def PyMapping_DelItem(space, o, key):
    """Remove the mapping for object key from the object o. Return -1 on
    failure.  This is equivalent to the Python statement del o[key]."""
    raise NotImplementedError

@cpython_api([PyObject, rffi.CCHARP], rffi.INT_real)
def PyMapping_HasKeyString(space, o, key):
    """On success, return 1 if the mapping object has the key key and 0
    otherwise.  This is equivalent to o[key], returning True on success
    and False on an exception.  This function always succeeds."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], rffi.INT_real)
def PyMapping_HasKey(space, o, key):
    """Return 1 if the mapping object has the key key and 0 otherwise.
    This is equivalent to o[key], returning True on success and False
    on an exception.  This function always succeeds."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyMapping_Values(space, o):
    """On success, return a list of the values in object o.  On failure, return
    NULL. This is equivalent to the Python expression o.values()."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyMapping_Items(space, o):
    """On success, return a list of the items in object o, where each item is a tuple
    containing a key-value pair.  On failure, return NULL. This is equivalent to
    the Python expression o.items()."""
    raise NotImplementedError

@cpython_api([PyObject, rffi.CCHARP], PyObject)
def PyMapping_GetItemString(space, o, key):
    """Return element of o corresponding to the object key or NULL on failure.
    This is the equivalent of the Python expression o[key]."""
    raise NotImplementedError

@cpython_api([PyObject, rffi.CCHARP, PyObject], rffi.INT_real)
def PyMapping_SetItemString(space, o, key, v):
    """Map the object key to the value v in object o. Returns -1 on failure.
    This is the equivalent of the Python statement o[key] = v."""
    raise NotImplementedError

@cpython_api([lltype.Signed, {FILE*}, rffi.INT_real], lltype.Void)
def PyMarshal_WriteLongToFile(space, value, file, version):
    """Marshal a long integer, value, to file.  This will only write
    the least-significant 32 bits of value; regardless of the size of the
    native long type.
    
    version indicates the file format."""
    raise NotImplementedError

@cpython_api([PyObject, {FILE*}, rffi.INT_real], lltype.Void)
def PyMarshal_WriteObjectToFile(space, value, file, version):
    """Marshal a Python object, value, to file.
    
    version indicates the file format."""
    raise NotImplementedError

@cpython_api([PyObject, rffi.INT_real], PyObject)
def PyMarshal_WriteObjectToString(space, value, version):
    """Return a string object containing the marshalled representation of value.
    
    version indicates the file format."""
    raise NotImplementedError

@cpython_api([{FILE*}], lltype.Signed)
def PyMarshal_ReadLongFromFile(space, file):
    """Return a C long from the data stream in a FILE* opened
    for reading.  Only a 32-bit value can be read in using this function,
    regardless of the native size of long."""
    raise NotImplementedError

@cpython_api([{FILE*}], rffi.INT_real)
def PyMarshal_ReadShortFromFile(space, file):
    """Return a C short from the data stream in a FILE* opened
    for reading.  Only a 16-bit value can be read in using this function,
    regardless of the native size of short."""
    raise NotImplementedError

@cpython_api([{FILE*}], PyObject)
def PyMarshal_ReadObjectFromFile(space, file):
    """Return a Python object from the data stream in a FILE* opened for
    reading.  On error, sets the appropriate exception (EOFError or
    TypeError) and returns NULL."""
    raise NotImplementedError

@cpython_api([{FILE*}], PyObject)
def PyMarshal_ReadLastObjectFromFile(space, file):
    """Return a Python object from the data stream in a FILE* opened for
    reading.  Unlike PyMarshal_ReadObjectFromFile(), this function
    assumes that no further objects will be read from the file, allowing it to
    aggressively load file data into memory so that the de-serialization can
    operate from data in memory rather than reading a byte at a time from the
    file.  Only use these variant if you are certain that you won't be reading
    anything else from the file.  On error, sets the appropriate exception
    (EOFError or TypeError) and returns NULL."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, Py_ssize_t], PyObject)
def PyMarshal_ReadObjectFromString(space, string, len):
    """Return a Python object from the data stream in a character buffer
    containing len bytes pointed to by string.  On error, sets the
    appropriate exception (EOFError or TypeError) and returns
    NULL.
    
    This function used an int type for len. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([{size_t}], {void*})
def PyMem_Malloc(space, n):
    """Allocates n bytes and returns a pointer of type void* to the
    allocated memory, or NULL if the request fails. Requesting zero bytes returns
    a distinct non-NULL pointer if possible, as if PyMem_Malloc(1)() had
    been called instead. The memory will not have been initialized in any way."""
    raise NotImplementedError

@cpython_api([{void*}, {size_t}], {void*})
def PyMem_Realloc(space, p, n):
    """Resizes the memory block pointed to by p to n bytes. The contents will be
    unchanged to the minimum of the old and the new sizes. If p is NULL, the
    call is equivalent to PyMem_Malloc(n)(); else if n is equal to zero,
    the memory block is resized but is not freed, and the returned pointer is
    non-NULL.  Unless p is NULL, it must have been returned by a previous call
    to PyMem_Malloc() or PyMem_Realloc(). If the request fails,
    PyMem_Realloc() returns NULL and p remains a valid pointer to the
    previous memory area."""
    raise NotImplementedError

@cpython_api([{void*}], lltype.Void)
def PyMem_Free(space, p):
    """Frees the memory block pointed to by p, which must have been returned by a
    previous call to PyMem_Malloc() or PyMem_Realloc().  Otherwise, or
    if PyMem_Free(p)() has been called before, undefined behavior occurs. If
    p is NULL, no operation is performed."""
    raise NotImplementedError

@cpython_api([{TYPE}, {size_t}], {TYPE*})
def PyMem_New(space, , n):
    """Same as PyMem_Malloc(), but allocates (n * sizeof(TYPE)) bytes of
    memory.  Returns a pointer cast to TYPE*.  The memory will not have
    been initialized in any way."""
    raise NotImplementedError

@cpython_api([{void*}, {TYPE}, {size_t}], {TYPE*})
def PyMem_Resize(space, p, , n):
    """Same as PyMem_Realloc(), but the memory block is resized to (n *
    sizeof(TYPE)) bytes.  Returns a pointer cast to TYPE*. On return,
    p will be a pointer to the new memory area, or NULL in the event of
    failure.  This is a C preprocessor macro; p is always reassigned.  Save
    the original value of p to avoid losing memory when handling errors."""
    raise NotImplementedError

@cpython_api([{void*}], lltype.Void)
def PyMem_Del(space, p):
    """Same as PyMem_Free()."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PyMethod_Check(space, o):
    """Return true if o is a method object (has type PyMethod_Type).  The
    parameter must not be NULL."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject, PyObject], PyObject)
def PyMethod_New(space, func, self, class):
    """Return a new method object, with func being any callable object; this is the
    function that will be called when the method is called.  If this method should
    be bound to an instance, self should be the instance and class should be the
    class of self, otherwise self should be NULL and class should be the
    class which provides the unbound method.."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject, borrowed=True)
def PyMethod_Class(space, meth):
    """Return the class object from which the method meth was created; if this was
    created from an instance, it will be the class of the instance."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject, borrowed=True)
def PyMethod_GET_CLASS(space, meth):
    """Macro version of PyMethod_Class() which avoids error checking."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject, borrowed=True)
def PyMethod_Function(space, meth):
    """Return the function object associated with the method meth."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject, borrowed=True)
def PyMethod_GET_FUNCTION(space, meth):
    """Macro version of PyMethod_Function() which avoids error checking."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject, borrowed=True)
def PyMethod_Self(space, meth):
    """Return the instance associated with the method meth if it is bound, otherwise
    return NULL."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject, borrowed=True)
def PyMethod_GET_SELF(space, meth):
    """Macro version of PyMethod_Self() which avoids error checking."""
    raise NotImplementedError

@cpython_api([], rffi.INT_real)
def PyMethod_ClearFreeList(space, ):
    """Clear the free list. Return the total number of freed items.
    """
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PyModule_CheckExact(space, p):
    """Return true if p is a module object, but not a subtype of
    PyModule_Type.
    """
    raise NotImplementedError

@cpython_api([rffi.CCHARP], PyObject)
def PyModule_New(space, name):
    """
    
    
    
    Return a new module object with the __name__ attribute set to name.
    Only the module's __doc__ and __name__ attributes are filled in;
    the caller is responsible for providing a __file__ attribute."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.CCHARP)
def PyModule_GetFilename(space, module):
    """
    
    
    
    Return the name of the file from which module was loaded using module's
    __file__ attribute.  If this is not defined, or if it is not a string,
    raise SystemError and return NULL."""
    raise NotImplementedError

@cpython_api([PyObject, rffi.CCHARP, PyObject], rffi.INT_real)
def PyModule_AddObject(space, module, name, value):
    """Add an object to module as name.  This is a convenience function which can
    be used from the module's initialization function.  This steals a reference to
    value.  Return -1 on error, 0 on success.
    """
    raise NotImplementedError

@cpython_api([PyObject, rffi.CCHARP, lltype.Signed], rffi.INT_real)
def PyModule_AddIntConstant(space, module, name, value):
    """Add an integer constant to module as name.  This convenience function can be
    used from the module's initialization function. Return -1 on error, 0 on
    success.
    """
    raise NotImplementedError

@cpython_api([PyObject, rffi.CCHARP, rffi.CCHARP], rffi.INT_real)
def PyModule_AddStringConstant(space, module, name, value):
    """Add a string constant to module as name.  This convenience function can be
    used from the module's initialization function.  The string value must be
    null-terminated.  Return -1 on error, 0 on success.
    """
    raise NotImplementedError

@cpython_api([PyObject, {macro}], rffi.INT_real)
def PyModule_AddIntMacro(space, module, ):
    """Add an int constant to module. The name and the value are taken from
    macro. For example PyModule_AddConstant(module, AF_INET) adds the int
    constant AF_INET with the value of AF_INET to module.
    Return -1 on error, 0 on success.
    """
    raise NotImplementedError

@cpython_api([PyObject, {macro}], rffi.INT_real)
def PyModule_AddStringMacro(space, module, ):
    """Add a string constant to module.
    """
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PyNumber_Check(space, o):
    """Returns 1 if the object o provides numeric protocols, and false otherwise.
    This function always succeeds."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], PyObject)
def PyNumber_Add(space, o1, o2):
    """Returns the result of adding o1 and o2, or NULL on failure.  This is the
    equivalent of the Python expression o1 + o2."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], PyObject)
def PyNumber_Subtract(space, o1, o2):
    """Returns the result of subtracting o2 from o1, or NULL on failure.  This is
    the equivalent of the Python expression o1 - o2."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], PyObject)
def PyNumber_Multiply(space, o1, o2):
    """Returns the result of multiplying o1 and o2, or NULL on failure.  This is
    the equivalent of the Python expression o1 * o2."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], PyObject)
def PyNumber_Divide(space, o1, o2):
    """Returns the result of dividing o1 by o2, or NULL on failure.  This is the
    equivalent of the Python expression o1 / o2."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], PyObject)
def PyNumber_FloorDivide(space, o1, o2):
    """Return the floor of o1 divided by o2, or NULL on failure.  This is
    equivalent to the "classic" division of integers.
    """
    raise NotImplementedError

@cpython_api([PyObject, PyObject], PyObject)
def PyNumber_TrueDivide(space, o1, o2):
    """Return a reasonable approximation for the mathematical value of o1 divided by
    o2, or NULL on failure.  The return value is "approximate" because binary
    floating point numbers are approximate; it is not possible to represent all real
    numbers in base two.  This function can return a floating point value when
    passed two integers.
    """
    raise NotImplementedError

@cpython_api([PyObject, PyObject], PyObject)
def PyNumber_Remainder(space, o1, o2):
    """Returns the remainder of dividing o1 by o2, or NULL on failure.  This is
    the equivalent of the Python expression o1 % o2."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], PyObject)
def PyNumber_Divmod(space, o1, o2):
    """
    
    
    
    See the built-in function divmod(). Returns NULL on failure.  This is
    the equivalent of the Python expression divmod(o1, o2)."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject, PyObject], PyObject)
def PyNumber_Power(space, o1, o2, o3):
    """
    
    
    
    See the built-in function pow(). Returns NULL on failure.  This is the
    equivalent of the Python expression pow(o1, o2, o3), where o3 is optional.
    If o3 is to be ignored, pass Py_None in its place (passing NULL for
    o3 would cause an illegal memory access)."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyNumber_Negative(space, o):
    """Returns the negation of o on success, or NULL on failure. This is the
    equivalent of the Python expression -o."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyNumber_Positive(space, o):
    """Returns o on success, or NULL on failure.  This is the equivalent of the
    Python expression +o."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyNumber_Absolute(space, o):
    """
    
    
    
    Returns the absolute value of o, or NULL on failure.  This is the equivalent
    of the Python expression abs(o)."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyNumber_Invert(space, o):
    """Returns the bitwise negation of o on success, or NULL on failure.  This is
    the equivalent of the Python expression ~o."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], PyObject)
def PyNumber_Lshift(space, o1, o2):
    """Returns the result of left shifting o1 by o2 on success, or NULL on
    failure.  This is the equivalent of the Python expression o1 << o2."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], PyObject)
def PyNumber_Rshift(space, o1, o2):
    """Returns the result of right shifting o1 by o2 on success, or NULL on
    failure.  This is the equivalent of the Python expression o1 >> o2."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], PyObject)
def PyNumber_And(space, o1, o2):
    """Returns the "bitwise and" of o1 and o2 on success and NULL on failure.
    This is the equivalent of the Python expression o1 & o2."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], PyObject)
def PyNumber_Xor(space, o1, o2):
    """Returns the "bitwise exclusive or" of o1 by o2 on success, or NULL on
    failure.  This is the equivalent of the Python expression o1 ^ o2."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], PyObject)
def PyNumber_Or(space, o1, o2):
    """Returns the "bitwise or" of o1 and o2 on success, or NULL on failure.
    This is the equivalent of the Python expression o1 | o2."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], PyObject)
def PyNumber_InPlaceAdd(space, o1, o2):
    """Returns the result of adding o1 and o2, or NULL on failure.  The operation
    is done in-place when o1 supports it.  This is the equivalent of the Python
    statement o1 += o2."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], PyObject)
def PyNumber_InPlaceSubtract(space, o1, o2):
    """Returns the result of subtracting o2 from o1, or NULL on failure.  The
    operation is done in-place when o1 supports it.  This is the equivalent of
    the Python statement o1 -= o2."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], PyObject)
def PyNumber_InPlaceMultiply(space, o1, o2):
    """Returns the result of multiplying o1 and o2, or NULL on failure.  The
    operation is done in-place when o1 supports it.  This is the equivalent of
    the Python statement o1 *= o2."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], PyObject)
def PyNumber_InPlaceDivide(space, o1, o2):
    """Returns the result of dividing o1 by o2, or NULL on failure.  The
    operation is done in-place when o1 supports it. This is the equivalent of
    the Python statement o1 /= o2."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], PyObject)
def PyNumber_InPlaceFloorDivide(space, o1, o2):
    """Returns the mathematical floor of dividing o1 by o2, or NULL on failure.
    The operation is done in-place when o1 supports it.  This is the equivalent
    of the Python statement o1 //= o2.
    """
    raise NotImplementedError

@cpython_api([PyObject, PyObject], PyObject)
def PyNumber_InPlaceTrueDivide(space, o1, o2):
    """Return a reasonable approximation for the mathematical value of o1 divided by
    o2, or NULL on failure.  The return value is "approximate" because binary
    floating point numbers are approximate; it is not possible to represent all real
    numbers in base two.  This function can return a floating point value when
    passed two integers.  The operation is done in-place when o1 supports it.
    """
    raise NotImplementedError

@cpython_api([PyObject, PyObject], PyObject)
def PyNumber_InPlaceRemainder(space, o1, o2):
    """Returns the remainder of dividing o1 by o2, or NULL on failure.  The
    operation is done in-place when o1 supports it.  This is the equivalent of
    the Python statement o1 %= o2."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject, PyObject], PyObject)
def PyNumber_InPlacePower(space, o1, o2, o3):
    """
    
    
    
    See the built-in function pow(). Returns NULL on failure.  The operation
    is done in-place when o1 supports it.  This is the equivalent of the Python
    statement o1 **= o2 when o3 is Py_None, or an in-place variant of
    pow(o1, o2, o3) otherwise. If o3 is to be ignored, pass Py_None
    in its place (passing NULL for o3 would cause an illegal memory access)."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], PyObject)
def PyNumber_InPlaceLshift(space, o1, o2):
    """Returns the result of left shifting o1 by o2 on success, or NULL on
    failure.  The operation is done in-place when o1 supports it.  This is the
    equivalent of the Python statement o1 <<= o2."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], PyObject)
def PyNumber_InPlaceRshift(space, o1, o2):
    """Returns the result of right shifting o1 by o2 on success, or NULL on
    failure.  The operation is done in-place when o1 supports it.  This is the
    equivalent of the Python statement o1 >>= o2."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], PyObject)
def PyNumber_InPlaceAnd(space, o1, o2):
    """Returns the "bitwise and" of o1 and o2 on success and NULL on failure. The
    operation is done in-place when o1 supports it.  This is the equivalent of
    the Python statement o1 &= o2."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], PyObject)
def PyNumber_InPlaceXor(space, o1, o2):
    """Returns the "bitwise exclusive or" of o1 by o2 on success, or NULL on
    failure.  The operation is done in-place when o1 supports it.  This is the
    equivalent of the Python statement o1 ^= o2."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], PyObject)
def PyNumber_InPlaceOr(space, o1, o2):
    """Returns the "bitwise or" of o1 and o2 on success, or NULL on failure.  The
    operation is done in-place when o1 supports it.  This is the equivalent of
    the Python statement o1 |= o2."""
    raise NotImplementedError

@cpython_api([PyObjectP, PyObjectP], rffi.INT_real)
def PyNumber_Coerce(space, p1, p2):
    """
    
    
    
    This function takes the addresses of two variables of type PyObject*.
    If the objects pointed to by *p1 and *p2 have the same type, increment
    their reference count and return 0 (success). If the objects can be
    converted to a common numeric type, replace *p1 and *p2 by their
    converted value (with 'new' reference counts), and return 0. If no
    conversion is possible, or if some other error occurs, return -1 (failure)
    and don't increment the reference counts.  The call PyNumber_Coerce(&o1,
    &o2) is equivalent to the Python statement o1, o2 = coerce(o1, o2)."""
    raise NotImplementedError

@cpython_api([PyObjectP, PyObjectP], rffi.INT_real)
def PyNumber_CoerceEx(space, p1, p2):
    """This function is similar to PyNumber_Coerce(), except that it returns
    1 when the conversion is not possible and when no error is raised.
    Reference counts are still not increased in this case."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyNumber_Int(space, o):
    """
    
    
    
    Returns the o converted to an integer object on success, or NULL on failure.
    If the argument is outside the integer range a long object will be returned
    instead. This is the equivalent of the Python expression int(o)."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyNumber_Long(space, o):
    """
    
    
    
    Returns the o converted to a long integer object on success, or NULL on
    failure.  This is the equivalent of the Python expression long(o)."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyNumber_Index(space, o):
    """Returns the o converted to a Python int or long on success or NULL with a
    TypeError exception raised on failure.
    """
    raise NotImplementedError

@cpython_api([PyObject, rffi.INT_real], PyObject)
def PyNumber_ToBase(space, n, base):
    """Returns the integer n converted to base as a string with a base
    marker of '0b', '0o', or '0x' if applicable.  When
    base is not 2, 8, 10, or 16, the format is 'x#num' where x is the
    base. If n is not an int object, it is converted with
    PyNumber_Index() first.
    """
    raise NotImplementedError

@cpython_api([PyObject, PyObject], Py_ssize_t)
def PyNumber_AsSsize_t(space, o, exc):
    """Returns o converted to a Py_ssize_t value if o can be interpreted as an
    integer. If o can be converted to a Python int or long but the attempt to
    convert to a Py_ssize_t value would raise an OverflowError, then the
    exc argument is the type of exception that will be raised (usually
    IndexError or OverflowError).  If exc is NULL, then the
    exception is cleared and the value is clipped to PY_SSIZE_T_MIN for a negative
    integer or PY_SSIZE_T_MAX for a positive integer.
    """
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PyIndex_Check(space, o):
    """Returns True if o is an index integer (has the nb_index slot of  the
    tp_as_number structure filled in).
    """
    raise NotImplementedError

@cpython_api([PyObject, {const char**}, Py_ssize_t], rffi.INT_real)
def PyObject_AsCharBuffer(space, obj, buffer, buffer_len):
    """Returns a pointer to a read-only memory location usable as character-based
    input.  The obj argument must support the single-segment character buffer
    interface.  On success, returns 0, sets buffer to the memory location
    and buffer_len to the buffer length.  Returns -1 and sets a
    TypeError on error.
    
    
    
    This function used an int * type for buffer_len. This might
    require changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject, {const void**}, Py_ssize_t], rffi.INT_real)
def PyObject_AsReadBuffer(space, obj, buffer, buffer_len):
    """Returns a pointer to a read-only memory location containing arbitrary data.
    The obj argument must support the single-segment readable buffer
    interface.  On success, returns 0, sets buffer to the memory location
    and buffer_len to the buffer length.  Returns -1 and sets a
    TypeError on error.
    
    
    
    This function used an int * type for buffer_len. This might
    require changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PyObject_CheckReadBuffer(space, o):
    """Returns 1 if o supports the single-segment readable buffer interface.
    Otherwise returns 0.
    """
    raise NotImplementedError

@cpython_api([PyObject, {void**}, Py_ssize_t], rffi.INT_real)
def PyObject_AsWriteBuffer(space, obj, buffer, buffer_len):
    """Returns a pointer to a writeable memory location.  The obj argument must
    support the single-segment, character buffer interface.  On success,
    returns 0, sets buffer to the memory location and buffer_len to the
    buffer length.  Returns -1 and sets a TypeError on error.
    
    
    
    This function used an int * type for buffer_len. This might
    require changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject, {FILE*}, rffi.INT_real], rffi.INT_real)
def PyObject_Print(space, o, fp, flags):
    """Print an object o, on file fp.  Returns -1 on error.  The flags argument
    is used to enable certain printing options.  The only option currently supported
    is Py_PRINT_RAW; if given, the str() of the object is written
    instead of the repr()."""
    raise NotImplementedError

@cpython_api([PyObject, rffi.CCHARP], rffi.INT_real)
def PyObject_HasAttrString(space, o, attr_name):
    """Returns 1 if o has the attribute attr_name, and 0 otherwise.  This
    is equivalent to the Python expression hasattr(o, attr_name).  This function
    always succeeds."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], PyObject)
def PyObject_GetAttr(space, o, attr_name):
    """Retrieve an attribute named attr_name from object o. Returns the attribute
    value on success, or NULL on failure.  This is the equivalent of the Python
    expression o.attr_name."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], PyObject)
def PyObject_GenericGetAttr(space, o, name):
    """Generic attribute getter function that is meant to be put into a type
    object's tp_getattro slot.  It looks for a descriptor in the dictionary
    of classes in the object's MRO as well as an attribute in the object's
    __dict__ (if present).  As outlined in descriptors, data
    descriptors take preference over instance attributes, while non-data
    descriptors don't.  Otherwise, an AttributeError is raised."""
    raise NotImplementedError

@cpython_api([PyObject, rffi.CCHARP, PyObject], rffi.INT_real)
def PyObject_SetAttrString(space, o, attr_name, v):
    """Set the value of the attribute named attr_name, for object o, to the value
    v. Returns -1 on failure.  This is the equivalent of the Python statement
    o.attr_name = v."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject, PyObject], rffi.INT_real)
def PyObject_GenericSetAttr(space, o, name, value):
    """Generic attribute setter function that is meant to be put into a type
    object's tp_setattro slot.  It looks for a data descriptor in the
    dictionary of classes in the object's MRO, and if found it takes preference
    over setting the attribute in the instance dictionary. Otherwise, the
    attribute is set in the object's __dict__ (if present).  Otherwise,
    an AttributeError is raised and -1 is returned."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], rffi.INT_real)
def PyObject_DelAttr(space, o, attr_name):
    """Delete attribute named attr_name, for object o. Returns -1 on failure.
    This is the equivalent of the Python statement del o.attr_name."""
    raise NotImplementedError

@cpython_api([PyObject, rffi.CCHARP], rffi.INT_real)
def PyObject_DelAttrString(space, o, attr_name):
    """Delete attribute named attr_name, for object o. Returns -1 on failure.
    This is the equivalent of the Python statement del o.attr_name."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject, rffi.INT_real], PyObject)
def PyObject_RichCompare(space, o1, o2, opid):
    """Compare the values of o1 and o2 using the operation specified by opid,
    which must be one of Py_LT, Py_LE, Py_EQ,
    Py_NE, Py_GT, or Py_GE, corresponding to <,
    <=, ==, !=, >, or >= respectively. This is the equivalent of
    the Python expression o1 op o2, where op is the operator corresponding
    to opid. Returns the value of the comparison on success, or NULL on failure."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject, rffi.INT_real], rffi.INT_real)
def PyObject_RichCompareBool(space, o1, o2, opid):
    """Compare the values of o1 and o2 using the operation specified by opid,
    which must be one of Py_LT, Py_LE, Py_EQ,
    Py_NE, Py_GT, or Py_GE, corresponding to <,
    <=, ==, !=, >, or >= respectively. Returns -1 on error,
    0 if the result is false, 1 otherwise. This is the equivalent of the
    Python expression o1 op o2, where op is the operator corresponding to
    opid."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject, {int*}], rffi.INT_real)
def PyObject_Cmp(space, o1, o2, result):
    """
    
    
    
    Compare the values of o1 and o2 using a routine provided by o1, if one
    exists, otherwise with a routine provided by o2.  The result of the comparison
    is returned in result.  Returns -1 on failure.  This is the equivalent of
    the Python statement result = cmp(o1, o2)."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], rffi.INT_real)
def PyObject_Compare(space, o1, o2):
    """
    
    
    
    Compare the values of o1 and o2 using a routine provided by o1, if one
    exists, otherwise with a routine provided by o2.  Returns the result of the
    comparison on success.  On error, the value returned is undefined; use
    PyErr_Occurred() to detect an error.  This is equivalent to the Python
    expression cmp(o1, o2)."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyObject_Repr(space, o):
    """
    
    
    
    Compute a string representation of object o.  Returns the string
    representation on success, NULL on failure.  This is the equivalent of the
    Python expression repr(o).  Called by the repr() built-in function and
    by reverse quotes."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyObject_Str(space, o):
    """
    
    
    
    Compute a string representation of object o.  Returns the string
    representation on success, NULL on failure.  This is the equivalent of the
    Python expression str(o).  Called by the str() built-in function and
    by the print statement."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyObject_Bytes(space, o):
    """
    
    
    
    Compute a bytes representation of object o.  In 2.x, this is just a alias
    for PyObject_Str()."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyObject_Unicode(space, o):
    """
    
    
    
    Compute a Unicode string representation of object o.  Returns the Unicode
    string representation on success, NULL on failure. This is the equivalent of
    the Python expression unicode(o).  Called by the unicode() built-in
    function."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], rffi.INT_real)
def PyObject_IsInstance(space, inst, cls):
    """Returns 1 if inst is an instance of the class cls or a subclass of
    cls, or 0 if not.  On error, returns -1 and sets an exception.  If
    cls is a type object rather than a class object, PyObject_IsInstance()
    returns 1 if inst is of type cls.  If cls is a tuple, the check will
    be done against every entry in cls. The result will be 1 when at least one
    of the checks returns 1, otherwise it will be 0. If inst is not a
    class instance and cls is neither a type object, nor a class object, nor a
    tuple, inst must have a __class__ attribute --- the class relationship
    of the value of that attribute with cls will be used to determine the result
    of this function.
    
    
    
    Support for a tuple as the second argument added."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], rffi.INT_real)
def PyObject_IsSubclass(space, derived, cls):
    """Returns 1 if the class derived is identical to or derived from the class
    cls, otherwise returns 0.  In case of an error, returns -1. If cls
    is a tuple, the check will be done against every entry in cls. The result will
    be 1 when at least one of the checks returns 1, otherwise it will be
    0. If either derived or cls is not an actual class object (or tuple),
    this function uses the generic algorithm described above.
    
    
    
    Older versions of Python did not support a tuple as the second argument."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PyCallable_Check(space, o):
    """Determine if the object o is callable.  Return 1 if the object is callable
    and 0 otherwise.  This function always succeeds."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject, PyObject], PyObject)
def PyObject_Call(space, callable_object, args, kw):
    """
    
    
    
    Call a callable Python object callable_object, with arguments given by the
    tuple args, and named arguments given by the dictionary kw. If no named
    arguments are needed, kw may be NULL. args must not be NULL, use an
    empty tuple if no arguments are needed. Returns the result of the call on
    success, or NULL on failure.  This is the equivalent of the Python expression
    apply(callable_object, args, kw) or callable_object(*args, **kw).
    """
    raise NotImplementedError

@cpython_api([PyObject, rffi.CCHARP, ...], PyObject)
def PyObject_CallFunction(space, callable, format, ):
    """
    
    
    
    Call a callable Python object callable, with a variable number of C arguments.
    The C arguments are described using a Py_BuildValue() style format
    string.  The format may be NULL, indicating that no arguments are provided.
    Returns the result of the call on success, or NULL on failure.  This is the
    equivalent of the Python expression apply(callable, args) or
    callable(*args). Note that if you only pass PyObject * args,
    PyObject_CallFunctionObjArgs() is a faster alternative."""
    raise NotImplementedError

@cpython_api([PyObject, rffi.CCHARP, rffi.CCHARP, ...], PyObject)
def PyObject_CallMethod(space, o, method, format, ):
    """Call the method named method of object o with a variable number of C
    arguments.  The C arguments are described by a Py_BuildValue() format
    string that should  produce a tuple.  The format may be NULL, indicating that
    no arguments are provided. Returns the result of the call on success, or NULL
    on failure.  This is the equivalent of the Python expression o.method(args).
    Note that if you only pass PyObject * args,
    PyObject_CallMethodObjArgs() is a faster alternative."""
    raise NotImplementedError

@cpython_api([PyObject, ..., {NULL}], PyObject)
def PyObject_CallFunctionObjArgs(space, callable, , ):
    """Call a callable Python object callable, with a variable number of
    PyObject* arguments.  The arguments are provided as a variable number
    of parameters followed by NULL. Returns the result of the call on success, or
    NULL on failure.
    """
    raise NotImplementedError

@cpython_api([PyObject, PyObject, ..., {NULL}], PyObject)
def PyObject_CallMethodObjArgs(space, o, name, , ):
    """Calls a method of the object o, where the name of the method is given as a
    Python string object in name.  It is called with a variable number of
    PyObject* arguments.  The arguments are provided as a variable number
    of parameters followed by NULL. Returns the result of the call on success, or
    NULL on failure.
    """
    raise NotImplementedError

@cpython_api([PyObject], lltype.Signed)
def PyObject_Hash(space, o):
    """
    
    
    
    Compute and return the hash value of an object o.  On failure, return -1.
    This is the equivalent of the Python expression hash(o)."""
    raise NotImplementedError

@cpython_api([PyObject], lltype.Signed)
def PyObject_HashNotImplemented(space, o):
    """Set a TypeError indicating that type(o) is not hashable and return -1.
    This function receives special treatment when stored in a tp_hash slot,
    allowing a type to explicitly indicate to the interpreter that it is not
    hashable.
    """
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyObject_Type(space, o):
    """
    
    
    
    When o is non-NULL, returns a type object corresponding to the object type
    of object o. On failure, raises SystemError and returns NULL.  This
    is equivalent to the Python expression type(o). This function increments the
    reference count of the return value. There's really no reason to use this
    function instead of the common expression o->ob_type, which returns a
    pointer of type PyTypeObject*, except when the incremented reference
    count is needed."""
    raise NotImplementedError

@cpython_api([PyObject, PyTypeObjectPtr], rffi.INT_real)
def PyObject_TypeCheck(space, o, type):
    """Return true if the object o is of type type or a subtype of type.  Both
    parameters must be non-NULL.
    """
    raise NotImplementedError

@cpython_api([PyObject], Py_ssize_t)
def PyObject_Length(space, o):
    """
    
    
    
    Return the length of object o.  If the object o provides either the sequence
    and mapping protocols, the sequence length is returned.  On error, -1 is
    returned.  This is the equivalent to the Python expression len(o).
    
    These functions returned an int type. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject, PyObject], rffi.INT_real)
def PyObject_SetItem(space, o, key, v):
    """Map the object key to the value v.  Returns -1 on failure.  This is the
    equivalent of the Python statement o[key] = v."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], rffi.INT_real)
def PyObject_DelItem(space, o, key):
    """Delete the mapping for key from o.  Returns -1 on failure. This is the
    equivalent of the Python statement del o[key]."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PyObject_AsFileDescriptor(space, o):
    """Derives a file descriptor from a Python object.  If the object is an integer or
    long integer, its value is returned.  If not, the object's fileno() method
    is called if it exists; the method must return an integer or long integer, which
    is returned as the file descriptor value.  Returns -1 on failure."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyObject_Dir(space, o):
    """This is equivalent to the Python expression dir(o), returning a (possibly
    empty) list of strings appropriate for the object argument, or NULL if there
    was an error.  If the argument is NULL, this is like the Python dir(),
    returning the names of the current locals; in this case, if no execution frame
    is active then NULL is returned but PyErr_Occurred() will return false."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyObject_GetIter(space, o):
    """This is equivalent to the Python expression iter(o). It returns a new
    iterator for the object argument, or the object  itself if the object is already
    an iterator.  Raises TypeError and returns NULL if the object cannot be
    iterated."""
    raise NotImplementedError

@cpython_api([PyObject], lltype.Void)
def Py_INCREF(space, o):
    """Increment the reference count for object o.  The object must not be NULL; if
    you aren't sure that it isn't NULL, use Py_XINCREF()."""
    raise NotImplementedError

@cpython_api([PyObject], lltype.Void)
def Py_XINCREF(space, o):
    """Increment the reference count for object o.  The object may be NULL, in
    which case the macro has no effect."""
    raise NotImplementedError

@cpython_api([PyObject], lltype.Void)
def Py_DECREF(space, o):
    """Decrement the reference count for object o.  The object must not be NULL; if
    you aren't sure that it isn't NULL, use Py_XDECREF().  If the reference
    count reaches zero, the object's type's deallocation function (which must not be
    NULL) is invoked.
    
    The deallocation function can cause arbitrary Python code to be invoked (e.g.
    when a class instance with a __del__() method is deallocated).  While
    exceptions in such code are not propagated, the executed code has free access to
    all Python global variables.  This means that any object that is reachable from
    a global variable should be in a consistent state before Py_DECREF() is
    invoked.  For example, code to delete an object from a list should copy a
    reference to the deleted object in a temporary variable, update the list data
    structure, and then call Py_DECREF() for the temporary variable."""
    raise NotImplementedError

@cpython_api([PyObject], lltype.Void)
def Py_XDECREF(space, o):
    """Decrement the reference count for object o.  The object may be NULL, in
    which case the macro has no effect; otherwise the effect is the same as for
    Py_DECREF(), and the same warning applies."""
    raise NotImplementedError

@cpython_api([PyObject], lltype.Void)
def Py_CLEAR(space, o):
    """Decrement the reference count for object o.  The object may be NULL, in
    which case the macro has no effect; otherwise the effect is the same as for
    Py_DECREF(), except that the argument is also set to NULL.  The warning
    for Py_DECREF() does not apply with respect to the object passed because
    the macro carefully uses a temporary variable and sets the argument to NULL
    before decrementing its reference count.
    
    It is a good idea to use this macro whenever decrementing the value of a
    variable that might be traversed during garbage collection.
    """
    raise NotImplementedError

@cpython_api([], PyObject, borrowed=True)
def PyEval_GetBuiltins(space, ):
    """Return a dictionary of the builtins in the current execution frame,
    or the interpreter of the thread state if no frame is currently executing."""
    raise NotImplementedError

@cpython_api([], PyObject, borrowed=True)
def PyEval_GetLocals(space, ):
    """Return a dictionary of the local variables in the current execution frame,
    or NULL if no frame is currently executing."""
    raise NotImplementedError

@cpython_api([], PyObject, borrowed=True)
def PyEval_GetGlobals(space, ):
    """Return a dictionary of the global variables in the current execution frame,
    or NULL if no frame is currently executing."""
    raise NotImplementedError

@cpython_api([], {PyFrameObject*}, borrowed=True)
def PyEval_GetFrame(space, ):
    """Return the current thread state's frame, which is NULL if no frame is
    currently executing."""
    raise NotImplementedError

@cpython_api([{PyFrameObject*}], rffi.INT_real)
def PyFrame_GetLineNumber(space, frame):
    """Return the line number that frame is currently executing."""
    raise NotImplementedError

@cpython_api([], rffi.INT_real)
def PyEval_GetRestricted(space, ):
    """If there is a current frame and it is executing in restricted mode, return true,
    otherwise false."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.CCHARP)
def PyEval_GetFuncName(space, func):
    """Return the name of func if it is a function, class or instance object, else the
    name of funcs type."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.CCHARP)
def PyEval_GetFuncDesc(space, func):
    """Return a description string, depending on the type of func.
    Return values include "()" for functions and methods, " constructor",
    " instance", and " object".  Concatenated with the result of
    PyEval_GetFuncName(), the result will be a description of
    func."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PySequence_Check(space, o):
    """Return 1 if the object provides sequence protocol, and 0 otherwise.
    This function always succeeds."""
    raise NotImplementedError

@cpython_api([PyObject], Py_ssize_t)
def PySequence_Size(space, o):
    """
    
    
    
    Returns the number of objects in sequence o on success, and -1 on failure.
    For objects that do not provide sequence protocol, this is equivalent to the
    Python expression len(o).
    
    These functions returned an int type. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], PyObject)
def PySequence_Concat(space, o1, o2):
    """Return the concatenation of o1 and o2 on success, and NULL on failure.
    This is the equivalent of the Python expression o1 + o2."""
    raise NotImplementedError

@cpython_api([PyObject, Py_ssize_t], PyObject)
def PySequence_Repeat(space, o, count):
    """Return the result of repeating sequence object o count times, or NULL on
    failure.  This is the equivalent of the Python expression o * count.
    
    This function used an int type for count. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], PyObject)
def PySequence_InPlaceConcat(space, o1, o2):
    """Return the concatenation of o1 and o2 on success, and NULL on failure.
    The operation is done in-place when o1 supports it.  This is the equivalent
    of the Python expression o1 += o2."""
    raise NotImplementedError

@cpython_api([PyObject, Py_ssize_t], PyObject)
def PySequence_InPlaceRepeat(space, o, count):
    """Return the result of repeating sequence object o count times, or NULL on
    failure.  The operation is done in-place when o supports it.  This is the
    equivalent of the Python expression o *= count.
    
    This function used an int type for count. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject, Py_ssize_t], PyObject)
def PySequence_GetItem(space, o, i):
    """Return the ith element of o, or NULL on failure. This is the equivalent of
    the Python expression o[i].
    
    This function used an int type for i. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject, Py_ssize_t, PyObject], rffi.INT_real)
def PySequence_SetItem(space, o, i, v):
    """Assign object v to the ith element of o.  Returns -1 on failure.  This
    is the equivalent of the Python statement o[i] = v.  This function does
    not steal a reference to v.
    
    This function used an int type for i. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject, Py_ssize_t], rffi.INT_real)
def PySequence_DelItem(space, o, i):
    """Delete the ith element of object o.  Returns -1 on failure.  This is the
    equivalent of the Python statement del o[i].
    
    This function used an int type for i. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject, Py_ssize_t, Py_ssize_t, PyObject], rffi.INT_real)
def PySequence_SetSlice(space, o, i1, i2, v):
    """Assign the sequence object v to the slice in sequence object o from i1 to
    i2.  This is the equivalent of the Python statement o[i1:i2] = v.
    
    This function used an int type for i1 and i2. This might
    require changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject, Py_ssize_t, Py_ssize_t], rffi.INT_real)
def PySequence_DelSlice(space, o, i1, i2):
    """Delete the slice in sequence object o from i1 to i2.  Returns -1 on
    failure.  This is the equivalent of the Python statement del o[i1:i2].
    
    This function used an int type for i1 and i2. This might
    require changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], Py_ssize_t)
def PySequence_Count(space, o, value):
    """Return the number of occurrences of value in o, that is, return the number
    of keys for which o[key] == value.  On failure, return -1.  This is
    equivalent to the Python expression o.count(value).
    
    This function returned an int type. This might require changes
    in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], rffi.INT_real)
def PySequence_Contains(space, o, value):
    """Determine if o contains value.  If an item in o is equal to value,
    return 1, otherwise return 0. On error, return -1.  This is
    equivalent to the Python expression value in o."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], Py_ssize_t)
def PySequence_Index(space, o, value):
    """Return the first index i for which o[i] == value.  On error, return
    -1.    This is equivalent to the Python expression o.index(value).
    
    This function returned an int type. This might require changes
    in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PySequence_List(space, o):
    """Return a list object with the same contents as the arbitrary sequence o.  The
    returned list is guaranteed to be new."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PySequence_Tuple(space, o):
    """
    
    
    
    Return a tuple object with the same contents as the arbitrary sequence o or
    NULL on failure.  If o is a tuple, a new reference will be returned,
    otherwise a tuple will be constructed with the appropriate contents.  This is
    equivalent to the Python expression tuple(o)."""
    raise NotImplementedError

@cpython_api([PyObject], PyObjectP)
def PySequence_Fast_ITEMS(space, o):
    """Return the underlying array of PyObject pointers.  Assumes that o was returned
    by PySequence_Fast() and o is not NULL.
    
    Note, if a list gets resized, the reallocation may relocate the items array.
    So, only use the underlying array pointer in contexts where the sequence
    cannot change.
    """
    raise NotImplementedError

@cpython_api([PyObject, Py_ssize_t], PyObject)
def PySequence_ITEM(space, o, i):
    """Return the ith element of o or NULL on failure. Macro form of
    PySequence_GetItem() but without checking that
    PySequence_Check(o)() is true and without adjustment for negative
    indices.
    
    
    
    This function used an int type for i. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PySet_Check(space, p):
    """Return true if p is a set object or an instance of a subtype.
    """
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PyFrozenSet_Check(space, p):
    """Return true if p is a frozenset object or an instance of a
    subtype.
    """
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PyAnySet_Check(space, p):
    """Return true if p is a set object, a frozenset object, or an
    instance of a subtype."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PyAnySet_CheckExact(space, p):
    """Return true if p is a set object or a frozenset object but
    not an instance of a subtype."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PyFrozenSet_CheckExact(space, p):
    """Return true if p is a frozenset object but not an instance of a
    subtype."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PySet_New(space, iterable):
    """Return a new set containing objects returned by the iterable.  The
    iterable may be NULL to create a new empty set.  Return the new set on
    success or NULL on failure.  Raise TypeError if iterable is not
    actually iterable.  The constructor is also useful for copying a set
    (c=set(s))."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyFrozenSet_New(space, iterable):
    """Return a new frozenset containing objects returned by the iterable.
    The iterable may be NULL to create a new empty frozenset.  Return the new
    set on success or NULL on failure.  Raise TypeError if iterable is
    not actually iterable.
    
    Now guaranteed to return a brand-new frozenset.  Formerly,
    frozensets of zero-length were a singleton.  This got in the way of
    building-up new frozensets with PySet_Add()."""
    raise NotImplementedError

@cpython_api([PyObject], Py_ssize_t)
def PySet_Size(space, anyset):
    """
    
    
    
    Return the length of a set or frozenset object. Equivalent to
    len(anyset).  Raises a PyExc_SystemError if anyset is not a
    set, frozenset, or an instance of a subtype.
    
    This function returned an int. This might require changes in
    your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject], Py_ssize_t)
def PySet_GET_SIZE(space, anyset):
    """Macro form of PySet_Size() without error checking."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], rffi.INT_real)
def PySet_Contains(space, anyset, key):
    """Return 1 if found, 0 if not found, and -1 if an error is encountered.  Unlike
    the Python __contains__() method, this function does not automatically
    convert unhashable sets into temporary frozensets.  Raise a TypeError if
    the key is unhashable. Raise PyExc_SystemError if anyset is not a
    set, frozenset, or an instance of a subtype."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], rffi.INT_real)
def PySet_Add(space, set, key):
    """Add key to a set instance.  Does not apply to frozenset
    instances.  Return 0 on success or -1 on failure. Raise a TypeError if
    the key is unhashable. Raise a MemoryError if there is no room to grow.
    Raise a SystemError if set is an not an instance of set or its
    subtype.
    
    Now works with instances of frozenset or its subtypes.
    Like PyTuple_SetItem() in that it can be used to fill-in the
    values of brand new frozensets before they are exposed to other code."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], rffi.INT_real)
def PySet_Discard(space, set, key):
    """Return 1 if found and removed, 0 if not found (no action taken), and -1 if an
    error is encountered.  Does not raise KeyError for missing keys.  Raise a
    TypeError if the key is unhashable.  Unlike the Python discard()
    method, this function does not automatically convert unhashable sets into
    temporary frozensets. Raise PyExc_SystemError if set is an not an
    instance of set or its subtype."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PySet_Pop(space, set):
    """Return a new reference to an arbitrary object in the set, and removes the
    object from the set.  Return NULL on failure.  Raise KeyError if the
    set is empty. Raise a SystemError if set is an not an instance of
    set or its subtype."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PySet_Clear(space, set):
    """Empty an existing set of all elements."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PySlice_Check(space, ob):
    """Return true if ob is a slice object; ob must not be NULL."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject, PyObject], PyObject)
def PySlice_New(space, start, stop, step):
    """Return a new slice object with the given values.  The start, stop, and
    step parameters are used as the values of the slice object attributes of
    the same names.  Any of the values may be NULL, in which case the
    None will be used for the corresponding attribute.  Return NULL if
    the new object could not be allocated."""
    raise NotImplementedError

@cpython_api([{PySliceObject*}, Py_ssize_t, Py_ssize_t, Py_ssize_t, Py_ssize_t], rffi.INT_real)
def PySlice_GetIndices(space, slice, length, start, stop, step):
    """Retrieve the start, stop and step indices from the slice object slice,
    assuming a sequence of length length. Treats indices greater than
    length as errors.
    
    Returns 0 on success and -1 on error with no exception set (unless one of
    the indices was not None and failed to be converted to an integer,
    in which case -1 is returned with an exception set).
    
    You probably do not want to use this function.  If you want to use slice
    objects in versions of Python prior to 2.3, you would probably do well to
    incorporate the source of PySlice_GetIndicesEx(), suitably renamed,
    in the source of your extension.
    
    This function used an int type for length and an
    int * type for start, stop, and step. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([{PySliceObject*}, Py_ssize_t, Py_ssize_t, Py_ssize_t, Py_ssize_t, Py_ssize_t], rffi.INT_real)
def PySlice_GetIndicesEx(space, slice, length, start, stop, step, slicelength):
    """Usable replacement for PySlice_GetIndices().  Retrieve the start,
    stop, and step indices from the slice object slice assuming a sequence of
    length length, and store the length of the slice in slicelength.  Out
    of bounds indices are clipped in a manner consistent with the handling of
    normal slices.
    
    Returns 0 on success and -1 on error with exception set.
    
    
    
    This function used an int type for length and an
    int * type for start, stop, step, and slicelength. This
    might require changes in your code for properly supporting 64-bit
    systems."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, ...], PyObject)
def PyString_FromFormat(space, format, ):
    """Take a C printf()-style format string and a variable number of
    arguments, calculate the size of the resulting Python string and return a string
    with the values formatted into it.  The variable arguments must be C types and
    must correspond exactly to the format characters in the format string.  The
    following format characters are allowed:
    
    % This should be exactly the same as the table in PyErr_Format.
    
    % One should just refer to the other.
    
    % The descriptions for %zd and %zu are wrong, but the truth is complicated
    
    % because not all compilers support the %z width modifier -- we fake it
    
    % when necessary via interpolating PY_FORMAT_SIZE_T.
    
    % Similar comments apply to the %ll width modifier and
    
    % PY_FORMAT_LONG_LONG.
    
    % %u, %lu, %zu should have "new in Python 2.5" blurbs.
    
    
    
    
    
    
    
    Format Characters
    
    Type
    
    Comment
    
    %%
    
    n/a
    
    The literal % character.
    
    %c
    
    int
    
    A single character,
    represented as an C int.
    
    %d
    
    int
    
    Exactly equivalent to
    printf("%d").
    
    %u
    
    unsigned int
    
    Exactly equivalent to
    printf("%u").
    
    %ld
    
    long
    
    Exactly equivalent to
    printf("%ld").
    
    %lu
    
    unsigned long
    
    Exactly equivalent to
    printf("%lu").
    
    %lld
    
    long long
    
    Exactly equivalent to
    printf("%lld").
    
    %llu
    
    unsigned
    long long
    
    Exactly equivalent to
    printf("%llu").
    
    %zd
    
    Py_ssize_t
    
    Exactly equivalent to
    printf("%zd").
    
    %zu
    
    size_t
    
    Exactly equivalent to
    printf("%zu").
    
    %i
    
    int
    
    Exactly equivalent to
    printf("%i").
    
    %x
    
    int
    
    Exactly equivalent to
    printf("%x").
    
    %s
    
    char*
    
    A null-terminated C character
    array.
    
    %p
    
    void*
    
    The hex representation of a C
    pointer. Mostly equivalent to
    printf("%p") except that
    it is guaranteed to start with
    the literal 0x regardless
    of what the platform's
    printf yields.
    
    An unrecognized format character causes all the rest of the format string to be
    copied as-is to the result string, and any extra arguments discarded.
    
    The "%lld" and "%llu" format specifiers are only available
    when HAVE_LONG_LONG is defined.
    
    Support for "%lld" and "%llu" added."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, {va_list}], PyObject)
def PyString_FromFormatV(space, format, vargs):
    """Identical to PyString_FromFormat() except that it takes exactly two
    arguments."""
    raise NotImplementedError

@cpython_api([PyObject], Py_ssize_t)
def PyString_GET_SIZE(space, string):
    """Macro form of PyString_Size() but without error checking.
    
    This macro returned an int type. This might require changes in
    your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.CCHARP)
def PyString_AS_STRING(space, string):
    """Macro form of PyString_AsString() but without error checking.  Only
    string objects are supported; no Unicode objects should be passed."""
    raise NotImplementedError

@cpython_api([PyObject, {char**}, Py_ssize_t], rffi.INT_real)
def PyString_AsStringAndSize(space, obj, buffer, length):
    """Return a NUL-terminated representation of the contents of the object obj
    through the output variables buffer and length.
    
    The function accepts both string and Unicode objects as input. For Unicode
    objects it returns the default encoded version of the object.  If length is
    NULL, the resulting buffer may not contain NUL characters; if it does, the
    function returns -1 and a TypeError is raised.
    
    The buffer refers to an internal string buffer of obj, not a copy. The data
    must not be modified in any way, unless the string was just created using
    PyString_FromStringAndSize(NULL, size).  It must not be deallocated.  If
    string is a Unicode object, this function computes the default encoding of
    string and operates on that.  If string is not a string object at all,
    PyString_AsStringAndSize() returns -1 and raises TypeError.
    
    This function used an int * type for length. This might
    require changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObjectP, PyObject], lltype.Void)
def PyString_Concat(space, string, newpart):
    """Create a new string object in *string containing the contents of newpart
    appended to string; the caller will own the new reference.  The reference to
    the old value of string will be stolen.  If the new string cannot be created,
    the old reference to string will still be discarded and the value of
    *string will be set to NULL; the appropriate exception will be set."""
    raise NotImplementedError

@cpython_api([PyObjectP, PyObject], lltype.Void)
def PyString_ConcatAndDel(space, string, newpart):
    """Create a new string object in *string containing the contents of newpart
    appended to string.  This version decrements the reference count of newpart."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], PyObject)
def PyString_Format(space, format, args):
    """Return a new string object from format and args. Analogous to format %
    args.  The args argument must be a tuple."""
    raise NotImplementedError

@cpython_api([PyObjectP], lltype.Void)
def PyString_InternInPlace(space, string):
    """Intern the argument *string in place.  The argument must be the address of a
    pointer variable pointing to a Python string object.  If there is an existing
    interned string that is the same as *string, it sets *string to it
    (decrementing the reference count of the old string object and incrementing the
    reference count of the interned string object), otherwise it leaves *string
    alone and interns it (incrementing its reference count).  (Clarification: even
    though there is a lot of talk about reference counts, think of this function as
    reference-count-neutral; you own the object after the call if and only if you
    owned it before the call.)
    
    This function is not available in 3.x and does not have a PyBytes alias."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP], PyObject)
def PyString_InternFromString(space, v):
    """A combination of PyString_FromString() and
    PyString_InternInPlace(), returning either a new string object that has
    been interned, or a new ("owned") reference to an earlier interned string object
    with the same value.
    
    This function is not available in 3.x and does not have a PyBytes alias."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, Py_ssize_t, rffi.CCHARP, rffi.CCHARP], PyObject)
def PyString_Decode(space, s, size, encoding, errors):
    """Create an object by decoding size bytes of the encoded buffer s using the
    codec registered for encoding.  encoding and errors have the same meaning
    as the parameters of the same name in the unicode() built-in function.
    The codec to be used is looked up using the Python codec registry.  Return
    NULL if an exception was raised by the codec.
    
    This function is not available in 3.x and does not have a PyBytes alias.
    
    This function used an int type for size. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject, rffi.CCHARP, rffi.CCHARP], PyObject)
def PyString_AsDecodedObject(space, str, encoding, errors):
    """Decode a string object by passing it to the codec registered for encoding and
    return the result as Python object. encoding and errors have the same
    meaning as the parameters of the same name in the string encode() method.
    The codec to be used is looked up using the Python codec registry. Return NULL
    if an exception was raised by the codec.
    
    This function is not available in 3.x and does not have a PyBytes alias."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, Py_ssize_t, rffi.CCHARP, rffi.CCHARP], PyObject)
def PyString_Encode(space, s, size, encoding, errors):
    """Encode the char buffer of the given size by passing it to the codec
    registered for encoding and return a Python object. encoding and errors
    have the same meaning as the parameters of the same name in the string
    encode() method. The codec to be used is looked up using the Python codec
    registry.  Return NULL if an exception was raised by the codec.
    
    This function is not available in 3.x and does not have a PyBytes alias.
    
    This function used an int type for size. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject, rffi.CCHARP, rffi.CCHARP], PyObject)
def PyString_AsEncodedObject(space, str, encoding, errors):
    """Encode a string object using the codec registered for encoding and return the
    result as Python object. encoding and errors have the same meaning as the
    parameters of the same name in the string encode() method. The codec to be
    used is looked up using the Python codec registry. Return NULL if an exception
    was raised by the codec.
    
    This function is not available in 3.x and does not have a PyBytes alias."""
    raise NotImplementedError

@cpython_api([{PyMethodDef}, PyObject, rffi.CCHARP], PyObject)
def Py_FindMethod(space, table[], ob, name):
    """Return a bound method object for an extension type implemented in C.  This
    can be useful in the implementation of a tp_getattro or
    tp_getattr handler that does not use the
    PyObject_GenericGetAttr() function."""
    raise NotImplementedError

@cpython_api([{FILE*}, rffi.CCHARP], rffi.INT_real)
def Py_FdIsInteractive(space, fp, filename):
    """Return true (nonzero) if the standard I/O file fp with name filename is
    deemed interactive.  This is the case for files for which isatty(fileno(fp))
    is true.  If the global flag Py_InteractiveFlag is true, this function
    also returns true if the filename pointer is NULL or if the name is equal to
    one of the strings '<stdin>' or '???'."""
    raise NotImplementedError

@cpython_api([], lltype.Void)
def PyOS_AfterFork(space, ):
    """Function to update some internal state after a process fork; this should be
    called in the new process if the Python interpreter will continue to be used.
    If a new executable is loaded into the new process, this function does not need
    to be called."""
    raise NotImplementedError

@cpython_api([], rffi.INT_real)
def PyOS_CheckStack(space, ):
    """Return true when the interpreter runs out of stack space.  This is a reliable
    check, but is only available when USE_STACKCHECK is defined (currently
    on Windows using the Microsoft Visual C++ compiler).  USE_STACKCHECK
    will be defined automatically; you should never change the definition in your
    own code."""
    raise NotImplementedError

@cpython_api([rffi.INT_real], {PyOS_sighandler_t})
def PyOS_getsig(space, i):
    """Return the current signal handler for signal i.  This is a thin wrapper around
    either sigaction() or signal().  Do not call those functions
    directly! PyOS_sighandler_t is a typedef alias for void
    (*)(int)."""
    raise NotImplementedError

@cpython_api([rffi.INT_real, {PyOS_sighandler_t}], {PyOS_sighandler_t})
def PyOS_setsig(space, i, h):
    """Set the signal handler for signal i to be h; return the old signal handler.
    This is a thin wrapper around either sigaction() or signal().  Do
    not call those functions directly!  PyOS_sighandler_t is a typedef
    alias for void (*)(int)."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, {FILE*}], {FILE*})
def PySys_GetFile(space, name, def):
    """Return the FILE* associated with the object name in the
    sys module, or def if name is not in the module or is not associated
    with a FILE*."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, PyObject], rffi.INT_real)
def PySys_SetObject(space, name, v):
    """Set name in the sys module to v unless v is NULL, in which
    case name is deleted from the sys module. Returns 0 on success, -1
    on error."""
    raise NotImplementedError

@cpython_api([], lltype.Void)
def PySys_ResetWarnOptions(space, ):
    """Reset sys.warnoptions to an empty list."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP], lltype.Void)
def PySys_AddWarnOption(space, s):
    """Append s to sys.warnoptions."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP], lltype.Void)
def PySys_SetPath(space, path):
    """Set sys.path to a list object of paths found in path which should
    be a list of paths separated with the platform's search path delimiter
    (: on Unix, ; on Windows)."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, ...], lltype.Void)
def PySys_WriteStdout(space, format, ):
    """Write the output string described by format to sys.stdout.  No
    exceptions are raised, even if truncation occurs (see below).
    
    format should limit the total size of the formatted output string to
    1000 bytes or less -- after 1000 bytes, the output string is truncated.
    In particular, this means that no unrestricted "%s" formats should occur;
    these should be limited using "%.<N>s" where <N> is a decimal number
    calculated so that <N> plus the maximum size of other formatted text does not
    exceed 1000 bytes.  Also watch out for "%f", which can print hundreds of
    digits for very large numbers.
    
    If a problem occurs, or sys.stdout is unset, the formatted message
    is written to the real (C level) stdout."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, ...], lltype.Void)
def PySys_WriteStderr(space, format, ):
    """As above, but write to sys.stderr or stderr instead."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP], lltype.Void)
def Py_FatalError(space, message):
    """
    
    
    
    Print a fatal error message and kill the process.  No cleanup is performed.
    This function should only be invoked when a condition is detected that would
    make it dangerous to continue using the Python interpreter; e.g., when the
    object administration appears to be corrupted.  On Unix, the standard C library
    function abort() is called which will attempt to produce a core
    file."""
    raise NotImplementedError

@cpython_api([rffi.INT_real], lltype.Void)
def Py_Exit(space, status):
    """
    
    
    
    Exit the current process.  This calls Py_Finalize() and then calls the
    standard C library function exit(status)."""
    raise NotImplementedError

@cpython_api([{void (*func)}], rffi.INT_real)
def Py_AtExit(space, ()):
    """
    
    
    
    Register a cleanup function to be called by Py_Finalize().  The cleanup
    function will be called with no arguments and should return no value.  At most
    32 cleanup functions can be registered.  When the registration is successful,
    Py_AtExit() returns 0; on failure, it returns -1.  The cleanup
    function registered last is called first. Each cleanup function will be called
    at most once.  Since Python's internal finalization will have completed before
    the cleanup function, no Python APIs should be called by func."""
    raise NotImplementedError

@cpython_api([Py_ssize_t, ...], PyObject)
def PyTuple_Pack(space, n, ):
    """Return a new tuple object of size n, or NULL on failure. The tuple values
    are initialized to the subsequent n C arguments pointing to Python objects.
    PyTuple_Pack(2, a, b) is equivalent to Py_BuildValue("(OO)", a, b).
    
    
    
    This function used an int type for n. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject, Py_ssize_t], PyObject, borrowed=True)
def PyTuple_GET_ITEM(space, p, pos):
    """Like PyTuple_GetItem(), but does no checking of its arguments.
    
    This function used an int type for pos. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject, Py_ssize_t, Py_ssize_t], PyObject)
def PyTuple_GetSlice(space, p, low, high):
    """Take a slice of the tuple pointed to by p from low to high and return it
    as a new tuple.
    
    This function used an int type for low and high. This might
    require changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject, Py_ssize_t, PyObject], lltype.Void)
def PyTuple_SET_ITEM(space, p, pos, o):
    """Like PyTuple_SetItem(), but does no error checking, and should only be
    used to fill in brand new tuples.
    
    This function "steals" a reference to o.
    
    This function used an int type for pos. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObjectP, Py_ssize_t], rffi.INT_real)
def _PyTuple_Resize(space, p, newsize):
    """Can be used to resize a tuple.  newsize will be the new length of the tuple.
    Because tuples are supposed to be immutable, this should only be used if there
    is only one reference to the object.  Do not use this if the tuple may already
    be known to some other part of the code.  The tuple will always grow or shrink
    at the end.  Think of this as destroying the old tuple and creating a new one,
    only more efficiently.  Returns 0 on success. Client code should never
    assume that the resulting value of *p will be the same as before calling
    this function. If the object referenced by *p is replaced, the original
    *p is destroyed.  On failure, returns -1 and sets *p to NULL, and
    raises MemoryError or SystemError.
    
    Removed unused third parameter, last_is_sticky.
    
    This function used an int type for newsize. This might
    require changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([], rffi.INT_real)
def PyTuple_ClearFreeList(space, ):
    """Clear the free list. Return the total number of freed items.
    """
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PyType_Check(space, o):
    """Return true if the object o is a type object, including instances of types
    derived from the standard type object.  Return false in all other cases."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PyType_CheckExact(space, o):
    """Return true if the object o is a type object, but not a subtype of the
    standard type object.  Return false in all other cases.
    """
    raise NotImplementedError

@cpython_api([], {unsigned int})
def PyType_ClearCache(space, ):
    """Clear the internal lookup cache. Return the current version tag.
    """
    raise NotImplementedError

@cpython_api([PyTypeObjectPtr], lltype.Void)
def PyType_Modified(space, type):
    """Invalidate the internal lookup cache for the type and all of its
    subtypes.  This function must be called after any manual
    modification of the attributes or base classes of the type.
    """
    raise NotImplementedError

@cpython_api([PyObject, rffi.INT_real], rffi.INT_real)
def PyType_HasFeature(space, o, feature):
    """Return true if the type object o sets the feature feature.  Type features
    are denoted by single bit flags."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PyType_IS_GC(space, o):
    """Return true if the type object includes support for the cycle detector; this
    tests the type flag Py_TPFLAGS_HAVE_GC.
    """
    raise NotImplementedError

@cpython_api([PyTypeObjectPtr, PyTypeObjectPtr], rffi.INT_real)
def PyType_IsSubtype(space, a, b):
    """Return true if a is a subtype of b.
    """
    raise NotImplementedError

@cpython_api([PyTypeObjectPtr, Py_ssize_t], PyObject)
def PyType_GenericAlloc(space, type, nitems):
    """
    
    This function used an int type for nitems. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyTypeObjectPtr, PyObject, PyObject], PyObject)
def PyType_GenericNew(space, type, args, kwds):
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PyUnicode_Check(space, o):
    """Return true if the object o is a Unicode object or an instance of a Unicode
    subtype.
    
    Allowed subtypes to be accepted."""
    raise NotImplementedError

@cpython_api([PyObject], rffi.INT_real)
def PyUnicode_CheckExact(space, o):
    """Return true if the object o is a Unicode object, but not an instance of a
    subtype.
    """
    raise NotImplementedError

@cpython_api([], rffi.INT_real)
def PyUnicode_ClearFreeList(space, ):
    """Clear the free list. Return the total number of freed items.
    """
    raise NotImplementedError

@cpython_api([{Py_UNICODE}], rffi.INT_real)
def Py_UNICODE_ISTITLE(space, ch):
    """Return 1 or 0 depending on whether ch is a titlecase character."""
    raise NotImplementedError

@cpython_api([{Py_UNICODE}], rffi.INT_real)
def Py_UNICODE_ISDIGIT(space, ch):
    """Return 1 or 0 depending on whether ch is a digit character."""
    raise NotImplementedError

@cpython_api([{Py_UNICODE}], rffi.INT_real)
def Py_UNICODE_ISNUMERIC(space, ch):
    """Return 1 or 0 depending on whether ch is a numeric character."""
    raise NotImplementedError

@cpython_api([{Py_UNICODE}], rffi.INT_real)
def Py_UNICODE_ISALPHA(space, ch):
    """Return 1 or 0 depending on whether ch is an alphabetic character."""
    raise NotImplementedError

@cpython_api([{Py_UNICODE}], {Py_UNICODE})
def Py_UNICODE_TOTITLE(space, ch):
    """Return the character ch converted to title case."""
    raise NotImplementedError

@cpython_api([{Py_UNICODE}], rffi.INT_real)
def Py_UNICODE_TODECIMAL(space, ch):
    """Return the character ch converted to a decimal positive integer.  Return
    -1 if this is not possible.  This macro does not raise exceptions."""
    raise NotImplementedError

@cpython_api([{Py_UNICODE}], rffi.INT_real)
def Py_UNICODE_TODIGIT(space, ch):
    """Return the character ch converted to a single digit integer. Return -1 if
    this is not possible.  This macro does not raise exceptions."""
    raise NotImplementedError

@cpython_api([{Py_UNICODE}], {double})
def Py_UNICODE_TONUMERIC(space, ch):
    """Return the character ch converted to a double. Return -1.0 if this is not
    possible.  This macro does not raise exceptions."""
    raise NotImplementedError

@cpython_api([{const Py_UNICODE*}, Py_ssize_t], PyObject)
def PyUnicode_FromUnicode(space, u, size):
    """Create a Unicode Object from the Py_UNICODE buffer u of the given size. u
    may be NULL which causes the contents to be undefined. It is the user's
    responsibility to fill in the needed data.  The buffer is copied into the new
    object. If the buffer is not NULL, the return value might be a shared object.
    Therefore, modification of the resulting Unicode object is only allowed when u
    is NULL.
    
    This function used an int type for size. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject], Py_ssize_t)
def PyUnicode_GetSize(space, unicode):
    """Return the length of the Unicode object.
    
    This function returned an int type. This might require changes
    in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject, rffi.CCHARP, rffi.CCHARP], PyObject)
def PyUnicode_FromEncodedObject(space, obj, encoding, errors):
    """Coerce an encoded object obj to an Unicode object and return a reference with
    incremented refcount.
    
    String and other char buffer compatible objects are decoded according to the
    given encoding and using the error handling defined by errors.  Both can be
    NULL to have the interface use the default values (see the next section for
    details).
    
    All other objects, including Unicode objects, cause a TypeError to be
    set.
    
    The API returns NULL if there was an error.  The caller is responsible for
    decref'ing the returned objects."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyUnicode_FromObject(space, obj):
    """Shortcut for PyUnicode_FromEncodedObject(obj, NULL, "strict") which is used
    throughout the interpreter whenever coercion to Unicode is needed."""
    raise NotImplementedError

@cpython_api([{const wchar_t*}, Py_ssize_t], PyObject)
def PyUnicode_FromWideChar(space, w, size):
    """Create a Unicode object from the wchar_t buffer w of the given size.
    Return NULL on failure.
    
    This function used an int type for size. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([{PyUnicodeObject*}, {wchar_t*}, Py_ssize_t], Py_ssize_t)
def PyUnicode_AsWideChar(space, unicode, w, size):
    """Copy the Unicode object contents into the wchar_t buffer w.  At most
    size wchar_t characters are copied (excluding a possibly trailing
    0-termination character).  Return the number of wchar_t characters
    copied or -1 in case of an error.  Note that the resulting wchar_t
    string may or may not be 0-terminated.  It is the responsibility of the caller
    to make sure that the wchar_t string is 0-terminated in case this is
    required by the application.
    
    This function returned an int type and used an int
    type for size. This might require changes in your code for properly
    supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, Py_ssize_t, rffi.CCHARP, rffi.CCHARP], PyObject)
def PyUnicode_Decode(space, s, size, encoding, errors):
    """Create a Unicode object by decoding size bytes of the encoded string s.
    encoding and errors have the same meaning as the parameters of the same name
    in the unicode() built-in function.  The codec to be used is looked up
    using the Python codec registry.  Return NULL if an exception was raised by
    the codec.
    
    This function used an int type for size. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([{const Py_UNICODE*}, Py_ssize_t, rffi.CCHARP, rffi.CCHARP], PyObject)
def PyUnicode_Encode(space, s, size, encoding, errors):
    """Encode the Py_UNICODE buffer of the given size and return a Python
    string object.  encoding and errors have the same meaning as the parameters
    of the same name in the Unicode encode() method.  The codec to be used is
    looked up using the Python codec registry.  Return NULL if an exception was
    raised by the codec.
    
    This function used an int type for size. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, Py_ssize_t, rffi.CCHARP], PyObject)
def PyUnicode_DecodeUTF8(space, s, size, errors):
    """Create a Unicode object by decoding size bytes of the UTF-8 encoded string
    s. Return NULL if an exception was raised by the codec.
    
    This function used an int type for size. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, Py_ssize_t, rffi.CCHARP, Py_ssize_t], PyObject)
def PyUnicode_DecodeUTF8Stateful(space, s, size, errors, consumed):
    """If consumed is NULL, behave like PyUnicode_DecodeUTF8(). If
    consumed is not NULL, trailing incomplete UTF-8 byte sequences will not be
    treated as an error. Those bytes will not be decoded and the number of bytes
    that have been decoded will be stored in consumed.
    
    
    
    This function used an int type for size. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([{const Py_UNICODE*}, Py_ssize_t, rffi.CCHARP], PyObject)
def PyUnicode_EncodeUTF8(space, s, size, errors):
    """Encode the Py_UNICODE buffer of the given size using UTF-8 and return a
    Python string object.  Return NULL if an exception was raised by the codec.
    
    This function used an int type for size. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyUnicode_AsUTF8String(space, unicode):
    """Encode a Unicode object using UTF-8 and return the result as Python string
    object.  Error handling is "strict".  Return NULL if an exception was raised
    by the codec."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, Py_ssize_t, rffi.CCHARP, {int*}], PyObject)
def PyUnicode_DecodeUTF32(space, s, size, errors, byteorder):
    """Decode length bytes from a UTF-32 encoded buffer string and return the
    corresponding Unicode object.  errors (if non-NULL) defines the error
    handling. It defaults to "strict".
    
    If byteorder is non-NULL, the decoder starts decoding using the given byte
    order:
    
    *byteorder == -1: little endian
    *byteorder == 0:  native order
    *byteorder == 1:  big endian
    
    If *byteorder is zero, and the first four bytes of the input data are a
    byte order mark (BOM), the decoder switches to this byte order and the BOM is
    not copied into the resulting Unicode string.  If *byteorder is -1 or
    1, any byte order mark is copied to the output.
    
    After completion, *byteorder is set to the current byte order at the end
    of input data.
    
    In a narrow build codepoints outside the BMP will be decoded as surrogate pairs.
    
    If byteorder is NULL, the codec starts in native order mode.
    
    Return NULL if an exception was raised by the codec.
    """
    raise NotImplementedError

@cpython_api([rffi.CCHARP, Py_ssize_t, rffi.CCHARP, {int*}, Py_ssize_t], PyObject)
def PyUnicode_DecodeUTF32Stateful(space, s, size, errors, byteorder, consumed):
    """If consumed is NULL, behave like PyUnicode_DecodeUTF32(). If
    consumed is not NULL, PyUnicode_DecodeUTF32Stateful() will not treat
    trailing incomplete UTF-32 byte sequences (such as a number of bytes not divisible
    by four) as an error. Those bytes will not be decoded and the number of bytes
    that have been decoded will be stored in consumed.
    """
    raise NotImplementedError

@cpython_api([{const Py_UNICODE*}, Py_ssize_t, rffi.CCHARP, rffi.INT_real], PyObject)
def PyUnicode_EncodeUTF32(space, s, size, errors, byteorder):
    """Return a Python bytes object holding the UTF-32 encoded value of the Unicode
    data in s.  Output is written according to the following byte order:
    
    byteorder == -1: little endian
    byteorder == 0:  native byte order (writes a BOM mark)
    byteorder == 1:  big endian
    
    If byteorder is 0, the output string will always start with the Unicode BOM
    mark (U+FEFF). In the other two modes, no BOM mark is prepended.
    
    If Py_UNICODE_WIDE is not defined, surrogate pairs will be output
    as a single codepoint.
    
    Return NULL if an exception was raised by the codec.
    """
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyUnicode_AsUTF32String(space, unicode):
    """Return a Python string using the UTF-32 encoding in native byte order. The
    string always starts with a BOM mark.  Error handling is "strict".  Return
    NULL if an exception was raised by the codec.
    """
    raise NotImplementedError

@cpython_api([rffi.CCHARP, Py_ssize_t, rffi.CCHARP, {int*}], PyObject)
def PyUnicode_DecodeUTF16(space, s, size, errors, byteorder):
    """Decode length bytes from a UTF-16 encoded buffer string and return the
    corresponding Unicode object.  errors (if non-NULL) defines the error
    handling. It defaults to "strict".
    
    If byteorder is non-NULL, the decoder starts decoding using the given byte
    order:
    
    *byteorder == -1: little endian
    *byteorder == 0:  native order
    *byteorder == 1:  big endian
    
    If *byteorder is zero, and the first two bytes of the input data are a
    byte order mark (BOM), the decoder switches to this byte order and the BOM is
    not copied into the resulting Unicode string.  If *byteorder is -1 or
    1, any byte order mark is copied to the output (where it will result in
    either a \ufeff or a \ufffe character).
    
    After completion, *byteorder is set to the current byte order at the end
    of input data.
    
    If byteorder is NULL, the codec starts in native order mode.
    
    Return NULL if an exception was raised by the codec.
    
    This function used an int type for size. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, Py_ssize_t, rffi.CCHARP, {int*}, Py_ssize_t], PyObject)
def PyUnicode_DecodeUTF16Stateful(space, s, size, errors, byteorder, consumed):
    """If consumed is NULL, behave like PyUnicode_DecodeUTF16(). If
    consumed is not NULL, PyUnicode_DecodeUTF16Stateful() will not treat
    trailing incomplete UTF-16 byte sequences (such as an odd number of bytes or a
    split surrogate pair) as an error. Those bytes will not be decoded and the
    number of bytes that have been decoded will be stored in consumed.
    
    
    
    This function used an int type for size and an int *
    type for consumed. This might require changes in your code for
    properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([{const Py_UNICODE*}, Py_ssize_t, rffi.CCHARP, rffi.INT_real], PyObject)
def PyUnicode_EncodeUTF16(space, s, size, errors, byteorder):
    """Return a Python string object holding the UTF-16 encoded value of the Unicode
    data in s.  Output is written according to the following byte order:
    
    byteorder == -1: little endian
    byteorder == 0:  native byte order (writes a BOM mark)
    byteorder == 1:  big endian
    
    If byteorder is 0, the output string will always start with the Unicode BOM
    mark (U+FEFF). In the other two modes, no BOM mark is prepended.
    
    If Py_UNICODE_WIDE is defined, a single Py_UNICODE value may get
    represented as a surrogate pair. If it is not defined, each Py_UNICODE
    values is interpreted as an UCS-2 character.
    
    Return NULL if an exception was raised by the codec.
    
    This function used an int type for size. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyUnicode_AsUTF16String(space, unicode):
    """Return a Python string using the UTF-16 encoding in native byte order. The
    string always starts with a BOM mark.  Error handling is "strict".  Return
    NULL if an exception was raised by the codec."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, Py_ssize_t, rffi.CCHARP], PyObject)
def PyUnicode_DecodeUnicodeEscape(space, s, size, errors):
    """Create a Unicode object by decoding size bytes of the Unicode-Escape encoded
    string s.  Return NULL if an exception was raised by the codec.
    
    This function used an int type for size. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([{const Py_UNICODE*}, Py_ssize_t], PyObject)
def PyUnicode_EncodeUnicodeEscape(space, s, size):
    """Encode the Py_UNICODE buffer of the given size using Unicode-Escape and
    return a Python string object.  Return NULL if an exception was raised by the
    codec.
    
    This function used an int type for size. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyUnicode_AsUnicodeEscapeString(space, unicode):
    """Encode a Unicode object using Unicode-Escape and return the result as Python
    string object.  Error handling is "strict". Return NULL if an exception was
    raised by the codec."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, Py_ssize_t, rffi.CCHARP], PyObject)
def PyUnicode_DecodeRawUnicodeEscape(space, s, size, errors):
    """Create a Unicode object by decoding size bytes of the Raw-Unicode-Escape
    encoded string s.  Return NULL if an exception was raised by the codec.
    
    This function used an int type for size. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([{const Py_UNICODE*}, Py_ssize_t, rffi.CCHARP], PyObject)
def PyUnicode_EncodeRawUnicodeEscape(space, s, size, errors):
    """Encode the Py_UNICODE buffer of the given size using Raw-Unicode-Escape
    and return a Python string object.  Return NULL if an exception was raised by
    the codec.
    
    This function used an int type for size. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyUnicode_AsRawUnicodeEscapeString(space, unicode):
    """Encode a Unicode object using Raw-Unicode-Escape and return the result as
    Python string object. Error handling is "strict". Return NULL if an exception
    was raised by the codec."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, Py_ssize_t, rffi.CCHARP], PyObject)
def PyUnicode_DecodeLatin1(space, s, size, errors):
    """Create a Unicode object by decoding size bytes of the Latin-1 encoded string
    s.  Return NULL if an exception was raised by the codec.
    
    This function used an int type for size. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([{const Py_UNICODE*}, Py_ssize_t, rffi.CCHARP], PyObject)
def PyUnicode_EncodeLatin1(space, s, size, errors):
    """Encode the Py_UNICODE buffer of the given size using Latin-1 and return
    a Python string object.  Return NULL if an exception was raised by the codec.
    
    This function used an int type for size. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyUnicode_AsLatin1String(space, unicode):
    """Encode a Unicode object using Latin-1 and return the result as Python string
    object.  Error handling is "strict".  Return NULL if an exception was raised
    by the codec."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, Py_ssize_t, rffi.CCHARP], PyObject)
def PyUnicode_DecodeASCII(space, s, size, errors):
    """Create a Unicode object by decoding size bytes of the ASCII encoded string
    s.  Return NULL if an exception was raised by the codec.
    
    This function used an int type for size. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([{const Py_UNICODE*}, Py_ssize_t, rffi.CCHARP], PyObject)
def PyUnicode_EncodeASCII(space, s, size, errors):
    """Encode the Py_UNICODE buffer of the given size using ASCII and return a
    Python string object.  Return NULL if an exception was raised by the codec.
    
    This function used an int type for size. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyUnicode_AsASCIIString(space, unicode):
    """Encode a Unicode object using ASCII and return the result as Python string
    object.  Error handling is "strict".  Return NULL if an exception was raised
    by the codec."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, Py_ssize_t, PyObject, rffi.CCHARP], PyObject)
def PyUnicode_DecodeCharmap(space, s, size, mapping, errors):
    """Create a Unicode object by decoding size bytes of the encoded string s using
    the given mapping object.  Return NULL if an exception was raised by the
    codec. If mapping is NULL latin-1 decoding will be done. Else it can be a
    dictionary mapping byte or a unicode string, which is treated as a lookup table.
    Byte values greater that the length of the string and U+FFFE "characters" are
    treated as "undefined mapping".
    
    Allowed unicode string as mapping argument.
    
    This function used an int type for size. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([{const Py_UNICODE*}, Py_ssize_t, PyObject, rffi.CCHARP], PyObject)
def PyUnicode_EncodeCharmap(space, s, size, mapping, errors):
    """Encode the Py_UNICODE buffer of the given size using the given
    mapping object and return a Python string object. Return NULL if an
    exception was raised by the codec.
    
    This function used an int type for size. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], PyObject)
def PyUnicode_AsCharmapString(space, unicode, mapping):
    """Encode a Unicode object using the given mapping object and return the result
    as Python string object.  Error handling is "strict".  Return NULL if an
    exception was raised by the codec."""
    raise NotImplementedError

@cpython_api([{const Py_UNICODE*}, Py_ssize_t, PyObject, rffi.CCHARP], PyObject)
def PyUnicode_TranslateCharmap(space, s, size, table, errors):
    """Translate a Py_UNICODE buffer of the given length by applying a
    character mapping table to it and return the resulting Unicode object.  Return
    NULL when an exception was raised by the codec.
    
    The mapping table must map Unicode ordinal integers to Unicode ordinal
    integers or None (causing deletion of the character).
    
    Mapping tables need only provide the __getitem__() interface; dictionaries
    and sequences work well.  Unmapped character ordinals (ones which cause a
    LookupError) are left untouched and are copied as-is.
    
    This function used an int type for size. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, Py_ssize_t, rffi.CCHARP], PyObject)
def PyUnicode_DecodeMBCS(space, s, size, errors):
    """Create a Unicode object by decoding size bytes of the MBCS encoded string s.
    Return NULL if an exception was raised by the codec.
    
    This function used an int type for size. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, rffi.INT_real, rffi.CCHARP, {int*}], PyObject)
def PyUnicode_DecodeMBCSStateful(space, s, size, errors, consumed):
    """If consumed is NULL, behave like PyUnicode_DecodeMBCS(). If
    consumed is not NULL, PyUnicode_DecodeMBCSStateful() will not decode
    trailing lead byte and the number of bytes that have been decoded will be stored
    in consumed.
    """
    raise NotImplementedError

@cpython_api([{const Py_UNICODE*}, Py_ssize_t, rffi.CCHARP], PyObject)
def PyUnicode_EncodeMBCS(space, s, size, errors):
    """Encode the Py_UNICODE buffer of the given size using MBCS and return a
    Python string object.  Return NULL if an exception was raised by the codec.
    
    This function used an int type for size. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyUnicode_AsMBCSString(space, unicode):
    """Encode a Unicode object using MBCS and return the result as Python string
    object.  Error handling is "strict".  Return NULL if an exception was raised
    by the codec."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], PyObject)
def PyUnicode_Concat(space, left, right):
    """Concat two strings giving a new Unicode string."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject, Py_ssize_t], PyObject)
def PyUnicode_Split(space, s, sep, maxsplit):
    """Split a string giving a list of Unicode strings.  If sep is NULL, splitting
    will be done at all whitespace substrings.  Otherwise, splits occur at the given
    separator.  At most maxsplit splits will be done.  If negative, no limit is
    set.  Separators are not included in the resulting list.
    
    This function used an int type for maxsplit. This might require
    changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject, rffi.INT_real], PyObject)
def PyUnicode_Splitlines(space, s, keepend):
    """Split a Unicode string at line breaks, returning a list of Unicode strings.
    CRLF is considered to be one line break.  If keepend is 0, the Line break
    characters are not included in the resulting strings."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject, rffi.CCHARP], PyObject)
def PyUnicode_Translate(space, str, table, errors):
    """Translate a string by applying a character mapping table to it and return the
    resulting Unicode object.
    
    The mapping table must map Unicode ordinal integers to Unicode ordinal integers
    or None (causing deletion of the character).
    
    Mapping tables need only provide the __getitem__() interface; dictionaries
    and sequences work well.  Unmapped character ordinals (ones which cause a
    LookupError) are left untouched and are copied as-is.
    
    errors has the usual meaning for codecs. It may be NULL which indicates to
    use the default error handling."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], PyObject)
def PyUnicode_Join(space, separator, seq):
    """Join a sequence of strings using the given separator and return the resulting
    Unicode string."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject, Py_ssize_t, Py_ssize_t, rffi.INT_real], rffi.INT_real)
def PyUnicode_Tailmatch(space, str, substr, start, end, direction):
    """Return 1 if substr matches str*[*start:end] at the given tail end
    (direction == -1 means to do a prefix match, direction == 1 a suffix match),
    0 otherwise. Return -1 if an error occurred.
    
    This function used an int type for start and end. This
    might require changes in your code for properly supporting 64-bit
    systems."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject, Py_ssize_t, Py_ssize_t, rffi.INT_real], Py_ssize_t)
def PyUnicode_Find(space, str, substr, start, end, direction):
    """Return the first position of substr in str*[*start:end] using the given
    direction (direction == 1 means to do a forward search, direction == -1 a
    backward search).  The return value is the index of the first match; a value of
    -1 indicates that no match was found, and -2 indicates that an error
    occurred and an exception has been set.
    
    This function used an int type for start and end. This
    might require changes in your code for properly supporting 64-bit
    systems."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject, Py_ssize_t, Py_ssize_t], Py_ssize_t)
def PyUnicode_Count(space, str, substr, start, end):
    """Return the number of non-overlapping occurrences of substr in
    str[start:end].  Return -1 if an error occurred.
    
    This function returned an int type and used an int
    type for start and end. This might require changes in your code for
    properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject, PyObject, Py_ssize_t], PyObject)
def PyUnicode_Replace(space, str, substr, replstr, maxcount):
    """Replace at most maxcount occurrences of substr in str with replstr and
    return the resulting Unicode object. maxcount == -1 means replace all
    occurrences.
    
    This function used an int type for maxcount. This might
    require changes in your code for properly supporting 64-bit systems."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], rffi.INT_real)
def PyUnicode_Compare(space, left, right):
    """Compare two strings and return -1, 0, 1 for less than, equal, and greater than,
    respectively."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject, rffi.INT_real], rffi.INT_real)
def PyUnicode_RichCompare(space, left, right, op):
    """Rich compare two unicode strings and return one of the following:
    
    NULL in case an exception was raised
    
    Py_True or Py_False for successful comparisons
    
    Py_NotImplemented in case the type combination is unknown
    
    Note that Py_EQ and Py_NE comparisons can cause a
    UnicodeWarning in case the conversion of the arguments to Unicode fails
    with a UnicodeDecodeError.
    
    Possible values for op are Py_GT, Py_GE, Py_EQ,
    Py_NE, Py_LT, and Py_LE."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], PyObject)
def PyUnicode_Format(space, format, args):
    """Return a new string object from format and args; this is analogous to
    format % args.  The args argument must be a tuple."""
    raise NotImplementedError

@cpython_api([PyObject, PyObject], rffi.INT_real)
def PyUnicode_Contains(space, container, element):
    """Check whether element is contained in container and return true or false
    accordingly.
    
    element has to coerce to a one element Unicode string. -1 is returned if
    there was an error."""
    raise NotImplementedError

@cpython_api([rffi.INT_real, {char**}], rffi.INT_real)
def Py_Main(space, argc, argv):
    """The main program for the standard interpreter.  This is made available for
    programs which embed Python.  The argc and argv parameters should be
    prepared exactly as those which are passed to a C program's main()
    function.  It is important to note that the argument list may be modified (but
    the contents of the strings pointed to by the argument list are not). The return
    value will be the integer passed to the sys.exit() function, 1 if the
    interpreter exits due to an exception, or 2 if the parameter list does not
    represent a valid Python command line.
    
    Note that if an otherwise unhandled SystemError is raised, this
    function will not return 1, but exit the process, as long as
    Py_InspectFlag is not set."""
    raise NotImplementedError

@cpython_api([{FILE*}, rffi.CCHARP], rffi.INT_real)
def PyRun_AnyFile(space, fp, filename):
    """This is a simplified interface to PyRun_AnyFileExFlags() below, leaving
    closeit set to 0 and flags set to NULL."""
    raise NotImplementedError

@cpython_api([{FILE*}, rffi.CCHARP, {PyCompilerFlags*}], rffi.INT_real)
def PyRun_AnyFileFlags(space, fp, filename, flags):
    """This is a simplified interface to PyRun_AnyFileExFlags() below, leaving
    the closeit argument set to 0."""
    raise NotImplementedError

@cpython_api([{FILE*}, rffi.CCHARP, rffi.INT_real], rffi.INT_real)
def PyRun_AnyFileEx(space, fp, filename, closeit):
    """This is a simplified interface to PyRun_AnyFileExFlags() below, leaving
    the flags argument set to NULL."""
    raise NotImplementedError

@cpython_api([{FILE*}, rffi.CCHARP, rffi.INT_real, {PyCompilerFlags*}], rffi.INT_real)
def PyRun_AnyFileExFlags(space, fp, filename, closeit, flags):
    """If fp refers to a file associated with an interactive device (console or
    terminal input or Unix pseudo-terminal), return the value of
    PyRun_InteractiveLoop(), otherwise return the result of
    PyRun_SimpleFile().  If filename is NULL, this function uses
    "???" as the filename."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP], rffi.INT_real)
def PyRun_SimpleString(space, command):
    """This is a simplified interface to PyRun_SimpleStringFlags() below,
    leaving the PyCompilerFlags* argument set to NULL."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, {PyCompilerFlags*}], rffi.INT_real)
def PyRun_SimpleStringFlags(space, command, flags):
    """Executes the Python source code from command in the __main__ module
    according to the flags argument. If __main__ does not already exist, it
    is created.  Returns 0 on success or -1 if an exception was raised.  If
    there was an error, there is no way to get the exception information. For the
    meaning of flags, see below.
    
    Note that if an otherwise unhandled SystemError is raised, this
    function will not return -1, but exit the process, as long as
    Py_InspectFlag is not set."""
    raise NotImplementedError

@cpython_api([{FILE*}, rffi.CCHARP], rffi.INT_real)
def PyRun_SimpleFile(space, fp, filename):
    """This is a simplified interface to PyRun_SimpleFileExFlags() below,
    leaving closeit set to 0 and flags set to NULL."""
    raise NotImplementedError

@cpython_api([{FILE*}, rffi.CCHARP, {PyCompilerFlags*}], rffi.INT_real)
def PyRun_SimpleFileFlags(space, fp, filename, flags):
    """This is a simplified interface to PyRun_SimpleFileExFlags() below,
    leaving closeit set to 0."""
    raise NotImplementedError

@cpython_api([{FILE*}, rffi.CCHARP, rffi.INT_real], rffi.INT_real)
def PyRun_SimpleFileEx(space, fp, filename, closeit):
    """This is a simplified interface to PyRun_SimpleFileExFlags() below,
    leaving flags set to NULL."""
    raise NotImplementedError

@cpython_api([{FILE*}, rffi.CCHARP, rffi.INT_real, {PyCompilerFlags*}], rffi.INT_real)
def PyRun_SimpleFileExFlags(space, fp, filename, closeit, flags):
    """Similar to PyRun_SimpleStringFlags(), but the Python source code is read
    from fp instead of an in-memory string. filename should be the name of the
    file.  If closeit is true, the file is closed before PyRun_SimpleFileExFlags
    returns."""
    raise NotImplementedError

@cpython_api([{FILE*}, rffi.CCHARP], rffi.INT_real)
def PyRun_InteractiveOne(space, fp, filename):
    """This is a simplified interface to PyRun_InteractiveOneFlags() below,
    leaving flags set to NULL."""
    raise NotImplementedError

@cpython_api([{FILE*}, rffi.CCHARP, {PyCompilerFlags*}], rffi.INT_real)
def PyRun_InteractiveOneFlags(space, fp, filename, flags):
    """Read and execute a single statement from a file associated with an interactive
    device according to the flags argument.  If filename is NULL, "???" is
    used instead.  The user will be prompted using sys.ps1 and sys.ps2.
    Returns 0 when the input was executed successfully, -1 if there was an
    exception, or an error code from the errcode.h include file distributed
    as part of Python if there was a parse error.  (Note that errcode.h is
    not included by Python.h, so must be included specifically if needed.)"""
    raise NotImplementedError

@cpython_api([{FILE*}, rffi.CCHARP], rffi.INT_real)
def PyRun_InteractiveLoop(space, fp, filename):
    """This is a simplified interface to PyRun_InteractiveLoopFlags() below,
    leaving flags set to NULL."""
    raise NotImplementedError

@cpython_api([{FILE*}, rffi.CCHARP, {PyCompilerFlags*}], rffi.INT_real)
def PyRun_InteractiveLoopFlags(space, fp, filename, flags):
    """Read and execute statements from a file associated with an interactive device
    until EOF is reached.  If filename is NULL, "???" is used instead.  The
    user will be prompted using sys.ps1 and sys.ps2.  Returns 0 at EOF."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, rffi.INT_real], {struct _node*})
def PyParser_SimpleParseString(space, str, start):
    """This is a simplified interface to
    PyParser_SimpleParseStringFlagsFilename() below, leaving  filename set
    to NULL and flags set to 0."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, rffi.INT_real, rffi.INT_real], {struct _node*})
def PyParser_SimpleParseStringFlags(space, str, start, flags):
    """This is a simplified interface to
    PyParser_SimpleParseStringFlagsFilename() below, leaving  filename set
    to NULL."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, rffi.CCHARP, rffi.INT_real, rffi.INT_real], {struct _node*})
def PyParser_SimpleParseStringFlagsFilename(space, str, filename, start, flags):
    """Parse Python source code from str using the start token start according to
    the flags argument.  The result can be used to create a code object which can
    be evaluated efficiently. This is useful if a code fragment must be evaluated
    many times."""
    raise NotImplementedError

@cpython_api([{FILE*}, rffi.CCHARP, rffi.INT_real], {struct _node*})
def PyParser_SimpleParseFile(space, fp, filename, start):
    """This is a simplified interface to PyParser_SimpleParseFileFlags() below,
    leaving flags set to 0"""
    raise NotImplementedError

@cpython_api([{FILE*}, rffi.CCHARP, rffi.INT_real, rffi.INT_real], {struct _node*})
def PyParser_SimpleParseFileFlags(space, fp, filename, start, flags):
    """Similar to PyParser_SimpleParseStringFlagsFilename(), but the Python
    source code is read from fp instead of an in-memory string."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, rffi.INT_real, PyObject, PyObject], PyObject)
def PyRun_String(space, str, start, globals, locals):
    """This is a simplified interface to PyRun_StringFlags() below, leaving
    flags set to NULL."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, rffi.INT_real, PyObject, PyObject, {PyCompilerFlags*}], PyObject)
def PyRun_StringFlags(space, str, start, globals, locals, flags):
    """Execute Python source code from str in the context specified by the
    dictionaries globals and locals with the compiler flags specified by
    flags.  The parameter start specifies the start token that should be used to
    parse the source code.
    
    Returns the result of executing the code as a Python object, or NULL if an
    exception was raised."""
    raise NotImplementedError

@cpython_api([{FILE*}, rffi.CCHARP, rffi.INT_real, PyObject, PyObject], PyObject)
def PyRun_File(space, fp, filename, start, globals, locals):
    """This is a simplified interface to PyRun_FileExFlags() below, leaving
    closeit set to 0 and flags set to NULL."""
    raise NotImplementedError

@cpython_api([{FILE*}, rffi.CCHARP, rffi.INT_real, PyObject, PyObject, rffi.INT_real], PyObject)
def PyRun_FileEx(space, fp, filename, start, globals, locals, closeit):
    """This is a simplified interface to PyRun_FileExFlags() below, leaving
    flags set to NULL."""
    raise NotImplementedError

@cpython_api([{FILE*}, rffi.CCHARP, rffi.INT_real, PyObject, PyObject, {PyCompilerFlags*}], PyObject)
def PyRun_FileFlags(space, fp, filename, start, globals, locals, flags):
    """This is a simplified interface to PyRun_FileExFlags() below, leaving
    closeit set to 0."""
    raise NotImplementedError

@cpython_api([{FILE*}, rffi.CCHARP, rffi.INT_real, PyObject, PyObject, rffi.INT_real, {PyCompilerFlags*}], PyObject)
def PyRun_FileExFlags(space, fp, filename, start, globals, locals, closeit, flags):
    """Similar to PyRun_StringFlags(), but the Python source code is read from
    fp instead of an in-memory string. filename should be the name of the file.
    If closeit is true, the file is closed before PyRun_FileExFlags()
    returns."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, rffi.CCHARP, rffi.INT_real], PyObject)
def Py_CompileString(space, str, filename, start):
    """This is a simplified interface to Py_CompileStringFlags() below, leaving
    flags set to NULL."""
    raise NotImplementedError

@cpython_api([rffi.CCHARP, rffi.CCHARP, rffi.INT_real, {PyCompilerFlags*}], PyObject)
def Py_CompileStringFlags(space, str, filename, start, flags):
    """Parse and compile the Python source code in str, returning the resulting code
    object.  The start token is given by start; this can be used to constrain the
    code which can be compiled and should be Py_eval_input,
    Py_file_input, or Py_single_input.  The filename specified by
    filename is used to construct the code object and may appear in tracebacks or
    SyntaxError exception messages.  This returns NULL if the code cannot
    be parsed or compiled."""
    raise NotImplementedError

@cpython_api([{PyCodeObject*}, PyObject, PyObject], PyObject)
def PyEval_EvalCode(space, co, globals, locals):
    """This is a simplified interface to PyEval_EvalCodeEx(), with just
    the code object, and the dictionaries of global and local variables.
    The other arguments are set to NULL."""
    raise NotImplementedError

@cpython_api([{PyCodeObject*}, PyObject, PyObject, PyObjectP, rffi.INT_real, PyObjectP, rffi.INT_real, PyObjectP, rffi.INT_real, PyObject], PyObject)
def PyEval_EvalCodeEx(space, co, globals, locals, args, argcount, kws, kwcount, defs, defcount, closure):
    """Evaluate a precompiled code object, given a particular environment for its
    evaluation.  This environment consists of dictionaries of global and local
    variables, arrays of arguments, keywords and defaults, and a closure tuple of
    cells."""
    raise NotImplementedError

@cpython_api([{PyFrameObject*}], PyObject)
def PyEval_EvalFrame(space, f):
    """Evaluate an execution frame.  This is a simplified interface to
    PyEval_EvalFrameEx, for backward compatibility."""
    raise NotImplementedError

@cpython_api([{PyFrameObject*}, rffi.INT_real], PyObject)
def PyEval_EvalFrameEx(space, f, throwflag):
    """This is the main, unvarnished function of Python interpretation.  It is
    literally 2000 lines long.  The code object associated with the execution
    frame f is executed, interpreting bytecode and executing calls as needed.
    The additional throwflag parameter can mostly be ignored - if true, then
    it causes an exception to immediately be thrown; this is used for the
    throw() methods of generator objects."""
    raise NotImplementedError

@cpython_api([{PyCompilerFlags*}], rffi.INT_real)
def PyEval_MergeCompilerFlags(space, cf):
    """This function changes the flags of the current evaluation frame, and returns
    true on success, false on failure."""
    raise NotImplementedError

@cpython_api([{ob}], rffi.INT_real)
def PyWeakref_Check(space, ):
    """Return true if ob is either a reference or proxy object.
    """
    raise NotImplementedError

@cpython_api([{ob}], rffi.INT_real)
def PyWeakref_CheckRef(space, ):
    """Return true if ob is a reference object.
    """
    raise NotImplementedError

@cpython_api([{ob}], rffi.INT_real)
def PyWeakref_CheckProxy(space, ):
    """Return true if ob is a proxy object.
    """
    raise NotImplementedError

@cpython_api([PyObject, PyObject], PyObject)
def PyWeakref_NewRef(space, ob, callback):
    """Return a weak reference object for the object ob.  This will always return
    a new reference, but is not guaranteed to create a new object; an existing
    reference object may be returned.  The second parameter, callback, can be a
    callable object that receives notification when ob is garbage collected; it
    should accept a single parameter, which will be the weak reference object
    itself. callback may also be None or NULL.  If ob is not a
    weakly-referencable object, or if callback is not callable, None, or
    NULL, this will return NULL and raise TypeError.
    """
    raise NotImplementedError

@cpython_api([PyObject, PyObject], PyObject)
def PyWeakref_NewProxy(space, ob, callback):
    """Return a weak reference proxy object for the object ob.  This will always
    return a new reference, but is not guaranteed to create a new object; an
    existing proxy object may be returned.  The second parameter, callback, can
    be a callable object that receives notification when ob is garbage
    collected; it should accept a single parameter, which will be the weak
    reference object itself. callback may also be None or NULL.  If ob
    is not a weakly-referencable object, or if callback is not callable,
    None, or NULL, this will return NULL and raise TypeError.
    """
    raise NotImplementedError

@cpython_api([PyObject], PyObject, borrowed=True)
def PyWeakref_GetObject(space, ref):
    """Return the referenced object from a weak reference, ref.  If the referent is
    no longer live, returns None.
    """
    raise NotImplementedError

@cpython_api([PyObject], PyObject, borrowed=True)
def PyWeakref_GET_OBJECT(space, ref):
    """Similar to PyWeakref_GetObject(), but implemented as a macro that does no
    error checking.
    """
    raise NotImplementedError
