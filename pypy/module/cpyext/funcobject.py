from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import (
    PyObjectFields, generic_cpy_call, CONST_STRING, CANNOT_FAIL, Py_ssize_t,
    cpython_api, bootstrap_function, cpython_struct, build_type_checkers)
from pypy.module.cpyext.pyobject import (
    PyObject, Py_DecRef, setup_class_for_cpyext, as_pyobj, as_xpyobj,
    get_pyobj_and_incref)
from rpython.rlib.unroll import unrolling_iterable
from pypy.interpreter.error import OperationError
from pypy.interpreter.function import Function, Method
from pypy.interpreter.pycode import PyCode
from pypy.interpreter import pycode

CODE_FLAGS = dict(
    CO_OPTIMIZED   = 0x0001,
    CO_NEWLOCALS   = 0x0002,
    CO_VARARGS     = 0x0004,
    CO_VARKEYWORDS = 0x0008,
    CO_NESTED      = 0x0010,
    CO_GENERATOR   = 0x0020,
)
ALL_CODE_FLAGS = unrolling_iterable(CODE_FLAGS.items())

PyFunctionObjectStruct = lltype.ForwardReference()
PyFunctionObject = lltype.Ptr(PyFunctionObjectStruct)
PyFunctionObjectFields = PyObjectFields + \
    (("func_name", PyObject),)
cpython_struct("PyFunctionObject", PyFunctionObjectFields, PyFunctionObjectStruct)

PyCodeObjectStruct = lltype.ForwardReference()
PyCodeObject = lltype.Ptr(PyCodeObjectStruct)
PyCodeObjectFields = PyObjectFields + \
    (("co_name", PyObject),
     ("co_flags", rffi.INT),
     ("co_argcount", rffi.INT),
    )
cpython_struct("PyCodeObject", PyCodeObjectFields, PyCodeObjectStruct)

@bootstrap_function
def init_functionobject(space):
    setup_class_for_cpyext(
        Function,
        basestruct=PyFunctionObjectStruct,
        # --from a (W_)Function, this function fills a PyFunctionObject--
        fill_pyobj=function_fill_pyobj,
        alloc_pyobj_light=False,
        # --deallocator--
        dealloc=function_dealloc,
        )
    setup_class_for_cpyext(
        PyCode,
        basestruct=PyCodeObjectStruct,
        # --from a PyCode, this function fills a PyCodeObject--
        fill_pyobj=code_fill_pyobj,
        alloc_pyobj_light=False,
        # --deallocator--
        dealloc=code_dealloc,
        )

PyFunction_Check, PyFunction_CheckExact = build_type_checkers("Function", Function)
PyMethod_Check, PyMethod_CheckExact = build_type_checkers("Method", Method)

def function_fill_pyobj(space, w_func, py_func):
    func = space.interp_w(Function, w_func)
    py_func.c_func_name = get_pyobj_and_incref(space, space.wrap(func.name))

def function_dealloc(space, py_func):
    Py_DecRef(space, py_func.c_func_name)
    from pypy.module.cpyext.object import PyObject_dealloc
    PyObject_dealloc(space, rffi.cast(PyObject, py_func))

def code_fill_pyobj(space, w_code, py_code):
    code = space.interp_w(PyCode, w_code)
    py_code.c_co_name = get_pyobj_and_incref(space, space.wrap(code.co_name))
    co_flags = 0
    for name, value in ALL_CODE_FLAGS:
        if code.co_flags & getattr(pycode, name):
            co_flags |= value
    rffi.setintfield(py_code, 'c_co_flags', co_flags)
    rffi.setintfield(py_code, 'c_co_argcount', code.co_argcount)

def code_dealloc(space, py_code):
    Py_DecRef(space, py_code.c_co_name)
    from pypy.module.cpyext.object import PyObject_dealloc
    PyObject_dealloc(space, rffi.cast(PyObject, py_code))

@cpython_api([PyObject], PyObject)
def PyFunction_GetCode(space, w_func):
    """Return the code object associated with the function object op."""
    func = space.interp_w(Function, w_func)
    return as_pyobj(space, func.code)      # borrowed

@cpython_api([PyObject, PyObject, PyObject], PyObject)
def PyMethod_New(space, w_func, w_self, w_cls):
    """Return a new method object, with func being any callable object; this is the
    function that will be called when the method is called.  If this method should
    be bound to an instance, self should be the instance and class should be the
    class of self, otherwise self should be NULL and class should be the
    class which provides the unbound method."""
    return Method(space, w_func, w_self, w_cls)

@cpython_api([PyObject], PyObject)
def PyMethod_Function(space, w_method):
    """Return the function object associated with the method meth."""
    assert isinstance(w_method, Method)
    return as_pyobj(space, w_method.w_function)   # borrowed

@cpython_api([PyObject], PyObject)
def PyMethod_Self(space, w_method):
    """Return the instance associated with the method meth if it is bound,
    otherwise return NULL."""
    assert isinstance(w_method, Method)
    return as_xpyobj(space, w_method.w_instance)   # borrowed

@cpython_api([PyObject], PyObject)
def PyMethod_Class(space, w_method):
    """Return the class object from which the method meth was created; if this was
    created from an instance, it will be the class of the instance."""
    assert isinstance(w_method, Method)
    return as_pyobj(space, w_method.w_class)    # borrowed

def unwrap_list_of_strings(space, w_list):
    return [space.str_w(w_item) for w_item in space.fixedview(w_list)]

@cpython_api([rffi.INT_real, rffi.INT_real, rffi.INT_real, rffi.INT_real,
              PyObject, PyObject, PyObject, PyObject, PyObject, PyObject,
              PyObject, PyObject, rffi.INT_real, PyObject], PyCodeObject)
def PyCode_New(space, argcount, nlocals, stacksize, flags,
               w_code, w_consts, w_names, w_varnames, w_freevars, w_cellvars,
               w_filename, w_funcname, firstlineno, w_lnotab):
    """Return a new code object.  If you need a dummy code object to
    create a frame, use PyCode_NewEmpty() instead.  Calling
    PyCode_New() directly can bind you to a precise Python
    version since the definition of the bytecode changes often."""
    return space.wrap(PyCode(space,
                             argcount=rffi.cast(lltype.Signed, argcount),
                             nlocals=rffi.cast(lltype.Signed, nlocals),
                             stacksize=rffi.cast(lltype.Signed, stacksize),
                             flags=rffi.cast(lltype.Signed, flags),
                             code=space.str_w(w_code),
                             consts=space.fixedview(w_consts),
                             names=unwrap_list_of_strings(space, w_names),
                             varnames=unwrap_list_of_strings(space, w_varnames),
                             filename=space.str_w(w_filename),
                             name=space.str_w(w_funcname),
                             firstlineno=rffi.cast(lltype.Signed, firstlineno),
                             lnotab=space.str_w(w_lnotab),
                             freevars=unwrap_list_of_strings(space, w_freevars),
                             cellvars=unwrap_list_of_strings(space, w_cellvars)))

@cpython_api([CONST_STRING, CONST_STRING, rffi.INT_real], PyCodeObject)
def PyCode_NewEmpty(space, filename, funcname, firstlineno):
    """Creates a new empty code object with the specified source location."""
    return space.wrap(PyCode(space,
                             argcount=0,
                             nlocals=0,
                             stacksize=0,
                             flags=0,
                             code="",
                             consts=[],
                             names=[],
                             varnames=[],
                             filename=rffi.charp2str(filename),
                             name=rffi.charp2str(funcname),
                             firstlineno=rffi.cast(lltype.Signed, firstlineno),
                             lnotab="",
                             freevars=[],
                             cellvars=[]))

@cpython_api([PyCodeObject], Py_ssize_t, error=CANNOT_FAIL)
def PyCode_GetNumFree(space, w_co):
    """Return the number of free variables in co."""
    co = space.interp_w(PyCode, w_co)
    return len(co.co_freevars)

