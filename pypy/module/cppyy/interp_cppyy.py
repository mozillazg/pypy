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


def load_lib(space, name):
    cdll = CDLL(name)
    return W_CPPLibrary(space, cdll)
load_lib.unwrap_spec = [ObjSpace, str]

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
        args = lltype.malloc(rffi.CArray(rffi.VOIDP), len(args_w), flavor='raw')
        for i in range(len(args_w)):
            arg = self.space.int_w(args_w[i])
            x = lltype.malloc(rffi.LONGP.TO, 1, flavor='raw')
            x[0] = arg
            args[i] = rffi.cast(rffi.VOIDP, x)
        result = callstatic_l(self.name, name, len(args_w), args)
        for i in range(len(args_w)):
            lltype.free(args[i], flavor='raw')
        lltype.free(args, flavor='raw')
        return self.space.wrap(result)

    def construct(self, args_w):
        xxx

W_CPPType.typedef = TypeDef(
    'CPPType',
    invoke = interp2app(W_CPPType.invoke, unwrap_spec=['self', str, 'args_w']),
    construct = interp2app(W_CPPType.construct, unwrap_spec=['self', 'args_w']),
)
