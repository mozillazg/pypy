from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import (
    cpython_api, bootstrap_function, PyObjectFields, cpython_struct,
    CANNOT_FAIL, build_type_checkers, build_type_checkers3)
from pypy.module.cpyext.pyobject import (
    PyObject, Py_DecRef, get_pyobj_and_xincref, from_pyobj, new_pyobj, xincref,
    setup_class_for_cpyext, RRC_PERMANENT)
from pypy.module.cpyext.state import State
from pypy.module.cpyext.pystate import PyThreadState
from pypy.module.cpyext.funcobject import PyCodeObject
from pypy.interpreter.pyframe import PyFrame
from pypy.interpreter.pycode import PyCode
from pypy.interpreter.pytraceback import PyTraceback

PyFrameObjectStruct = lltype.ForwardReference()
PyFrameObject = lltype.Ptr(PyFrameObjectStruct)
PyFrameObjectFields = (PyObjectFields +
    (("f_code", PyCodeObject),
     ("f_globals", PyObject),
     ("f_lineno", rffi.INT),
     ))
cpython_struct("PyFrameObject", PyFrameObjectFields, PyFrameObjectStruct)

_, PyCode_Check = build_type_checkers("Code", PyCode)
_, PyFrame_Check, _PyFrame_Type = build_type_checkers3("Frame", PyFrame)

@bootstrap_function
def init_frameobject(space):
    setup_class_for_cpyext(
        PyFrame,
        basestruct=PyFrameObjectStruct,
        # --from a PyFrame, this function fills a PyFrameObject--
        fill_pyobj=frame_fill_pyobj,
        alloc_pyobj_light=False,
        # --from a PyFrameObject, this function allocs and fills a PyFrame--
        alloc_pypy=frame_alloc_pypy,
        # --deallocator--
        dealloc=frame_dealloc,
        )

def frame_fill_pyobj(space, w_frame, py_frame):
    "Fills a newly allocated PyFrameObject with a frame object"
    frame = space.interp_w(PyFrame, w_frame)
    py_frame.c_f_code = rffi.cast(PyCodeObject,
                                  get_pyobj_and_xincref(space, frame.pycode))
    py_frame.c_f_globals = get_pyobj_and_xincref(space, frame.w_globals)
    rffi.setintfield(py_frame, 'c_f_lineno', frame.getorcreatedebug().f_lineno)

def frame_dealloc(space, py_frame):
    py_code = rffi.cast(PyObject, py_frame.c_f_code)
    Py_DecRef(space, py_code)
    Py_DecRef(space, py_frame.c_f_globals)
    from pypy.module.cpyext.object import PyObject_dealloc
    PyObject_dealloc(space, rffi.cast(PyObject, py_frame))

def frame_alloc_pypy(space, py_obj):
    """
    Creates the frame in the interpreter. The PyFrameObject structure must not
    be modified after this call.
    """
    py_frame = rffi.cast(PyFrameObject, py_obj)
    w_code = from_pyobj(space, py_frame.c_f_code)
    code = space.interp_w(PyCode, w_code)
    w_globals = from_pyobj(space, py_frame.c_f_globals)

    frame = space.FrameClass(space, code, w_globals, outer_func=None)
    d = frame.getorcreatedebug()
    d.f_lineno = rffi.getintfield(py_frame, 'c_f_lineno')
    return frame, RRC_PERMANENT

@cpython_api([PyThreadState, PyCodeObject, PyObject, PyObject], PyFrameObject)
def PyFrame_New(space, tstate, py_code, py_globals, py_locals):
    py_frame = new_pyobj(PyFrameObjectStruct, _PyFrame_Type(space))
    assert PyCode_Check(space, py_code)   # sanity check
    xincref(space, py_code)
    py_frame.c_f_code = rffi.cast(PyCodeObject, py_code)
    xincref(space, py_globals)
    py_frame.c_f_globals = py_globals
    return py_frame

@cpython_api([PyFrameObject], rffi.INT_real, error=-1)
def PyTraceBack_Here(space, w_frame):
    from pypy.interpreter.pytraceback import record_application_traceback
    state = space.fromcache(State)
    if state.operror is None:
        return -1
    frame = space.interp_w(PyFrame, w_frame)
    record_application_traceback(space, state.operror, frame, 0)
    return 0

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyTraceBack_Check(space, w_obj):
    return isinstance(w_obj, PyTraceback)
