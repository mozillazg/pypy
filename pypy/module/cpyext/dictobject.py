from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import cpython_api, CANNOT_FAIL, build_type_checkers,\
        Py_ssize_t, PyObjectP, CONST_STRING
from pypy.module.cpyext.pyobject import PyObject, register_container
from pypy.module.cpyext.pyerrors import PyErr_BadInternalCall
from pypy.interpreter.error import OperationError

@cpython_api([], PyObject)
def PyDict_New(space):
    return space.newdict()

PyDict_Check, PyDict_CheckExact = build_type_checkers("Dict")

@cpython_api([PyObject, PyObject], PyObject)
def PyDict_GetItem(space, w_dict, w_key):
    if PyDict_Check(space, w_dict):
        return space.getitem(w_dict, w_key)
    else:
        PyErr_BadInternalCall(space)

@cpython_api([PyObject, PyObject, PyObject], rffi.INT_real, error=-1)
def PyDict_SetItem(space, w_dict, w_key, w_obj):
    if PyDict_Check(space, w_dict):
        space.setitem(w_dict, w_key, w_obj)
        return 0
    else:
        PyErr_BadInternalCall(space)

@cpython_api([PyObject, PyObject], rffi.INT_real, error=-1)
def PyDict_DelItem(space, w_dict, w_key):
    if PyDict_Check(space, w_dict):
        space.delitem(w_dict, w_key)
        return 0
    else:
        PyErr_BadInternalCall(space)

@cpython_api([PyObject, CONST_STRING, PyObject], rffi.INT_real, error=-1)
def PyDict_SetItemString(space, w_dict, key_ptr, w_obj):
    if PyDict_Check(space, w_dict):
        key = rffi.charp2str(key_ptr)
        # our dicts dont have a standardized interface, so we need
        # to go through the space
        space.setitem(w_dict, space.wrap(key), w_obj)
        return 0
    else:
        PyErr_BadInternalCall(space)

@cpython_api([PyObject, CONST_STRING], PyObject, borrowed=True)
def PyDict_GetItemString(space, w_dict, key):
    """This is the same as PyDict_GetItem(), but key is specified as a
    char*, rather than a PyObject*."""
    if not PyDict_Check(space, w_dict):
        PyErr_BadInternalCall(space)
    w_res = space.finditem_str(w_dict, rffi.charp2str(key))
    if w_res is None:
        raise OperationError(space.w_KeyError, space.wrap("Key not found"))
    register_container(space, w_dict)
    return w_res

@cpython_api([PyObject], Py_ssize_t, error=-1)
def PyDict_Size(space, w_obj):
    """
    Return the number of items in the dictionary.  This is equivalent to
    len(p) on a dictionary."""
    return space.int_w(space.len(w_obj))

@cpython_api([PyObject, Py_ssize_t, PyObjectP, PyObjectP], rffi.INT_real, error=CANNOT_FAIL)
def PyDict_Next(space, w_obj, ppos, pkey, pvalue):
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
    }"""
    if w_obj is None:
        return 0
    raise NotImplementedError


