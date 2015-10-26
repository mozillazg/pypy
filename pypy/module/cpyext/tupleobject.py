from pypy.interpreter.error import OperationError, oefmt
from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import (cpython_api, Py_ssize_t, CANNOT_FAIL,
    cpython_struct, PyVarObjectFields, build_type_checkers3, bootstrap_function)
from pypy.module.cpyext.pyobject import (PyObject, PyObjectP, Py_DecRef,
    setup_class_for_cpyext, as_pyobj, get_pyobj_and_incref, from_pyobj,
    pyobj_has_w_obj, RRC_PERMANENT, RRC_PERMANENT_LIGHT, new_pyobj, xdecref)
from pypy.module.cpyext.pyerrors import PyErr_BadInternalCall
from pypy.objspace.std.tupleobject import W_TupleObject, W_AbstractTupleObject

PyTupleObjectStruct = lltype.ForwardReference()
PyTupleObject = lltype.Ptr(PyTupleObjectStruct)
PyTupleObjectFields = PyVarObjectFields + \
    (("ob_item", rffi.CArray(PyObject)),)
cpython_struct("PyTupleObject", PyTupleObjectFields, PyTupleObjectStruct)

PyTuple_Check, PyTuple_CheckExact, _PyTuple_Type = build_type_checkers3("Tuple")


@bootstrap_function
def init_intobject(space):
    "Type description of PyTupleObject"
    setup_class_for_cpyext(
        W_AbstractTupleObject,
        basestruct=PyTupleObjectStruct,

        # --from a W_TupleObject, we call this function to allocate and
        #   fill a PyTupleObject --
        alloc_pyobj=tuple_alloc_pyobj,

        # --reverse direction: from a PyTupleObject, we make a W_TupleObject
        #   by instantiating a custom subclass of W_TupleObject--
        realize_subclass_of=W_TupleObject,

        # --and then we call this function to initialize the W_TupleObject--
        fill_pypy=tuple_fill_pypy,

        # --deallocator, *not* called if tuple_alloc_pyobj() made a
        #   PyTupleObject of borrowed items--
        dealloc=tuple_dealloc,
        )

def tuple_alloc_pyobj(space, w_obj):
    """
    Makes a PyTupleObject from a W_AbstractTupleObject.
    """
    assert isinstance(w_obj, W_AbstractTupleObject)
    lst_w = w_obj.tolist()
    ob = lltype.malloc(PyTupleObjectStruct, len(lst_w), flavor='raw',
                       track_allocation=False)
    ob.c_ob_size = len(lst_w)
    if w_obj.cpyext_returned_items_can_be_borrowed:
        for i in range(len(lst_w)):
            ob.c_ob_item[i] = as_pyobj(space, lst_w[i])
        return ob, RRC_PERMANENT_LIGHT
    else:
        for i in range(len(lst_w)):
            ob.c_ob_item[i] = get_pyobj_and_incref(space, lst_w[i])
        return ob, RRC_PERMANENT

class PyTupleObjectWithNullItem(Exception):
    pass

def tuple_fill_pypy(space, w_obj, py_obj):
    """
    Fills in a W_TupleObject from a PyTupleObject.
    """
    py_tuple = rffi.cast(PyTupleObject, py_obj)
    objects_w = []
    for i in range(py_tuple.c_ob_size):
        item = py_tuple.c_ob_item[i]
        if not item:
            raise PyTupleObjectWithNullItem
        objects_w.append(from_pyobj(space, item))
    W_TupleObject.__init__(w_obj, objects_w)

def tuple_dealloc(space, py_tup):
    for i in range(py_tup.c_ob_size):
        xdecref(space, py_tup.c_ob_item[i])
    lltype.free(py_tup, flavor='raw', track_allocation=False)


@cpython_api([Py_ssize_t], PyObject)
def PyTuple_New(space, size):
    py_tuple = new_pyobj(PyTupleObjectStruct, _PyTuple_Type(space), size)
    for i in range(size):
        py_tuple.c_ob_item[i] = lltype.nullptr(PyObject.TO)
    return rffi.cast(PyObject, py_tuple)

@cpython_api([PyObject, Py_ssize_t, PyObject], rffi.INT_real, error=-1)
def PyTuple_SetItem(space, py_t, pos, py_obj):
    if not PyTuple_Check(space, py_t) or py_t.c_ob_refcnt != 1:
        Py_DecRef(space, py_obj)
        PyErr_BadInternalCall(space)
    py_tuple = rffi.cast(PyTupleObject, py_t)
    if pos < 0 or pos >= py_tuple.c_ob_size:
        raise oefmt(space.w_IndexError, "tuple assignment index out of range")

    olditem = py_tuple.c_ob_item[pos]
    py_tuple.c_ob_item[pos] = py_obj

    if olditem:
        Py_DecRef(space, olditem)
    return 0

@cpython_api([PyObject, Py_ssize_t], PyObject, result_borrowed=True)
def PyTuple_GetItem(space, py_t, pos):
    if not PyTuple_Check(space, py_t):
        PyErr_BadInternalCall(space)
    py_tuple = rffi.cast(PyTupleObject, py_t)
    if pos < 0 or pos >= py_tuple.c_ob_size:
        raise oefmt(space.w_IndexError, "tuple assignment index out of range")

    return py_tuple.c_ob_item[pos]     # borrowed

@cpython_api([PyObject], Py_ssize_t, error=-1)
def PyTuple_Size(space, py_t):
    """Take a pointer to a tuple object, and return the size of that tuple."""
    if not PyTuple_Check(space, py_t):
        PyErr_BadInternalCall(space)
    py_tuple = rffi.cast(PyTupleObject, py_t)
    return py_tuple.c_ob_size


@cpython_api([PyObjectP, Py_ssize_t], rffi.INT_real, error=-1)
def _PyTuple_Resize(space, ref, newsize):
    """Can be used to resize a tuple.  newsize will be the new length of the tuple.
    Because tuples are supposed to be immutable, this should only be used if there
    is only one reference to the object.  Do not use this if the tuple may already
    be known to some other part of the code.  The tuple will always grow or shrink
    at the end.  Think of this as destroying the old tuple and creating a new one,
    only more efficiently.  Returns 0 on success. Client code should never
    assume that the resulting value of *p will be the same as before calling
    this function. If the object referenced by *p is replaced, the original
    *p is destroyed.  On failure, returns -1 and sets *p to NULL, and
    raises MemoryError or SystemError."""
    py_t = ref[0]
    if not PyTuple_Check(space, py_t) or py_t.c_ob_refcnt != 1:
        PyErr_BadInternalCall(space)

    py_oldtuple = rffi.cast(PyTupleObject, py_t)
    py_newtuple = rffi.cast(PyTupleObject, PyTuple_New(space, newsize))

    oldsize = py_oldtuple.c_ob_size
    if oldsize > newsize:
        to_copy = newsize
        for i in range(to_copy, oldsize):
            Py_DecRef(space, py_oldtuple.c_ob_item[i])
    else:
        to_copy = oldsize
    for i in range(to_copy):
        py_newtuple.c_ob_item[i] = py_oldtuple.c_ob_item[i]

    ref[0] = rffi.cast(PyObject, py_newtuple)
    Py_DecRef(space, py_oldtuple)
    return 0

@cpython_api([PyObject, Py_ssize_t, Py_ssize_t], PyObject)
def PyTuple_GetSlice(space, w_obj, low, high):
    """Take a slice of the tuple pointed to by p from low to high and return it
    as a new tuple.
    """
    return space.getslice(w_obj, space.wrap(low), space.wrap(high))
