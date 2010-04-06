import ctypes
import sys

import py

from pypy.translator.goal import autopath
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rpython.tool import rffi_platform
from pypy.rpython.lltypesystem import ll2ctypes
from pypy.rpython.annlowlevel import llhelper
from pypy.rlib.objectmodel import we_are_translated
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
from pypy.module import exceptions
from pypy.module.exceptions import interp_exceptions
# CPython 2.4 compatibility
from py.builtin import BaseException

DEBUG_WRAPPER = False

# update these for other platforms
Py_ssize_t = lltype.Signed
size_t = rffi.ULONG
ADDR = lltype.Signed

include_dir = py.path.local(autopath.pypydir) / 'module' / 'cpyext' / 'include'
source_dir = py.path.local(autopath.pypydir) / 'module' / 'cpyext' / 'src'
include_dirs = [
    include_dir,
    udir,
    ]

class CConfig:
    _compilation_info_ = ExternalCompilationInfo(
        include_dirs=include_dirs,
        includes=['Python.h', 'stdarg.h']
        )

class CConfig_constants:
    _compilation_info_ = CConfig._compilation_info_

VA_LIST_P = rffi.VOIDP # rffi.COpaquePtr('va_list')

constant_names = """
Py_TPFLAGS_READY Py_TPFLAGS_READYING
METH_COEXIST METH_STATIC METH_CLASS METH_NOARGS METH_VARARGS METH_KEYWORDS
Py_TPFLAGS_HEAPTYPE Py_TPFLAGS_HAVE_CLASS
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
            wrapper.relax_sig_check = True
        return wrapper

def cpython_api(argtypes, restype, borrowed=False, error=_NOT_SPECIFIED,
                external=True, name=None):
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
        if name is None:
            func_name = func.func_name
        else:
            func_name = name

        if error is _NOT_SPECIFIED:
            raise ValueError("function %s has no return value for exceptions"
                             % func)
        def make_unwrapper(catch_exception):
            names = api_function.argnames
            types_names_enum_ui = unrolling_iterable(enumerate(
                zip(api_function.argtypes,
                    [tp_name.startswith("w_") for tp_name in names])))

            @specialize.ll()
            def unwrapper(space, *args):
                from pypy.module.cpyext.pyobject import Py_DecRef
                from pypy.module.cpyext.pyobject import make_ref, from_ref
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
                    for arg in to_decref:
                        Py_DecRef(space, arg)
            unwrapper.func = func
            unwrapper.api_func = api_function
            unwrapper._always_inline_ = True
            return unwrapper

        unwrapper_catch = make_unwrapper(True)
        unwrapper_raise = make_unwrapper(False)
        if external:
            FUNCTIONS[func_name] = api_function
        else:
            FUNCTIONS_STATIC[func_name] = api_function
        INTERPLEVEL_API[func_name] = unwrapper_catch # used in tests
        return unwrapper_raise # used in 'normal' RPython code.
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
FUNCTIONS_STATIC = {}
FUNCTIONS_C = [
    'Py_FatalError', 'PyOS_snprintf', 'PyOS_vsnprintf', 'PyArg_Parse',
    'PyArg_ParseTuple', 'PyArg_UnpackTuple', 'PyArg_ParseTupleAndKeywords',
    'PyString_FromFormatV', 'PyModule_AddObject', 'Py_BuildValue',
]
TYPES = {}
GLOBALS = { # this needs to include all prebuilt pto, otherwise segfaults occur
    'Py_None': ('PyObject*', 'space.w_None'),
    'Py_True': ('PyObject*', 'space.w_True'),
    'Py_False': ('PyObject*', 'space.w_False'),
    }

for exc_name in exceptions.Module.interpleveldefs.keys():
    GLOBALS['PyExc_' + exc_name] = ('PyTypeObject*', 'space.gettypeobject(interp_exceptions.W_%s.typedef)'% (exc_name, ))

for cpyname, pypyexpr in {"Type": "space.w_type",
        "BaseObject": "space.w_object",
        "Dict": "space.w_dict",
        "Tuple": "space.w_tuple",
        "List": "space.w_list",
        "Unicode": "space.w_unicode",
        'Bool': 'space.w_bool',
        'None': 'space.w_None',
        }.items():
    GLOBALS['Py%s_Type#' % (cpyname, )] = ('PyTypeObject*', pypyexpr)

def get_structtype_for_ctype(ctype):
    from pypy.module.cpyext.typeobjectdefs import PyTypeObjectPtr
    return {"PyObject*": PyObject, "PyTypeObject*": PyTypeObjectPtr}[ctype]

PyTypeObject = lltype.ForwardReference()
PyTypeObjectPtr = lltype.Ptr(PyTypeObject)
# It is important that these PyObjects are allocated in a raw fashion
# Thus we cannot save a forward pointer to the wrapped object
# So we need a forward and backward mapping in our State instance
PyObjectStruct = lltype.ForwardReference()
PyObject = lltype.Ptr(PyObjectStruct)
PyObjectFields = (("ob_refcnt", lltype.Signed), ("ob_type", PyTypeObjectPtr))
PyVarObjectFields = PyObjectFields + (("ob_size", Py_ssize_t), )
cpython_struct('struct _object', PyObjectFields, PyObjectStruct)
PyVarObjectStruct = cpython_struct("PyVarObject", PyVarObjectFields)
PyVarObject = lltype.Ptr(PyVarObjectStruct)

# a pointer to PyObject
PyObjectP = rffi.CArrayPtr(PyObject)

PyStringObjectStruct = lltype.ForwardReference()
PyStringObject = lltype.Ptr(PyStringObjectStruct)
PyStringObjectFields = PyObjectFields + \
    (("buffer", rffi.CCHARP), ("size", Py_ssize_t))
cpython_struct("PyStringObject", PyStringObjectFields, PyStringObjectStruct)

PyUnicodeObjectStruct = lltype.ForwardReference()
PyUnicodeObject = lltype.Ptr(PyUnicodeObjectStruct)
PyUnicodeObjectFields = (PyObjectFields +
    (("buffer", rffi.VOIDP), ("size", Py_ssize_t)))
cpython_struct("PyUnicodeObject", PyUnicodeObjectFields, PyUnicodeObjectStruct)

VA_TP_LIST = {}
#{'int': lltype.Signed,
#              'PyObject*': PyObject,
#              'PyObject**': PyObjectP,
#              'int*': rffi.INTP}

def configure_types():
    for name, TYPE in rffi_platform.configure(CConfig).iteritems():
        if name in TYPES:
            TYPES[name].become(TYPE)

def build_type_checkers(type_name, on_space=None):
    if on_space is None:
        on_space = "w_" + type_name.lower()
    check_name = "Py" + type_name + "_Check"
    @cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL, name=check_name)
    def check(space, w_obj):
        w_obj_type = space.type(w_obj)
        w_type = getattr(space, on_space)
        return int(space.is_w(w_obj_type, w_type) or
                   space.is_true(space.issubtype(w_obj_type, w_type)))
    @cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL,
                 name=check_name + "Exact")
    def check_exact(space, w_obj):
        w_obj_type = space.type(w_obj)
        w_type = getattr(space, on_space)
        return int(space.is_w(w_obj_type, w_type))
    return check, check_exact

# Make the wrapper for the cases (1) and (2)
def make_wrapper(space, callable):
    names = callable.api_func.argnames
    argtypes_enum_ui = unrolling_iterable(enumerate(zip(callable.api_func.argtypes,
        [name.startswith("w_") for name in names])))

    @specialize.ll()
    def wrapper(*args):
        from pypy.module.cpyext.pyobject import make_ref, from_ref
        from pypy.module.cpyext.pyobject import add_borrowed_object
        from pypy.module.cpyext.pyobject import NullPointerException
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
            if not rffi._isllptr(retval):
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

def process_va_name(name):
    return name.replace('*', '_star')

def setup_va_functions(eci):
    for name, TP in VA_TP_LIST.iteritems():
        name_no_star = process_va_name(name)
        func = rffi.llexternal('pypy_va_get_%s' % name_no_star, [VA_LIST_P],
                               TP, compilation_info=eci)
        globals()['va_get_%s' % name_no_star] = func


def bootstrap_types(space):
    from pypy.module.cpyext.pyobject import make_ref
    from pypy.module.cpyext.typeobject import PyTypeObjectPtr, PyPyType_Ready, \
            inherit_slots
    # bootstrap this damn cycle
    type_pto = make_ref(space, space.w_type)
    type_pto = rffi.cast(PyTypeObjectPtr, type_pto)
    object_pto = make_ref(space, space.w_object)
    object_pto = rffi.cast(PyTypeObjectPtr, object_pto)
    type_pto.c_tp_base = object_pto
    type_pto.c_ob_type = rffi.cast(PyTypeObjectPtr, make_ref(space, space.w_type))
    object_pto.c_ob_type = rffi.cast(PyTypeObjectPtr, make_ref(space, space.w_type))
    PyPyType_Ready(space, object_pto, space.w_object)
    PyPyType_Ready(space, type_pto, space.w_type)
    type_pto.c_tp_bases = make_ref(space, space.newtuple([space.w_object]))
    object_pto.c_tp_bases = make_ref(space, space.newtuple([]))
    inherit_slots(space, type_pto, space.w_object)

#_____________________________________________________
# Build the bridge DLL, Allow extension DLLs to call
# back into Pypy space functions
# Do not call this more than once per process
def build_bridge(space, rename=True):
    from pypy.module.cpyext.pyobject import make_ref

    export_symbols = list(FUNCTIONS) + FUNCTIONS_C + list(GLOBALS)
    from pypy.translator.c.database import LowLevelDatabase
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

    functions = generate_decls_and_callbacks(db, export_symbols)

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

    setup_va_functions(eci)

    return modulename.new(ext='')

def generate_macros(export_symbols, rename=True, do_deref=True):
    pypy_macros = []
    renamed_symbols = []
    for name in export_symbols:
        if name.startswith("PyPy"):
            renamed_symbols.append(name)
            continue
        if "#" in name:
            deref = "*"
            if not do_deref and not rename: continue
        else:
            deref = ""
            if not rename: continue
        name = name.replace("#", "")
        newname = name.replace('Py', 'PyPy')
        if not rename:
            newname = name
        pypy_macros.append('#define %s %s%s' % (name, deref, newname))
        renamed_symbols.append(newname)
    if rename:
        export_symbols[:] = renamed_symbols
    else:
        export_symbols[:] = [sym.replace("#", "") for sym in export_symbols]
    pypy_macros_h = udir.join('pypy_macros.h')
    pypy_macros_h.write('\n'.join(pypy_macros))

def generate_decls_and_callbacks(db, export_symbols, api_struct=True):
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
        header = "%s %s(%s)" % (restype, name, args)
        pypy_decls.append(header + ";")
        if api_struct:
            callargs = ', '.join('arg%d' % (i,)
                                 for i in range(len(func.argtypes)))
            body = "{ return _pypyAPI.%s(%s); }" % (name, callargs)
            functions.append('%s\n%s\n' % (header, body))
    pypy_decls.append("#ifndef PYPY_STANDALONE\n")
    for name, (typ, expr) in GLOBALS.iteritems():
        pypy_decls.append('PyAPI_DATA(%s) %s;' % (typ, name.replace("#", "")))
    for name in VA_TP_LIST:
        name_no_star = process_va_name(name)
        header = ('%s pypy_va_get_%s(va_list* vp)' %
                  (name, name_no_star))
        pypy_decls.append(header + ';')
        functions.append(header + '\n{return va_arg(*vp, %s);}\n' % name)
        export_symbols.append('pypy_va_get_%s' % (name_no_star,))
    
    pypy_decls.append("#endif\n")

    pypy_decl_h = udir.join('pypy_decl.h')
    pypy_decl_h.write('\n'.join(pypy_decls))
    return functions

def build_eci(build_bridge, export_symbols, code):
    # Build code and get pointer to the structure
    kwds = {}
    export_symbols_eci = export_symbols[:]

    if build_bridge:
        if sys.platform == "win32":
            # '%s' undefined; assuming extern returning int
            kwds["compile_extra"] = ["/we4013"]
        else:
            kwds["compile_extra"] = ["-Werror=implicit-function-declaration"]
        export_symbols_eci.append('pypyAPI')
    else:
        kwds["includes"] = ['Python.h'] # this is our Python.h

    eci = ExternalCompilationInfo(
        include_dirs=include_dirs,
        separate_module_files=[source_dir / "varargwrapper.c",
                               source_dir / "pyerrors.c",
                               source_dir / "modsupport.c",
                               source_dir / "getargs.c",
                               source_dir / "stringobject.c",
                               source_dir / "mysnprintf.c",
                               source_dir / "pythonrun.c"],
        separate_module_sources = [code],
        export_symbols=export_symbols_eci,
        **kwds
        )
    return eci


def setup_library(space, rename=False):
    from pypy.module.cpyext.pyobject import make_ref

    export_symbols = list(FUNCTIONS) + FUNCTIONS_C + list(GLOBALS)
    from pypy.translator.c.database import LowLevelDatabase
    db = LowLevelDatabase()

    generate_macros(export_symbols, rename, False)

    functions = generate_decls_and_callbacks(db, [], api_struct=False)
    code = "#include <Python.h>\n" + "\n".join(functions)

    eci = build_eci(False, export_symbols, code)

    bootstrap_types(space)
    setup_va_functions(eci)

    # populate static data
    for name, (type, expr) in GLOBALS.iteritems():
        name = name.replace("#", "")
        if rename:
            name = name.replace('Py', 'PyPy')
        w_obj = eval(expr)
        struct_ptr = make_ref(space, w_obj)
        struct = rffi.cast(get_structtype_for_ctype(type), struct_ptr)._obj
        struct._compilation_info = eci
        export_struct(name, struct)

    for name, func in FUNCTIONS.iteritems():
        deco = entrypoint("cpyext", func.argtypes, name, relax=True)
        deco(func.get_wrapper(space))
    for name, func in FUNCTIONS_STATIC.iteritems():
        func.get_wrapper(space).c_name = name


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
    from pypy.module.cpyext.pyobject import make_ref, from_ref, Py_DecRef
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
                        Py_DecRef(space, result)

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
                    Py_DecRef(space, ref)
    return generic_cpy_call

