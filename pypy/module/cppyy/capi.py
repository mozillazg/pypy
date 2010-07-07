import py, os

from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.rpython.lltypesystem import rffi, lltype

srcpath = py.path.local(__file__).dirpath().join("src")
incpath = py.path.local(__file__).dirpath().join("include")

try:
   rootincpath = os.path.join(os.environ["ROOTSYS"], "include")
   rootlibpath = os.path.join(os.environ["ROOTSYS"], "lib")
except KeyError:
   print 'please set ROOTSYS envar to the location of the ROOT installation'
   raise

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

def charp2str_free(charp):
    string = rffi.charp2str(charp)
    c_myfree(charp)
    return string
