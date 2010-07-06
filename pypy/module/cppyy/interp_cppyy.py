import py, os

from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import ObjSpace, interp2app
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.baseobjspace import Wrappable

from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.rpython.lltypesystem import rffi, lltype

from pypy.rlib.libffi import CDLL
from pypy.rlib import jit, debug

from pypy.module.cppyy import converter


srcpath = py.path.local(__file__).dirpath().join("src")
incpath = py.path.local(__file__).dirpath().join("include")
rootincpath = os.path.join(os.environ["ROOTSYS"], "include")
rootlibpath = os.path.join(os.environ["ROOTSYS"], "lib")

eci = ExternalCompilationInfo(
    separate_module_files=[srcpath.join("reflexcwrapper.cxx")],
    include_dirs=[incpath, rootincpath],
    library_dirs=[rootlibpath],
    libraries=["Reflex"],
    use_cpp_linker=True,
)

c_callstatic_l = rffi.llexternal(
    "callstatic_l",
    [rffi.CCHARP, rffi.INT, rffi.INT, rffi.VOIDPP], rffi.LONG,
    compilation_info=eci)
c_callstatic_d = rffi.llexternal(
    "callstatic_d",
    [rffi.CCHARP, rffi.INT, rffi.INT, rffi.VOIDPP], rffi.DOUBLE,
    compilation_info=eci)
c_construct = rffi.llexternal(
    "construct",
    [rffi.CCHARP, rffi.INT, rffi.VOIDPP], rffi.VOIDP,
    compilation_info=eci)
c_callmethod_l = rffi.llexternal(
    "callmethod_l",
    [rffi.CCHARP, rffi.INT, rffi.VOIDP, rffi.INT, rffi.VOIDPP], rffi.LONG,
    compilation_info=eci)
c_destruct = rffi.llexternal(
    "destruct",
    [rffi.CCHARP, rffi.VOIDP], lltype.Void,
    compilation_info=eci)


c_num_methods = rffi.llexternal(
    "num_methods",
    [rffi.CCHARP], rffi.INT,
    compilation_info=eci)
c_method_name = rffi.llexternal(
    "method_name",
    [rffi.CCHARP, rffi.INT], rffi.CCHARP,
    compilation_info=eci)
c_result_type_method = rffi.llexternal(
    "result_type_method",
    [rffi.CCHARP, rffi.INT], rffi.CCHARP,
    compilation_info=eci)
c_num_args_method = rffi.llexternal(
    "num_args_method",
    [rffi.CCHARP, rffi.INT], rffi.INT,
    compilation_info=eci)
c_arg_type_method = rffi.llexternal(
    "arg_type_method",
    [rffi.CCHARP, rffi.INT, rffi.INT], rffi.CCHARP,
    compilation_info=eci)
c_is_constructor = rffi.llexternal(
    "is_constructor",
    [rffi.CCHARP, rffi.INT], rffi.INT,
    compilation_info=eci)
c_is_static = rffi.llexternal(
    "is_static",
    [rffi.CCHARP, rffi.INT], rffi.INT,
    compilation_info=eci)
c_myfree = rffi.llexternal(
    "myfree",
    [rffi.VOIDP], lltype.Void,
    compilation_info=eci)


NULL_VOIDP = lltype.nullptr(rffi.VOIDP.TO)

def load_lib(space, name):
    cdll = CDLL(name)
    return W_CPPLibrary(space, cdll)
load_lib.unwrap_spec = [ObjSpace, str]

class W_CPPLibrary(Wrappable):
    _immutable_ = True
    def __init__(self, space, cdll):
        self.cdll = cdll
        self.space = space

    def type_byname(self, name):
        return W_CPPType(self, name)

W_CPPLibrary.typedef = TypeDef(
    'CPPLibrary',
    type_byname = interp2app(W_CPPLibrary.type_byname, unwrap_spec=['self', str]),
)

class CPPMethod(object):
    """ A concrete function after overloading has been resolved """
    _immutable_ = True
    _immutable_fields_ = ["arg_types[*]", "arg_converters[*]"]
    
    def __init__(self, cpptype, method_index, result_type, arg_types):
        self.cpptype = cpptype
        self.space = cpptype.space
        self.method_index = method_index
        self.result_type = result_type
        self.arg_types = arg_types
        self.arg_converters = None

    def call(self, cppthis, args_w):
        args = self.prepare_arguments(args_w)
        result = c_callmethod_l(self.cpptype.name, self.method_index,
                              cppthis, len(args_w), args)
        self.free_arguments(args)
        return self.space.wrap(result)

    def _build_converters(self):
        self.arg_converters = [converter.get_converter(arg_type)
                                   for arg_type in self.arg_types]

    @jit.unroll_safe
    def prepare_arguments(self, args_w):
        space = self.space
        if len(args_w) != len(self.arg_types):
            raise OperationError(space.w_TypeError, space.wrap("wrong number of args"))
        if self.arg_converters is None:
            self._build_converters()
        args = lltype.malloc(rffi.CArray(rffi.VOIDP), len(args_w), flavor='raw')
        for i in range(len(args_w)):
            argtype = self.arg_types[i]
            conv = self.arg_converters[i]
            w_arg = args_w[i]
            try:
                 arg = conv.convert_argument(space, w_arg)
            except:
                # fun :-(
                for j in range(i):
                    conv = self.arg_converters[j]
                    conv.free_argument(args[j])
                lltype.free(args, flavor='raw')
                raise
            args[i] = arg
        return args

    def free_arguments(self, args):
        for i in range(len(self.arg_types)):
            conv = self.arg_converters[i]
            conv.free_argument(args[i])
        lltype.free(args, flavor='raw')

    def __repr__(self):
        return "CPPFunction(%s, %s, %s, %s)" % (
            self.cpptype, self.method_index, self.result_type, self.arg_types)

class CPPFunction(CPPMethod):
    def call(self, cppthis, args_w):
        assert not cppthis
        args = self.prepare_arguments(args_w)
        try:
            if self.result_type == "int":
                result = c_callstatic_l(self.cpptype.name, self.method_index, len(args_w), args)
                return self.space.wrap(result)
            if self.result_type == "double":
                result = c_callstatic_d(self.cpptype.name, self.method_index, len(args_w), args)
                return self.space.wrap(result)
            if self.result_type == "char*":
                lresult = c_callstatic_l(self.cpptype.name, self.method_index, len(args_w), args)
                ccpresult = rffi.cast(rffi.CCHARP, lresult)
                result = charp2str_free(ccpresult)
                return self.space.wrap(result)
            else:
                raise NotImplementedError
        finally:
            self.free_arguments(args)
 

class CPPConstructor(CPPFunction):
    def call(self, cppthis, args_w):
        assert not cppthis
        args = self.prepare_arguments(args_w)
        result = c_construct(self.cpptype.name, len(args_w), args)
        self.free_arguments(args)
        return W_CPPObject(self.cpptype, result)


class CPPOverload(object):
    _immutable_ = True
    _immutable_fields_ = ["functions[*]"]
    def __init__(self, space, func_name, functions):
        self.space = space
        self.func_name = func_name
        self.functions = debug.make_sure_not_resized(functions)

    @jit.unroll_safe
    def call(self, cppthis, args_w):
        space = self.space
        for i in range(len(self.functions)):
            cppyyfunc = self.functions[i]
            try:
                return cppyyfunc.call(cppthis, args_w)
            except OperationError, e:
                if not e.match(space, space.w_TypeError):
                    raise
            except KeyError:
                pass
        # XXX better error reporting
        raise OperationError(space.w_TypeError, space.wrap("none of the overloads matched"))

    def __repr__(self):
        return "CPPOverload(%s, %s)" % (self.func_name, self.functions)

def charp2str_free(charp):
    string = rffi.charp2str(charp)
    c_myfree(charp)
    return string

class W_CPPType(Wrappable):
    _immutable_fields_ = ["cpplib", "name"]

    def __init__(self, cpplib, name):
        self.space = cpplib.space
        self.cpplib = cpplib
        self.name = name
        self.function_members = {}
        self._find_func_members()
    
    def _find_func_members(self):
        num_func_members = c_num_methods(self.name)
        args_temp = {}
        for i in range(num_func_members):
            func_member_name = charp2str_free(c_method_name(self.name, i))
            cppfunction = self._make_cppfunction(i)
            overload = args_temp.setdefault(func_member_name, [])
            overload.append(cppfunction)
        for name, functions in args_temp.iteritems():
            overload = CPPOverload(self.space, name, functions[:])
            self.function_members[name] = overload

    def _make_cppfunction(self, method_index):
        result_type = charp2str_free(c_result_type_method(self.name, method_index))
        num_args = c_num_args_method(self.name, method_index)
        argtypes = []
        for i in range(num_args):
            argtype = charp2str_free(c_arg_type_method(self.name, method_index, i))
            argtypes.append(argtype)
        if c_is_constructor(self.name, method_index):
            cls = CPPConstructor
        elif c_is_static(self.name, method_index):
            cls = CPPFunction
        else:
            cls = CPPMethod
        return cls(self, method_index, result_type, argtypes)

    @jit.purefunction
    def get_overload(self, name):
        return self.function_members[name]

    def invoke(self, name, args_w):
        overload = self.get_overload(name)
        return overload.call(NULL_VOIDP, args_w)

    def construct(self, args_w):
        overload = self.get_overload(self.name)
        return overload.call(NULL_VOIDP, args_w)

W_CPPType.typedef = TypeDef(
    'CPPType',
    invoke = interp2app(W_CPPType.invoke, unwrap_spec=['self', str, 'args_w']),
    construct = interp2app(W_CPPType.construct, unwrap_spec=['self', 'args_w']),
)

class W_CPPObject(Wrappable):
    _immutable_ = True
    def __init__(self, cppclass, rawobject):
        self.space = cppclass.space
        self.cppclass = cppclass
        self.rawobject = rawobject

    def invoke(self, method_name, args_w):
        cppclass = jit.hint(self.cppclass, promote=True)
        overload = cppclass.get_overload(method_name)
        return overload.call(self.rawobject, args_w)

    def destruct(self):
        c_destruct(self.cppclass.name, self.rawobject)

W_CPPObject.typedef = TypeDef(
    'CPPObject',
    invoke = interp2app(W_CPPObject.invoke, unwrap_spec=['self', str, 'args_w']),
    destruct = interp2app(W_CPPObject.destruct, unwrap_spec=['self']),
)
