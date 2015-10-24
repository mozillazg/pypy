from rpython.rlib.buffer import StringBuffer, SubBuffer
from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.interpreter.error import OperationError
from pypy.module.cpyext.api import (
    cpython_api, Py_ssize_t, cpython_struct, bootstrap_function,
    PyObjectFields, PyObject)
from pypy.module.cpyext.pyobject import (
    setup_class_for_cpyext, RRC_PERMANENT, get_pyobj_and_xincref, xdecref)
from pypy.module.cpyext import support
from pypy.module.array.interp_array import ArrayBuffer
from pypy.objspace.std.bufferobject import W_Buffer


PyBufferObjectStruct = lltype.ForwardReference()
PyBufferObject = lltype.Ptr(PyBufferObjectStruct)
PyBufferObjectFields = PyObjectFields + (
    ("b_base", PyObject),
    ("b_ptr", rffi.VOIDP),
    ("b_size", Py_ssize_t),
    ("b_offset", Py_ssize_t),
    ("b_readonly", rffi.INT),
    ("b_hash", rffi.LONG),
    ("_b_data_pypy", rffi.CArray(lltype.Char)),
    )

cpython_struct("PyBufferObject", PyBufferObjectFields, PyBufferObjectStruct)

@bootstrap_function
def init_bufferobject(space):
    "Type description of PyBufferObject"
    setup_class_for_cpyext(
        W_Buffer,
        basestruct=PyBufferObjectStruct,

        # --from a W_Buffer, we call this function to create and fill a
        #   new PyBufferObject --
        alloc_pyobj=buffer_alloc_pyobj,

        # --deallocator--
        dealloc=buffer_dealloc,
        )

def buffer_alloc_pyobj(space, w_obj):
    """
    Fills a newly allocated PyBufferObject with the given W_Buffer object.
    """

    assert isinstance(w_obj, W_Buffer)
    buf = w_obj.buf

    # If buf already allocated a fixed buffer, use it, and keep a
    # reference to buf.
    # Otherwise, b_base stays NULL, and the b_ptr points inside the
    # allocated object.

    try:
        ptr = buf.get_raw_address()
    except ValueError:
        srcstring = buf.as_str()
        size = len(srcstring)
        w_base = None
        ptr = lltype.nullptr(rffi.VOIDP.TO)
    else:
        srcstring = ''
        if isinstance(buf, ArrayBuffer):
            w_base = buf.array
        else:
            w_base = w_obj
        size = buf.getlength()
        ptr = rffi.cast(rffi.VOIDP, ptr)

    py_buf = lltype.malloc(PyBufferObjectStruct, len(srcstring), flavor='raw',
                           track_allocation=False)
    py_buf.c_b_base = get_pyobj_and_xincref(space, w_base)

    if w_base is None:
        ptr = py_buf.c__b_data_pypy
        rffi.str2rawmem(srcstring, ptr, 0, size)
        ptr = rffi.cast(rffi.VOIDP, ptr)
    py_buf.c_b_ptr = ptr
    py_buf.c_b_size = size
    if isinstance(buf, SubBuffer):
        py_buf.c_b_offset = buf.offset
    else:
        py_buf.c_b_offset = 0
    rffi.setintfield(py_buf, 'c_b_readonly', 1)
    rffi.setintfield(py_buf, 'c_b_hash', -1)

    return py_buf, RRC_PERMANENT


def buffer_dealloc(space, py_buf):
    xdecref(space, py_buf.c_b_base)
    lltype.free(py_buf, flavor='raw', track_allocation=False)
