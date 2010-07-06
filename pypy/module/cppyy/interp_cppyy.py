import py, os

from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import ObjSpace, interp2app
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.baseobjspace import Wrappable

from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.rpython.lltypesystem import rffi, lltype

from pypy.rlib.libffi import CDLL

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

callstatic_l = rffi.llexternal(
    "callstatic_l",
    [rffi.CCHARP, rffi.INT, rffi.INT, rffi.VOIDPP], rffi.LONG,
    compilation_info=eci)
callstatic_d = rffi.llexternal(
    "callstatic_d",
    [rffi.CCHARP, rffi.INT, rffi.INT, rffi.VOIDPP], rffi.DOUBLE,
    compilation_info=eci)
construct = rffi.llexternal(
    "construct",
    [rffi.CCHARP, rffi.INT, rffi.VOIDPP], rffi.VOIDP,
    compilation_info=eci)
callmethod_l = rffi.llexternal(
    "callmethod_l",
    [rffi.CCHARP, rffi.INT, rffi.VOIDP, rffi.INT, rffi.VOIDPP], rffi.LONG,
    compilation_info=eci)
destruct = rffi.llexternal(
    "destruct",
    [rffi.CCHARP, rffi.VOIDP], lltype.Void,
    compilation_info=eci)


num_methods = rffi.llexternal(
    "num_methods",
    [rffi.CCHARP], rffi.INT,
    compilation_info=eci)
method_name = rffi.llexternal(
    "method_name",
    [rffi.CCHARP, rffi.INT], rffi.CCHARP,
    compilation_info=eci)
result_type_method = rffi.llexternal(
    "result_type_method",
    [rffi.CCHARP, rffi.INT], rffi.CCHARP,
    compilation_info=eci)
num_args_method = rffi.llexternal(
    "num_args_method",
    [rffi.CCHARP, rffi.INT], rffi.INT,
    compilation_info=eci)
arg_type_method = rffi.llexternal(
    "arg_type_method",
    [rffi.CCHARP, rffi.INT, rffi.INT], rffi.CCHARP,
    compilation_info=eci)
is_constructor = rffi.llexternal(
    "is_constructor",
    [rffi.CCHARP, rffi.INT], rffi.INT,
    compilation_info=eci)
is_static = rffi.llexternal(
    "is_static",
    [rffi.CCHARP, rffi.INT], rffi.INT,
    compilation_info=eci)
myfree = rffi.llexternal(
    "myfree",
    [rffi.VOIDP], lltype.Void,
    compilation_info=eci)


def load_lib(space, name):
    cdll = CDLL(name)
    return W_CPPLibrary(space, cdll)
load_lib.unwrap_spec = [ObjSpace, str]

def prepare_arguments(space, args_w, argtypes):
    if len(args_w) != len(argtypes):
        raise OperationError(space.w_TypeError, space.wrap("wrong number of args"))
    args = lltype.malloc(rffi.CArray(rffi.VOIDP), len(args_w), flavor='raw')
    for i in range(len(args_w)):
        argtype = argtypes[i]
        conv = converter.get_converter(argtype)
        # XXX this can leak so far
        args[i] = conv.convert_argument(space, args_w[i])
    return args

def free_arguments(args, numargs):
    for i in range(numargs):
        lltype.free(args[i], flavor='raw')
    lltype.free(args, flavor='raw')

class W_CPPLibrary(Wrappable):
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
    
    def __init__(self, cpptype, method_index, result_type, arg_types):
        self.cpptype = cpptype
        self.space = cpptype.space
        self.method_index = method_index
        self.result_type = result_type
        self.arg_types = arg_types

    def call(self, cppthis, args_w):
        args = prepare_arguments(self.space, args_w, self.arg_types)
        result = callmethod_l(self.cpptype.name, self.method_index,
                              cppthis, len(args_w), args)
        free_arguments(args, len(args_w))
        return result

    def __repr__(self):
        return "CPPFunction(%s, %s, %s, %s)" % (
            self.cpptype, self.method_index, self.result_type, self.arg_types)

class CPPFunction(CPPMethod):
    def call(self, cppthis, args_w):
        assert cppthis is None
        args = prepare_arguments(self.space, args_w, self.arg_types)
        if self.result_type == "int":
            result = callstatic_l(self.cpptype.name, self.method_index, len(args_w), args)
            return self.space.wrap(result)
        if self.result_type == "double":
            result = callstatic_d(self.cpptype.name, self.method_index, len(args_w), args)
            return self.space.wrap(result)
        else:
            raise NotImplementedError
        free_arguments(args, len(args_w))
 

class CPPConstructor(CPPFunction):
    def call(self, cppthis, args_w):
        assert cppthis is None
        args = prepare_arguments(self.space, args_w, self.arg_types)
        result = construct(self.cpptype.name, len(args_w), args)
        free_arguments(args, len(args_w))
        return result


class CPPOverload(object):
    def __init__(self, space, func_name):
        self.space = space
        self.func_name = func_name
        self.functions = []

    def add_function(self, cppfunc):
        self.functions.append(cppfunc)

    def call(self, cppthis, args_w):
        space = self.space
        for cppyyfunc in self.functions:
            try:
                return cppyyfunc.call(cppthis, args_w)
            except OperationError, e:
                if not e.match(space, space.w_TypeError):
                    raise
        # XXX better error reporting
        raise OperationError(space.w_TypeError, space.wrap("none of the overloads matched"))

    def __repr__(self):
        return "CPPOverload(%s, %s)" % (self.func_name, self.functions)

def charp2str(charp):
    string = rffi.charp2str(charp)
    myfree(charp)
    return string

class W_CPPType(Wrappable):
    def __init__(self, cpplib, name):
        self.space = cpplib.space
        self.cpplib = cpplib
        self.name = name
        self.function_members = {}
        self._find_func_members()
    
    def _find_func_members(self):
        num_func_members = num_methods(self.name)
        for i in range(num_func_members):
            func_member_name = charp2str(method_name(self.name, i))
            cppfunction = self._make_cppfunction(i)
            overload = self.function_members.get(func_member_name, None)
            if overload is None:
                overload = CPPOverload(self.space, func_member_name)
                self.function_members[func_member_name] = overload
            overload.add_function(cppfunction)

    def _make_cppfunction(self, method_index):
        result_type = charp2str(result_type_method(self.name, method_index))
        num_args = num_args_method(self.name, method_index)
        argtypes = []
        for i in range(num_args):
            argtype = charp2str(arg_type_method(self.name, method_index, i))
            argtypes.append(argtype)
        if is_constructor(self.name, method_index):
            cls = CPPConstructor
        elif is_static(self.name, method_index):
            cls = CPPFunction
        else:
            cls = CPPMethod
        return cls(self, method_index, result_type, argtypes)

    def invoke(self, name, args_w):
        overload = self.function_members[name]
        return overload.call(None, args_w)

    def construct(self, args_w):
        overload = self.function_members[self.name]
        return W_CPPObject(self, overload.call(None, args_w))

W_CPPType.typedef = TypeDef(
    'CPPType',
    invoke = interp2app(W_CPPType.invoke, unwrap_spec=['self', str, 'args_w']),
    construct = interp2app(W_CPPType.construct, unwrap_spec=['self', 'args_w']),
)



class W_CPPObject(Wrappable):
    def __init__(self, cppclass, rawobject):
        self.space = cppclass.space
        self.cppclass = cppclass
        self.rawobject = rawobject

    def invoke(self, method_name, args_w):
        overload = self.cppclass.function_members[method_name]
        result = overload.call(self.rawobject, args_w)
        return self.space.wrap(result)

    def destruct(self):
        destruct(self.cppclass.name, self.rawobject)

W_CPPObject.typedef = TypeDef(
    'CPPObject',
    invoke = interp2app(W_CPPObject.invoke, unwrap_spec=['self', str, 'args_w']),
    destruct = interp2app(W_CPPObject.destruct, unwrap_spec=['self']),
)
