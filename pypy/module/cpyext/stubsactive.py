from pypy.module.cpyext.pyobject import PyObject
from pypy.module.cpyext.api import cpython_api, Py_ssize_t, CANNOT_FAIL
from pypy.rpython.lltypesystem import rffi, lltype

@cpython_api([PyObject], rffi.VOIDP, error=CANNOT_FAIL) #XXX
def PyFile_AsFile(space, p):
    """Return the file object associated with p as a FILE*.
    
    If the caller will ever use the returned FILE* object while
    the GIL is released it must also call the PyFile_IncUseCount() and
    PyFile_DecUseCount() functions described below as appropriate."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyObject_GetIter(space, o):
    """This is equivalent to the Python expression iter(o). It returns a new
    iterator for the object argument, or the object  itself if the object is already
    an iterator.  Raises TypeError and returns NULL if the object cannot be
    iterated."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyIter_Next(space, o):
    """Return the next value from the iteration o.  If the object is an iterator,
    this retrieves the next value from the iteration, and returns NULL with no
    exception set if there are no remaining items.  If the object is not an
    iterator, TypeError is raised, or if there is an error in retrieving the
    item, returns NULL and passes along the exception."""
    raise NotImplementedError

@cpython_api([rffi.ULONG], PyObject)
def PyLong_FromUnsignedLong(space, v):
    """Return a new PyLongObject object from a C unsigned long, or
    NULL on failure."""
    raise NotImplementedError

FILE = rffi.VOIDP_real.TO
FILEP = lltype.Ptr(FILE)
@cpython_api([PyObject, FILEP, rffi.INT_real], rffi.INT_real, error=-1)
def PyObject_Print(space, o, fp, flags):
    """Print an object o, on file fp.  Returns -1 on error.  The flags argument
    is used to enable certain printing options.  The only option currently supported
    is Py_PRINT_RAW; if given, the str() of the object is written
    instead of the repr()."""
    raise NotImplementedError

