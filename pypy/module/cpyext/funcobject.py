from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import (
    PyObjectFields, generic_cpy_call,
    cpython_api, bootstrap_function, cpython_struct, build_type_checkers)
from pypy.module.cpyext.pyobject import PyObject, make_ref, from_ref, Py_DecRef, make_typedescr
from pypy.interpreter.function import Function, Method

PyFunctionObjectStruct = lltype.ForwardReference()
PyFunctionObject = lltype.Ptr(PyFunctionObjectStruct)
PyFunctionObjectFields = PyObjectFields + \
    (("func_name", PyObject),)
cpython_struct("PyFunctionObject", PyFunctionObjectFields, PyFunctionObjectStruct)

@bootstrap_function
def init_functionobject(space):
    make_typedescr(Function.typedef,
                   basestruct=PyFunctionObject.TO,
                   attach=function_attach,
                   dealloc=function_dealloc)

PyFunction_Check, PyFunction_CheckExact = build_type_checkers("Function", Function)
PyMethod_Check, PyMethod_CheckExact = build_type_checkers("Method", Method)

def function_attach(space, py_obj, w_obj):
    py_func = rffi.cast(PyFunctionObject, py_obj)
    assert isinstance(w_obj, Function)
    py_func.c_func_name = make_ref(space, space.wrap(w_obj.name))

@cpython_api([PyObject], lltype.Void, external=False)
def function_dealloc(space, py_obj):
    py_func = rffi.cast(PyFunctionObject, py_obj)
    Py_DecRef(space, py_func.c_func_name)
    # standard dealloc
    pto = py_obj.c_ob_type
    obj_voidp = rffi.cast(rffi.VOIDP_real, py_obj)
    generic_cpy_call(space, pto.c_tp_free, obj_voidp)
    pto = rffi.cast(PyObject, pto)
    Py_DecRef(space, pto)

@cpython_api([PyObject], PyObject, borrowed=True)
def PyMethod_Function(space, w_method):
    """Return the function object associated with the method meth."""
    assert isinstance(w_method, Method)
    return w_method.w_function

@cpython_api([PyObject], PyObject, borrowed=True)
def PyMethod_Class(space, w_method):
    """Return the class object from which the method meth was created; if this was
    created from an instance, it will be the class of the instance."""
    assert isinstance(w_method, Method)
    return w_method.w_class

