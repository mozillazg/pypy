import py, os

from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.rpython.lltypesystem import rffi, lltype

srcpath = py.path.local(__file__).dirpath().join("src")
incpath = py.path.local(__file__).dirpath().join("include")

if os.environ.get("ROOTSYS"):
    rootincpath = [os.path.join(os.environ["ROOTSYS"], "include")]
    rootlibpath = [os.path.join(os.environ["ROOTSYS"], "lib")]
else:
    rootincpath = []
    rootlibpath = []

eci = ExternalCompilationInfo(
    separate_module_files=[srcpath.join("reflexcwrapper.cxx")],
    include_dirs=[incpath] + rootincpath,
    includes=["reflexcwrapper.h"],
    library_dirs=rootlibpath,
    libraries=["Reflex"],
    use_cpp_linker=True,
)

C_TYPEHANDLE = rffi.VOIDP
C_OBJECT = rffi.VOIDP

C_METHPTRGETTER = lltype.FuncType([C_OBJECT], rffi.VOIDP)
C_METHPTRGETTER_PTR = lltype.Ptr(C_METHPTRGETTER)

c_cppyy_get_typehandle = rffi.llexternal(
    "cppyy_get_typehandle",
    [rffi.CCHARP], C_TYPEHANDLE,
    compilation_info=eci)

c_cppyy_allocate = rffi.llexternal(
    "cppyy_allocate",
    [C_TYPEHANDLE], rffi.VOIDP,
    compilation_info=eci)
c_cppyy_deallocate = rffi.llexternal(
    "cppyy_deallocate",
    [C_TYPEHANDLE, C_OBJECT], rffi.VOIDP,
    compilation_info=eci)
c_cppyy_call_v = rffi.llexternal(
    "cppyy_call_v",
    [C_TYPEHANDLE, rffi.INT, C_OBJECT, rffi.INT, rffi.VOIDPP], lltype.Void,
    compilation_info=eci)
c_cppyy_call_l = rffi.llexternal(
    "cppyy_call_l",
    [C_TYPEHANDLE, rffi.INT, C_OBJECT, rffi.INT, rffi.VOIDPP], rffi.LONG,
    compilation_info=eci)
c_cppyy_call_d = rffi.llexternal(
    "cppyy_call_d",
    [C_TYPEHANDLE, rffi.INT, C_OBJECT, rffi.INT, rffi.VOIDPP], rffi.DOUBLE,
    compilation_info=eci)
c_cppyy_destruct = rffi.llexternal(
    "cppyy_destruct",
    [C_TYPEHANDLE, C_OBJECT], lltype.Void,
    compilation_info=eci)
c_cppyy_get_methptr_getter = rffi.llexternal(
    "cppyy_get_methptr_getter",
    [C_TYPEHANDLE, rffi.INT], C_METHPTRGETTER_PTR,
    compilation_info=eci)


c_num_methods = rffi.llexternal(
    "num_methods",
    [C_TYPEHANDLE], rffi.INT,
    compilation_info=eci)
c_method_name = rffi.llexternal(
    "method_name",
    [C_TYPEHANDLE, rffi.INT], rffi.CCHARP,
    compilation_info=eci)
c_result_type_method = rffi.llexternal(
    "result_type_method",
    [C_TYPEHANDLE, rffi.INT], rffi.CCHARP,
    compilation_info=eci)
c_num_args_method = rffi.llexternal(
    "num_args_method",
    [C_TYPEHANDLE, rffi.INT], rffi.INT,
    compilation_info=eci)
c_arg_type_method = rffi.llexternal(
    "arg_type_method",
    [C_TYPEHANDLE, rffi.INT, rffi.INT], rffi.CCHARP,
    compilation_info=eci)
c_is_constructor = rffi.llexternal(
    "is_constructor",
    [C_TYPEHANDLE, rffi.INT], rffi.INT,
    compilation_info=eci)
c_is_static = rffi.llexternal(
    "is_static",
    [C_TYPEHANDLE, rffi.INT], rffi.INT,
    compilation_info=eci)
c_is_subtype = rffi.llexternal(
    "is_subtype",
    [C_TYPEHANDLE, C_TYPEHANDLE], rffi.INT,
    compilation_info=eci)
c_dynamic_type = rffi.llexternal(
    "dynamic_type",
    [C_TYPEHANDLE, C_OBJECT], C_TYPEHANDLE,
    compilation_info=eci)

c_myfree = rffi.llexternal(
    "myfree",
    [rffi.VOIDP], lltype.Void,
    compilation_info=eci)

def charp2str_free(charp):
    string = rffi.charp2str(charp)
    c_myfree(charp)
    return string
