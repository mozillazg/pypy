from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import (
    PyObjectFields, generic_cpy_call, CONST_STRING, CANNOT_FAIL, Py_ssize_t,
    cpython_api, bootstrap_function, cpython_struct, build_type_checkers)
from pypy.module.cpyext.pyobject import (
    PyObject, Py_DecRef, get_pyobj_and_xincref, setup_class_for_cpyext)
from pypy.module.cpyext.frameobject import PyFrameObject
from rpython.rlib.unroll import unrolling_iterable
from pypy.interpreter.error import OperationError
from pypy.interpreter.pytraceback import PyTraceback
from pypy.interpreter import pycode


PyTracebackObjectStruct = lltype.ForwardReference()
PyTracebackObject = lltype.Ptr(PyTracebackObjectStruct)
PyTracebackObjectFields = PyObjectFields + (
    ("tb_next", PyTracebackObject),
    ("tb_frame", PyFrameObject),
    ("tb_lasti", rffi.INT),
    ("tb_lineno", rffi.INT),
)
cpython_struct("PyTracebackObject", PyTracebackObjectFields, PyTracebackObjectStruct)

@bootstrap_function
def init_traceback(space):
    setup_class_for_cpyext(
        PyTraceback,
        basestruct=PyTracebackObjectStruct,
        # --from a PyTraceback, this function fills a PyTracebackObject--
        fill_pyobj=traceback_fill_pyobj,
        alloc_pyobj_light=False,
        # --deallocator--
        dealloc=traceback_dealloc,
        )

def traceback_fill_pyobj(space, w_obj, py_traceback):
    traceback = space.interp_w(PyTraceback, w_obj)
    if traceback.next is None:
        w_next_traceback = None
    else:
        w_next_traceback = space.wrap(traceback.next)
    py_traceback.c_tb_next = rffi.cast(PyTracebackObject,
                    get_pyobj_and_xincref(space, w_next_traceback))
    py_traceback.c_tb_frame = rffi.cast(PyFrameObject,
                    get_pyobj_and_xincref(space, space.wrap(traceback.frame)))
    rffi.setintfield(py_traceback, 'c_tb_lasti', traceback.lasti)
    rffi.setintfield(py_traceback, 'c_tb_lineno',traceback.get_lineno())

def traceback_dealloc(space, py_traceback):
    Py_DecRef(space, rffi.cast(PyObject, py_traceback.c_tb_next))
    Py_DecRef(space, rffi.cast(PyObject, py_traceback.c_tb_frame))
    from pypy.module.cpyext.object import PyObject_dealloc
    PyObject_dealloc(space, rffi.cast(PyObject, py_traceback))
