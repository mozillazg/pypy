from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import (
    cpython_api, cpython_struct, bootstrap_function, build_type_checkers,
    CANNOT_FAIL, Py_ssize_t, Py_ssize_tP, PyObjectFields)
from pypy.module.cpyext.pyobject import (
    PyObject, setup_class_for_cpyext, get_pyobj_and_incref, decref)
from pypy.module.cpyext.pyerrors import PyErr_BadInternalCall
from pypy.interpreter.error import OperationError
from pypy.objspace.std.sliceobject import W_SliceObject

# Slice objects directly expose their members as PyObject.
# Don't change them!

PySliceObjectStruct = lltype.ForwardReference()
PySliceObject = lltype.Ptr(PySliceObjectStruct)
PySliceObjectFields = PyObjectFields + \
    (("start", PyObject), ("step", PyObject), ("stop", PyObject), )
cpython_struct("PySliceObject", PySliceObjectFields, PySliceObjectStruct)

@bootstrap_function
def init_sliceobject(space):
    "Type description of PySliceObject"
    setup_class_for_cpyext(
        W_SliceObject,
        basestruct=PySliceObjectStruct,
        # --from a W_SliceObject, this function fills a PySliceObject--
        fill_pyobj=slice_fill_pyobj,
        alloc_pyobj_light=False,
        # --deallocator--
        dealloc=slice_dealloc,
        )

def slice_fill_pyobj(space, w_slice, py_slice):
    """
    Fills a newly allocated PySliceObject with the given slice object. The
    fields must not be modified.
    """
    assert isinstance(w_slice, W_SliceObject)
    py_slice.c_start = get_pyobj_and_incref(space, w_slice.w_start)
    py_slice.c_stop = get_pyobj_and_incref(space, w_slice.w_stop)
    py_slice.c_step = get_pyobj_and_incref(space, w_slice.w_step)

def slice_dealloc(space, py_slice):
    """Frees allocated PySliceObject resources.
    """
    decref(space, py_slice.c_start)
    decref(space, py_slice.c_stop)
    decref(space, py_slice.c_step)
    from pypy.module.cpyext.object import PyObject_dealloc
    PyObject_dealloc(space, rffi.cast(PyObject, py_slice))

PySlice_Check, PySlice_CheckExact = build_type_checkers("Slice")

@cpython_api([PyObject, PyObject, PyObject], PyObject)
def PySlice_New(space, w_start, w_stop, w_step):
    """Return a new slice object with the given values.  The start, stop, and
    step parameters are used as the values of the slice object attributes of
    the same names.  Any of the values may be NULL, in which case the
    None will be used for the corresponding attribute.  Return NULL if
    the new object could not be allocated."""
    if w_start is None:
        w_start = space.w_None
    if w_stop is None:
        w_stop = space.w_None
    if w_step is None:
        w_step = space.w_None
    return W_SliceObject(w_start, w_stop, w_step)

@cpython_api([PySliceObject, Py_ssize_t, Py_ssize_tP, Py_ssize_tP, Py_ssize_tP,
                Py_ssize_tP], rffi.INT_real, error=-1)
def PySlice_GetIndicesEx(space, w_slice, length, start_p, stop_p, step_p,
                         slicelength_p):
    """Usable replacement for PySlice_GetIndices().  Retrieve the start,
    stop, and step indices from the slice object slice assuming a sequence of
    length length, and store the length of the slice in slicelength.  Out
    of bounds indices are clipped in a manner consistent with the handling of
    normal slices.
    
    Returns 0 on success and -1 on error with exception set."""
    if not PySlice_Check(space, w_slice):
        PyErr_BadInternalCall(space)
    assert isinstance(w_slice, W_SliceObject)
    start_p[0], stop_p[0], step_p[0], slicelength_p[0] = \
            w_slice.indices4(space, length)
    return 0

@cpython_api([PySliceObject, Py_ssize_t, Py_ssize_tP, Py_ssize_tP, Py_ssize_tP],
                rffi.INT_real, error=-1)
def PySlice_GetIndices(space, w_slice, length, start_p, stop_p, step_p):
    """Retrieve the start, stop and step indices from the slice object slice,
    assuming a sequence of length length. Treats indices greater than
    length as errors.
    
    Returns 0 on success and -1 on error with no exception set (unless one of
    the indices was not None and failed to be converted to an integer,
    in which case -1 is returned with an exception set).
    
    You probably do not want to use this function.  If you want to use slice
    objects in versions of Python prior to 2.3, you would probably do well to
    incorporate the source of PySlice_GetIndicesEx(), suitably renamed,
    in the source of your extension."""
    if not PySlice_Check(space, w_slice):
        PyErr_BadInternalCall(space)
    assert isinstance(w_slice, W_SliceObject)
    start_p[0], stop_p[0], step_p[0] = \
            w_slice.indices3(space, length)
    return 0
