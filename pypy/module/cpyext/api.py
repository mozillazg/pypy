import ctypes
import sys

import py

from pypy.translator.goal import autopath
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rpython.tool import rffi_platform
from pypy.rpython.lltypesystem import ll2ctypes
from pypy.rpython.annlowlevel import llhelper
from pypy.rlib.objectmodel import we_are_translated
from pypy.translator.c.database import LowLevelDatabase
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.tool.udir import udir
from pypy.translator import platform
from pypy.module.cpyext.state import State
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.gateway import ObjSpace, unwrap_spec
from pypy.objspace.std.stringobject import W_StringObject
from pypy.rlib.entrypoint import entrypoint
from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.objectmodel import specialize
from pypy.rlib.exports import export_struct
# CPython 2.4 compatibility
from py.builtin import BaseException

DEBUG_REFCOUNT = False
DEBUG_WRAPPER = False

Py_ssize_t = lltype.Signed
ADDR = lltype.Signed

include_dir = py.path.local(autopath.pypydir) / 'module' / 'cpyext' / 'include'
include_dirs = [
    include_dir,
    udir,
    ]

class CConfig:
    _compilation_info_ = ExternalCompilationInfo(
        include_dirs=include_dirs,
        includes=['Python.h']
        )

class CConfig_constants:
    _compilation_info_ = CConfig._compilation_info_

constant_names = """
Py_TPFLAGS_READY Py_TPFLAGS_READYING
METH_COEXIST METH_STATIC METH_CLASS METH_NOARGS
Py_TPFLAGS_HEAPTYPE
""".split()
for name in constant_names:
    setattr(CConfig_constants, name, rffi_platform.ConstantInteger(name))
udir.join('pypy_decl.h').write("/* Will be filled later */")
udir.join('pypy_macros.h').write("/* Will be filled later */")
globals().update(rffi_platform.configure(CConfig_constants))

_NOT_SPECIFIED = object()
CANNOT_FAIL = object()

# The same function can be called in three different contexts:
# (1) from C code
# (2) in the test suite, though the "api" object
# (3) from RPython code, for example in the implementation of another function.
#
# In contexts (2) and (3), a function declaring a PyObject argument type will
# receive a wrapped pypy object if the parameter name starts with 'w_', a
# reference (= rffi pointer) otherwise; conversion is automatic.  Context (2)
# only allows calls with a wrapped object.
#
# Functions with a PyObject return type should return a wrapped object.
#
# Functions may raise exceptions.  In context (3), the exception flows normally
# through the calling function.  In context (1) and (2), the exception is
# caught; if it is an OperationError, it is stored in the thread state; other
# exceptions generate a OperationError(w_SystemError); and the funtion returns
# the error value specifed in the API.
#

class ApiFunction:
    def __init__(self, argtypes, restype, callable, borrowed, error):
        self.argtypes = argtypes
        self.restype = restype
        self.functype = lltype.Ptr(lltype.FuncType(argtypes, restype))
        self.callable = callable
        self.borrowed = borrowed
        if error is not _NOT_SPECIFIED:
            self.error_value = error

        # extract the signature from the (CPython-level) code object
        from pypy.interpreter import pycode
        argnames, varargname, kwargname = pycode.cpython_code_signature(callable.func_code)

        assert argnames[0] == 'space'
        self.argnames = argnames[1:]
        assert len(self.argnames) == len(self.argtypes)

    def _freeze_(self):
        return True

    def get_llhelper(self, space):
        llh = getattr(self, '_llhelper', None)
        if llh is None:
            llh = llhelper(self.functype, self.get_wrapper(space))
            self._llhelper = llh
        return llh

    @specialize.memo()
    def get_wrapper(self, space):
        wrapper = getattr(self, '_wrapper', None)
        if wrapper is None:
            wrapper = make_wrapper(space, self.callable)
            self._wrapper = wrapper
        return wrapper

def cpython_api(argtypes, restype, borrowed=False, error=_NOT_SPECIFIED, external=True):
    if error is _NOT_SPECIFIED:
        if restype is PyObject:
            error = lltype.nullptr(PyObject.TO)
        elif restype is lltype.Void:
            error = CANNOT_FAIL
    if type(error) is int:
        error = rffi.cast(restype, error)

    def decorate(func):
        api_function = ApiFunction(argtypes, restype, func, borrowed, error)
        func.api_func = api_function

        if error is _NOT_SPECIFIED:
            raise ValueError("function %s has no return value for exceptions"
                             % func)
        def make_unwrapper(catch_exception):
            names = api_function.argnames
            types_names_enum_ui = unrolling_iterable(enumerate(
                zip(api_function.argtypes,
                    [name.startswith("w_") for name in names])))

            @specialize.ll()
            def unwrapper(space, *args):
                newargs = ()
                to_decref = []
                for i, (ARG, is_wrapped) in types_names_enum_ui:
                    input_arg = args[i]
                    if ARG is PyObject and not is_wrapped:
                        # build a reference
                        if input_arg is None:
                            arg = lltype.nullptr(PyObject.TO)
                        elif isinstance(input_arg, W_Root):
                            arg = make_ref(space, input_arg)
                            to_decref.append(arg)
                        else:
                            arg = input_arg
                    elif ARG is PyObject and is_wrapped:
                        # convert to a wrapped object
                        if rffi._isllptr(input_arg):
                            arg = from_ref(space, input_arg)
                        else:
                            arg = input_arg
                    else:
                        arg = input_arg
                    newargs += (arg, )
                try:
                    try:
                        return func(space, *newargs)
                    except OperationError, e:
                        if not catch_exception:
                            raise
                        if not hasattr(api_function, "error_value"):
                            raise
                        state = space.fromcache(State)
                        e.normalize_exception(space)
                        state.set_exception(e.w_type, e.get_w_value(space))
                        return api_function.error_value
                finally:
                    if api_function.borrowed:
                        state = space.fromcache(State)
                        state.last_container = 0
                    from pypy.module.cpyext.macros import Py_DECREF
                    for arg in to_decref:
                        Py_DECREF(space, arg)
            unwrapper.func = func
            unwrapper.api_func = api_function
            unwrapper._always_inline_ = True
            return unwrapper

        unwrapper_catch = make_unwrapper(True)
        unwrapper_raise = make_unwrapper(False)
        if external:
            FUNCTIONS[func.func_name] = api_function
        INTERPLEVEL_API[func.func_name] = unwrapper_catch # used in tests
        return unwrapper_raise # used in 'normal' RPython code.
    return decorate

def cpython_api_c():
    def decorate(func):
        FUNCTIONS_C[func.func_name] = None
    return decorate

def cpython_struct(name, fields, forward=None):
    configname = name.replace(' ', '__')
    setattr(CConfig, configname, rffi_platform.Struct(name, fields))
    if forward is None:
        forward = lltype.ForwardReference()
    TYPES[configname] = forward
    return forward

INTERPLEVEL_API = {}
FUNCTIONS = {}
FUNCTIONS_C = {}
TYPES = {}
GLOBALS = {
    'Py_None': ('PyObject*', 'space.w_None'),
    'Py_True': ('PyObject*', 'space.w_True'),
    'Py_False': ('PyObject*', 'space.w_False'),
    'PyExc_Exception': ('PyObject*', 'space.w_Exception'),
    'PyExc_TypeError': ('PyObject*', 'space.w_TypeError'),
    'PyType_Type#': ('PyTypeObject*', 'space.w_type'),
    'PyBaseObject_Type#': ('PyTypeObject*', 'space.w_object'),
    }

# It is important that these PyObjects are allocated in a raw fashion
# Thus we cannot save a forward pointer to the wrapped object
# So we need a forward and backward mapping in our State instance
PyObjectStruct = lltype.ForwardReference()
PyObject = lltype.Ptr(PyObjectStruct)
PyObjectFields = (("ob_refcnt", lltype.Signed), ("ob_type", PyObject))
PyVarObjectFields = PyObjectFields + (("ob_size", Py_ssize_t), )
cpython_struct('struct _object', PyObjectFields, PyObjectStruct)

PyStringObjectStruct = lltype.ForwardReference()
PyStringObject = lltype.Ptr(PyStringObjectStruct)
PyStringObjectFields = PyObjectFields + \
    (("buffer", rffi.CCHARP), ("size", Py_ssize_t))
cpython_struct("PyStringObject", PyStringObjectFields, PyStringObjectStruct)

def configure_types():
    for name, TYPE in rffi_platform.configure(CConfig).iteritems():
        if name in TYPES:
            TYPES[name].become(TYPE)


class NullPointerException(Exception):
    pass

class InvalidPointerException(Exception):
    pass

def debug_refcount(*args, **kwargs):
    frame_stackdepth = kwargs.pop("frame_stackdepth", 2)
    assert not kwargs
    frame = sys._getframe(frame_stackdepth)
    print >>sys.stderr, "%25s" % (frame.f_code.co_name, ),
    for arg in args:
        print >>sys.stderr, arg,
    print >>sys.stderr


def make_ref(space, w_obj, borrowed=False, steal=False):
    from pypy.module.cpyext.macros import Py_INCREF, Py_DECREF
    if w_obj is None:
        return lltype.nullptr(PyObject.TO)
    assert isinstance(w_obj, W_Root)
    state = space.fromcache(State)
    py_obj = state.py_objects_w2r.get(w_obj, lltype.nullptr(PyObject.TO))
    if not py_obj:
        from pypy.module.cpyext.typeobject import allocate_type_obj,\
                W_PyCTypeObject, W_PyCObject
        w_type = space.type(w_obj)
        if space.is_w(w_type, space.w_type):
            pto = allocate_type_obj(space, w_obj)
            py_obj = rffi.cast(PyObject, pto)
            # c_ob_type and c_ob_refcnt are set by allocate_type_obj
        elif isinstance(w_obj, W_PyCObject):
            w_type = space.type(w_obj)
            assert isinstance(w_type, W_PyCTypeObject)
            pto = w_type.pto
            # Don't increase refcount for non-heaptypes
            # Py_INCREF(space, pto)
            basicsize = pto.c_tp_basicsize
            py_obj_pad = lltype.malloc(rffi.VOIDP.TO, basicsize,
                    flavor="raw", zero=True)
            py_obj = rffi.cast(PyObject, py_obj_pad)
            py_obj.c_ob_refcnt = 1
            py_obj.c_ob_type = rffi.cast(PyObject, pto)
        elif isinstance(w_obj, W_StringObject):
            py_obj_str = lltype.malloc(PyStringObject.TO, flavor='raw', zero=True)
            py_obj_str.c_size = len(space.str_w(w_obj))
            py_obj_str.c_buffer = lltype.nullptr(rffi.CCHARP.TO)
            pto = make_ref(space, space.w_str)
            py_obj = rffi.cast(PyObject, py_obj_str)
            py_obj.c_ob_refcnt = 1
            py_obj.c_ob_type = rffi.cast(PyObject, pto)
        else:
            py_obj = lltype.malloc(PyObject.TO, flavor="raw", zero=True)
            py_obj.c_ob_refcnt = 1
            pto = make_ref(space, space.type(w_obj))
            py_obj.c_ob_type = rffi.cast(PyObject, pto)
        ptr = rffi.cast(ADDR, py_obj)
        if DEBUG_REFCOUNT:
            debug_refcount("MAKREF", py_obj, w_obj)
        state.py_objects_w2r[w_obj] = py_obj
        state.py_objects_r2w[ptr] = w_obj
        if borrowed and ptr not in state.borrowed_objects:
            state.borrowed_objects[ptr] = None
    elif not steal:
        if borrowed:
            py_obj_addr = rffi.cast(ADDR, py_obj)
            if py_obj_addr not in state.borrowed_objects:
                Py_INCREF(space, py_obj)
                state.borrowed_objects[py_obj_addr] = None
        else:
            Py_INCREF(space, py_obj)
    return py_obj

def force_string(space, ref):
    state = space.fromcache(State)
    ref = rffi.cast(PyStringObject, ref)
    s = rffi.charpsize2str(ref.c_buffer, ref.c_size)
    ref = rffi.cast(PyObject, ref)
    w_str = space.wrap(s)
    state.py_objects_w2r[w_str] = ref
    ptr = rffi.cast(ADDR, ref)
    state.py_objects_r2w[ptr] = w_str
    return w_str


def from_ref(space, ref):
    assert lltype.typeOf(ref) == PyObject
    if not ref:
        return None
    state = space.fromcache(State)
    ptr = rffi.cast(ADDR, ref)
    try:
        obj = state.py_objects_r2w[ptr]
    except KeyError:
        ref_type = ref.c_ob_type
        if ref != ref_type and space.is_w(from_ref(space, ref_type), space.w_str):
            return force_string(space, ref)
        else:
            msg = ""
            if not we_are_translated():
                msg = "Got invalid reference to a PyObject: %r" % (ref, )
            raise InvalidPointerException(msg)
    return obj


@cpython_api([PyObject], lltype.Void, external=False)
def register_container(space, container):
    state = space.fromcache(State)
    if not container: # self-managed
        container_ptr = -1
    else:
        container_ptr = rffi.cast(ADDR, container)
    assert not state.last_container, "Last container was not fetched"
    state.last_container = container_ptr

def add_borrowed_object(space, obj):
    state = space.fromcache(State)
    container_ptr = state.last_container
    state.last_container = 0
    if not container_ptr:
        raise NullPointerException
    if container_ptr == -1:
        return
    borrowees = state.borrow_mapping.get(container_ptr, None)
    if borrowees is None:
        state.borrow_mapping[container_ptr] = borrowees = {}
    obj_ptr = rffi.cast(ADDR, obj)
    borrowees[obj_ptr] = None


def general_check(space, w_obj, w_type):
    w_obj_type = space.type(w_obj)
    return int(space.is_w(w_obj_type, w_type) or space.is_true(space.issubtype(w_obj_type, w_type)))

def general_check_exact(space, w_obj, w_type):
    w_obj_type = space.type(w_obj)
    return int(space.is_w(w_obj_type, w_type))

# Make the wrapper for the cases (1) and (2)
def make_wrapper(space, callable):
    names = callable.api_func.argnames
    argtypes_enum_ui = unrolling_iterable(enumerate(zip(callable.api_func.argtypes,
        [name.startswith("w_") for name in names])))

    @specialize.ll()
    def wrapper(*args):
        boxed_args = ()
        if DEBUG_WRAPPER:
            print >>sys.stderr, callable,
        for i, (typ, is_wrapped) in argtypes_enum_ui:
            arg = args[i]
            if (typ is PyObject and
                is_wrapped):
                if arg:
                    arg_conv = from_ref(space, arg)
                else:
                    arg_conv = None
            else:
                arg_conv = arg
            boxed_args += (arg_conv, )
        state = space.fromcache(State)
        try:
            retval = callable(space, *boxed_args)
            if DEBUG_WRAPPER:
                print >>sys.stderr, " DONE"
        except OperationError, e:
            failed = True
            e.normalize_exception(space)
            state.set_exception(e.w_type, e.get_w_value(space))
        except BaseException, e:
            failed = True
            state.set_exception(space.w_SystemError, space.wrap(str(e)))
            if not we_are_translated():
                import traceback
                traceback.print_exc()
        else:
            failed = False

        if failed:
            error_value = callable.api_func.error_value
            if error_value is CANNOT_FAIL:
                raise SystemError("The function '%s' was not supposed to fail"
                                  % (callable.__name__,))
            return error_value

        if callable.api_func.restype is PyObject:
            borrowed = callable.api_func.borrowed
            retval = make_ref(space, retval, borrowed=borrowed)
            if borrowed:
                try:
                    add_borrowed_object(space, retval)
                except NullPointerException, e:
                    if not we_are_translated():
                        assert False, "Container not registered by %s" % (callable, )
                    else:
                        raise
        elif callable.api_func.restype is not lltype.Void:
            retval = rffi.cast(callable.api_func.restype, retval)
        return retval
    callable._always_inline_ = True
    wrapper.__name__ = "wrapper for %r" % (callable, )
    return wrapper

def bootstrap_types(space):
    from pypy.module.cpyext.typeobject import PyTypeObjectPtr, PyPyType_Ready
    # bootstrap this damn cycle
    type_pto = make_ref(space, space.w_type)
    type_pto = rffi.cast(PyTypeObjectPtr, type_pto)
    object_pto = make_ref(space, space.w_object)
    object_pto = rffi.cast(PyTypeObjectPtr, object_pto)
    type_pto.c_tp_base = object_pto
    type_pto.c_ob_type = make_ref(space, space.w_type)
    object_pto.c_ob_type = make_ref(space, space.w_type)
    PyPyType_Ready(space, object_pto, space.w_object)
    PyPyType_Ready(space, type_pto, space.w_type)
    type_pto.c_tp_bases = make_ref(space, space.newtuple([space.w_object]))
    object_pto.c_tp_bases = make_ref(space, space.newtuple([]))

#_____________________________________________________
# Build the bridge DLL, Allow extension DLLs to call
# back into Pypy space functions
# Do not call this more than once per process
def build_bridge(space, rename=True):
    export_symbols = list(FUNCTIONS) + list(FUNCTIONS_C) + list(GLOBALS)
    db = LowLevelDatabase()

    generate_macros(export_symbols, rename)

    # Structure declaration code
    members = []
    structindex = {}
    for name, func in FUNCTIONS.iteritems():
        cdecl = db.gettype(func.functype)
        members.append(cdecl.replace('@', name) + ';')
        structindex[name] = len(structindex)
    structmembers = '\n'.join(members)
    struct_declaration_code = """\
    struct PyPyAPI {
    %(members)s
    } _pypyAPI;
    struct PyPyAPI* pypyAPI = &_pypyAPI;
    """ % dict(members=structmembers)

    functions = generate_decls_and_callbacks(db)

    global_objects = []
    for name, (type, expr) in GLOBALS.iteritems():
        global_objects.append('%s %s = NULL;' % (type, name.replace("#", "")))
    global_code = '\n'.join(global_objects)

    prologue = "#include <Python.h>\n"
    code = (prologue +
            struct_declaration_code +
            global_code +
            '\n' +
            '\n'.join(functions))

    eci = build_eci(True, export_symbols, code)
    eci = eci.convert_sources_to_files()
    modulename = platform.platform.compile(
        [], eci,
        outputfilename=str(udir / "module_cache" / "pypyapi"),
        standalone=False)

    bootstrap_types(space)

    # load the bridge, and init structure
    import ctypes
    bridge = ctypes.CDLL(str(modulename))
    pypyAPI = ctypes.POINTER(ctypes.c_void_p).in_dll(bridge, 'pypyAPI')

    # populate static data
    for name, (type, expr) in GLOBALS.iteritems():
        name = name.replace("#", "")
        if rename:
            name = name.replace('Py', 'PyPy')
        w_obj = eval(expr)
        ptr = ctypes.c_void_p.in_dll(bridge, name)
        ptr.value = ctypes.cast(ll2ctypes.lltype2ctypes(make_ref(space, w_obj)),
            ctypes.c_void_p).value

    # implement structure initialization code
    for name, func in FUNCTIONS.iteritems():
        pypyAPI[structindex[name]] = ctypes.cast(
            ll2ctypes.lltype2ctypes(func.get_llhelper(space)),
            ctypes.c_void_p)

    return modulename.new(ext='')

def generate_macros(export_symbols, rename=True):
    pypy_macros = []
    renamed_symbols = []
    for name in export_symbols:
        if name.startswith("PyPy"):
            renamed_symbols.append(name)
            continue
        if "#" in name:
            deref = "*"
        else:
            deref = ""
            if not rename: continue
        name = name.replace("#", "")
        newname = name.replace('Py', 'PyPy')
        if not rename:
            newname = name
        pypy_macros.append('#define %s %s%s' % (name, deref, newname))
        renamed_symbols.append(newname)
    export_symbols[:] = renamed_symbols
    pypy_macros_h = udir.join('pypy_macros.h')
    pypy_macros_h.write('\n'.join(pypy_macros))

def generate_decls_and_callbacks(db):
    # implement function callbacks and generate function decls
    functions = []
    pypy_decls = []
    for name, func in sorted(FUNCTIONS.iteritems()):
        restype = db.gettype(func.restype).replace('@', '')
        args = []
        for i, argtype in enumerate(func.argtypes):
            arg = db.gettype(argtype)
            arg = arg.replace('@', 'arg%d' % (i,))
            args.append(arg)
        args = ', '.join(args) or "void"
        callargs = ', '.join('arg%d' % (i,) for i in range(len(func.argtypes)))
        header = "%s %s(%s)" % (restype, name, args)
        pypy_decls.append(header + ";")
        body = "{ return _pypyAPI.%s(%s); }" % (name, callargs)
        functions.append('%s\n%s\n' % (header, body))

    pypy_decl_h = udir.join('pypy_decl.h')
    pypy_decl_h.write('\n'.join(pypy_decls))
    return functions

def build_eci(build_bridge, export_symbols, code=None):
    # Build code and get pointer to the structure
    kwds = {}
    export_symbols_eci = export_symbols[:]

    if sys.platform != "win32":
        kwds["compile_extra"] = ["-Werror=implicit-function-declaration"]

    if build_bridge:
        assert code is not None
        kwds["separate_module_sources"] = [code]
        export_symbols_eci.append('pypyAPI')
    else:
        assert code is None

    eci = ExternalCompilationInfo(
        include_dirs=include_dirs,
        separate_module_files=[include_dir / "varargwrapper.c",
                               include_dir / "pyerrors.c",
                               include_dir / "modsupport.c"],
        export_symbols=export_symbols_eci,
        **kwds
        )
    return eci


def setup_library(space, rename=False):
    export_symbols = list(FUNCTIONS) + list(FUNCTIONS_C) + list(GLOBALS)
    db = LowLevelDatabase()

    generate_macros(export_symbols, rename)

    generate_decls_and_callbacks(db)

    eci = build_eci(False, export_symbols)

    bootstrap_types(space)

    # populate static data
    for name, (type, expr) in GLOBALS.iteritems():
        name = name.replace("#", "")
        if rename:
            name = name.replace('Py', 'PyPy')
        w_obj = eval(expr)
        export_struct(name, make_ref(space, w_obj)._obj)

    for name, func in FUNCTIONS.iteritems():
        deco = entrypoint("cpyext", func.argtypes, name, relax=True)
        deco(func.get_wrapper(space))


@unwrap_spec(ObjSpace, str, str)
def load_extension_module(space, path, name):
    state = space.fromcache(State)
    from pypy.rlib import libffi
    try:
        dll = libffi.CDLL(path, False)
    except libffi.DLOpenError, e:
        raise operationerrfmt(
            space.w_ImportError,
            "unable to load extension module '%s': %s",
            path, e.msg)
    try:
        initfunc = dll.getpointer(
            'init%s' % (name,), [], libffi.ffi_type_void)
    except KeyError:
        raise operationerrfmt(
            space.w_ImportError,
            "function init%s not found in library %s",
            name, path)
    initfunc.call(lltype.Void)
    state.check_and_raise_exception()

@specialize.ll()
def generic_cpy_call(space, func, *args):
    FT = lltype.typeOf(func).TO
    return make_generic_cpy_call(FT, True)(space, func, *args)

@specialize.ll()
def generic_cpy_call_dont_decref(space, func, *args):
    FT = lltype.typeOf(func).TO
    return make_generic_cpy_call(FT, False)(space, func, *args)

@specialize.memo()
def make_generic_cpy_call(FT, decref_args):
    from pypy.module.cpyext.macros import Py_DECREF
    from pypy.module.cpyext.pyerrors import PyErr_Occurred
    unrolling_arg_types = unrolling_iterable(enumerate(FT.ARGS))
    RESULT_TYPE = FT.RESULT

    @specialize.ll()
    def generic_cpy_call(space, func, *args):
        boxed_args = ()
        to_decref = []
        for i, ARG in unrolling_arg_types:
            arg = args[i]
            if ARG is PyObject:
                if arg is None:
                    boxed_args += (lltype.nullptr(PyObject.TO),)
                elif isinstance(arg, W_Root):
                    ref = make_ref(space, arg)
                    boxed_args += (ref,)
                    if decref_args:
                        to_decref.append(ref)
                else:
                    boxed_args += (arg,)
            else:
                boxed_args += (arg,)
        result = func(*boxed_args)
        try:
            if RESULT_TYPE is PyObject:
                if result is None:
                    ret = result
                elif isinstance(result, W_Root):
                    ret = result
                else:
                    ret = from_ref(space, result)
                    # The object reference returned from a C function
                    # that is called from Python must be an owned reference
                    # - ownership is transferred from the function to its caller.
                    if result:
                        Py_DECREF(space, result)

                # Check for exception consistency
                has_error = PyErr_Occurred(space) is not None
                has_result = ret is not None
                if has_error and has_result:
                    raise OperationError(space.w_SystemError, space.wrap(
                        "An exception was set, but function returned a value"))
                elif not has_error and not has_result:
                    raise OperationError(space.w_SystemError, space.wrap(
                        "Function returned a NULL result without setting an exception"))

                if has_error:
                    state = space.fromcache(State)
                    state.check_and_raise_exception()

                return ret
        finally:
            if decref_args:
                for ref in to_decref:
                    Py_DECREF(space, ref)
    return generic_cpy_call

