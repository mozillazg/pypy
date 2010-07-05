import py, os

from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import ObjSpace, interp2app
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.baseobjspace import Wrappable

from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.rpython.lltypesystem import rffi, lltype

from pypy.rlib.libffi import CDLL


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
    [rffi.CCHARP, rffi.CCHARP, rffi.INT, rffi.VOIDPP], rffi.LONG,
    compilation_info=eci)
construct = rffi.llexternal(
    "construct",
    [rffi.CCHARP, rffi.INT, rffi.VOIDPP], rffi.VOIDP,
    compilation_info=eci)
callmethod_l = rffi.llexternal(
    "callmethod_l",
    [rffi.CCHARP, rffi.CCHARP, rffi.VOIDP, rffi.INT, rffi.VOIDPP], rffi.LONG,
    compilation_info=eci)



def load_lib(space, name):
    cdll = CDLL(name)
    return W_CPPLibrary(space, cdll)
load_lib.unwrap_spec = [ObjSpace, str]

def prepare_arguments(space, args_w):
    args = lltype.malloc(rffi.CArray(rffi.VOIDP), len(args_w), flavor='raw')
    for i in range(len(args_w)):
        arg = space.int_w(args_w[i])
        x = lltype.malloc(rffi.LONGP.TO, 1, flavor='raw')
        x[0] = arg
        args[i] = rffi.cast(rffi.VOIDP, x)
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


class W_CPPType(Wrappable):
    def __init__(self, cpplib, name):
        self.space = cpplib.space
        self.cpplib = cpplib
        self.name = name

    def invoke(self, name, args_w):
        args = prepare_arguments(self.space, args_w)
        result = callstatic_l(self.name, name, len(args_w), args)
        free_arguments(args, len(args_w))
        return self.space.wrap(result)

    def construct(self, args_w):
        args = prepare_arguments(self.space, args_w)
        result = construct(self.name, len(args_w), args)
        free_arguments(args, len(args_w))
        return W_CPPObject(self, result)

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
        args = prepare_arguments(self.space, args_w)
        result = callmethod_l(self.cppclass.name, method_name,
                              self.rawobject, len(args_w), args)
        free_arguments(args, len(args_w))
        return self.space.wrap(result)


W_CPPObject.typedef = TypeDef(
    'CPPObject',
    invoke = interp2app(W_CPPObject.invoke, unwrap_spec=['self', str, 'args_w']),
)
