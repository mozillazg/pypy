from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rpython.lltypesystem.lltype import Ptr, FuncType, Void
from pypy.module.cpyext.api import cpython_api, cpython_api_c, cpython_struct, \
    PyObject, PyVarObjectFields, Py_ssize_t, Py_TPFLAGS_READYING, \
    Py_TPFLAGS_READY, Py_TPFLAGS_HEAPTYPE, make_ref, \
    PyStringObject, ADDR, from_ref
from pypy.module.cpyext.modsupport import PyMethodDef


PyTypeObject = lltype.ForwardReference()
PyTypeObjectPtr = lltype.Ptr(PyTypeObject)
PyCFunction = Ptr(FuncType([PyObject, PyObject], PyObject))
P, FT, PyO = Ptr, FuncType, PyObject
PyOPtr = Ptr(lltype.Array(PyO, hints={'nolength': True}))


# XXX
PyBufferProcs = PyMemberDef = rffi.VOIDP.TO

freefunc = P(FT([rffi.VOIDP_real], Void))
destructor = P(FT([PyO], Void))
printfunc = P(FT([PyO, rffi.VOIDP_real, rffi.INT_real], rffi.INT))
getattrfunc = P(FT([PyO, rffi.CCHARP], PyO))
getattrofunc = P(FT([PyO, PyO], PyO))
setattrfunc = P(FT([PyO, rffi.CCHARP, PyO], rffi.INT_real))
setattrofunc = P(FT([PyO, PyO, PyO], rffi.INT_real))
cmpfunc = P(FT([PyO, PyO], rffi.INT_real))
reprfunc = P(FT([PyO], PyO))
hashfunc = P(FT([PyO], lltype.Signed))
richcmpfunc = P(FT([PyO, PyO, rffi.INT_real], PyO))
getiterfunc = P(FT([PyO], PyO))
iternextfunc = P(FT([PyO], PyO))
descrgetfunc = P(FT([PyO, PyO, PyO], PyO))
descrsetfunc = P(FT([PyO, PyO, PyO], rffi.INT_real))
initproc = P(FT([PyO, PyO, PyO], rffi.INT_real))
newfunc = P(FT([PyTypeObjectPtr, PyO, PyO], PyO))
allocfunc = P(FT([PyTypeObjectPtr, Py_ssize_t], PyO))
unaryfunc = P(FT([PyO], PyO))
binaryfunc = P(FT([PyO, PyO], PyO))
ternaryfunc = P(FT([PyO, PyO, PyO], PyO))
inquiry = P(FT([PyO], rffi.INT_real))
lenfunc = P(FT([PyO], Py_ssize_t))
coercion = P(FT([PyOPtr, PyOPtr], rffi.INT_real))
intargfunc = P(FT([PyO, rffi.INT_real], PyO))
intintargfunc = P(FT([PyO, rffi.INT_real, rffi.INT], PyO))
ssizeargfunc = P(FT([PyO, Py_ssize_t], PyO))
ssizessizeargfunc = P(FT([PyO, Py_ssize_t, Py_ssize_t], PyO))
intobjargproc = P(FT([PyO, rffi.INT_real, PyO], rffi.INT))
intintobjargproc = P(FT([PyO, rffi.INT_real, rffi.INT, PyO], rffi.INT))
ssizeobjargproc = P(FT([PyO, Py_ssize_t, PyO], rffi.INT_real))
ssizessizeobjargproc = P(FT([PyO, Py_ssize_t, Py_ssize_t, PyO], rffi.INT_real))
objobjargproc = P(FT([PyO, PyO, PyO], rffi.INT_real))

objobjproc = P(FT([PyO, PyO], rffi.INT_real))
visitproc = P(FT([PyO, rffi.VOIDP_real], rffi.INT_real))
traverseproc = P(FT([PyO, visitproc, rffi.VOIDP_real], rffi.INT_real))

getter = P(FT([PyO, rffi.VOIDP_real], PyO))
setter = P(FT([PyO, PyO, rffi.VOIDP_real], rffi.INT_real))

wrapperfunc = P(FT([PyO, PyO, rffi.VOIDP_real], PyO))
wrapperfunc_kwds = P(FT([PyO, PyO, rffi.VOIDP_real, PyO], PyO))


PyGetSetDef = cpython_struct("PyGetSetDef", (
	("name", rffi.CCHARP),
    ("get", getter),
    ("set", setter),
    ("doc", rffi.CCHARP),
    ("closure", rffi.VOIDP_real),
))

PyNumberMethods = cpython_struct("PyNumberMethods", (
    ("nb_add", binaryfunc),
    ("nb_subtract", binaryfunc),
    ("nb_multiply", binaryfunc),
    ("nb_divide", binaryfunc),
    ("nb_remainder", binaryfunc),
    ("nb_divmod", binaryfunc),
    ("nb_power", ternaryfunc),
    ("nb_negative", unaryfunc),
    ("nb_positive", unaryfunc),
    ("nb_absolute", unaryfunc),
    ("nb_nonzero", inquiry),
    ("nb_invert", unaryfunc),
    ("nb_lshift", binaryfunc),
    ("nb_rshift", binaryfunc),
    ("nb_and", binaryfunc),
    ("nb_xor", binaryfunc),
    ("nb_or", binaryfunc),
    ("nb_coerce", coercion),
    ("nb_int", unaryfunc),
    ("nb_long", unaryfunc),
    ("nb_float", unaryfunc),
    ("nb_oct", unaryfunc),
    ("nb_hex", unaryfunc),
    ("nb_inplace_add", binaryfunc),
    ("nb_inplace_subtract", binaryfunc),
    ("nb_inplace_multiply", binaryfunc),
    ("nb_inplace_divide", binaryfunc),
    ("nb_inplace_remainder", binaryfunc),
    ("nb_inplace_power", ternaryfunc),
    ("nb_inplace_lshift", binaryfunc),
    ("nb_inplace_rshift", binaryfunc),
    ("nb_inplace_and", binaryfunc),
    ("nb_inplace_xor", binaryfunc),
    ("nb_inplace_or", binaryfunc),

    ("nb_floor_divide", binaryfunc),
    ("nb_true_divide", binaryfunc),
    ("nb_inplace_floor_divide", binaryfunc),
    ("nb_inplace_true_divide", binaryfunc),

    ("nb_index", unaryfunc),
))

PySequenceMethods = cpython_struct("PySequenceMethods", (
    ("sq_length", lenfunc),
    ("sq_concat", binaryfunc),
    ("sq_repeat", ssizeargfunc),
    ("sq_item", ssizeargfunc),
    ("sq_slice", ssizessizeargfunc),
    ("sq_ass_item", ssizeobjargproc),
    ("sq_ass_slice", ssizessizeobjargproc),
    ("sq_contains", objobjproc),
    ("sq_inplace_concat", binaryfunc),
    ("sq_inplace_repeat", ssizeargfunc),
))

PyMappingMethods = cpython_struct("PyMappingMethods", (
    ("mp_length", lenfunc),
    ("mp_subscript", binaryfunc),
    ("mp_ass_subscript", objobjargproc),
))

"""
PyBufferProcs = cpython_struct("PyBufferProcs", (
    ("bf_getreadbuffer", readbufferproc),
    ("bf_getwritebuffer", writebufferproc),
    ("bf_getsegcount", segcountproc),
    ("bf_getcharbuffer", charbufferproc),
    ("bf_getbuffer", getbufferproc),
    ("bf_releasebuffer", releasebufferproc),
))
"""

PyTypeObjectFields = []
PyTypeObjectFields.extend(PyVarObjectFields)
PyTypeObjectFields.extend([
    ("tp_name", rffi.CCHARP), # For printing, in format "<module>.<name>"
    ("tp_basicsize", Py_ssize_t), ("tp_itemsize", Py_ssize_t), # For allocation

    # Methods to implement standard operations
    ("tp_dealloc", destructor),
    ("tp_print", printfunc),
    ("tp_getattr", getattrfunc),
    ("tp_setattr", setattrfunc),
    ("tp_compare", cmpfunc),
    ("tp_repr", reprfunc),

    # Method suites for standard classes
    ("tp_as_number", Ptr(PyNumberMethods)),
    ("tp_as_sequence", Ptr(PySequenceMethods)),
    ("tp_as_mapping", Ptr(PyMappingMethods)),

    # More standard operations (here for binary compatibility)
    ("tp_hash", hashfunc),
    ("tp_call", ternaryfunc),
    ("tp_str", reprfunc),
    ("tp_getattro", getattrofunc),
    ("tp_setattro", setattrofunc),

    # Functions to access object as input/output buffer
    ("tp_as_buffer", Ptr(PyBufferProcs)),

    # Flags to define presence of optional/expanded features
    ("tp_flags", lltype.Signed),

    ("tp_doc", rffi.CCHARP), # Documentation string

    # Assigned meaning in release 2.0
    # call function for all accessible objects
    ("tp_traverse", traverseproc),

    # delete references to contained objects
    ("tp_clear", inquiry),

    # Assigned meaning in release 2.1
    # rich comparisons 
    ("tp_richcompare", richcmpfunc),

    # weak reference enabler
    ("tp_weaklistoffset", Py_ssize_t),

    # Added in release 2.2
    # Iterators
    ("tp_iter", getiterfunc),
    ("tp_iternext", iternextfunc),

    # Attribute descriptor and subclassing stuff
    ("tp_methods", Ptr(PyMethodDef)),
    ("tp_members", Ptr(PyMemberDef)),
    ("tp_getset", Ptr(PyGetSetDef)),
    ("tp_base", Ptr(PyTypeObject)),
    ("tp_dict", PyObject),
    ("tp_descr_get", descrgetfunc),
    ("tp_descr_set", descrsetfunc),
    ("tp_dictoffset", Py_ssize_t),  # can be ignored in PyPy
    ("tp_init", initproc),
    ("tp_alloc", allocfunc),
    ("tp_new", newfunc),
    ("tp_free", freefunc), # Low-level free-memory routine
    ("tp_is_gc", inquiry), # For PyObject_IS_GC
    ("tp_bases", PyObject),
    ("tp_mro", PyObject), # method resolution order
    ("tp_cache", PyObject),
    ("tp_subclasses", PyObject),
    ("tp_weaklist", PyObject),
    ("tp_del", destructor),
    ])
cpython_struct("PyTypeObject", PyTypeObjectFields, PyTypeObject)


