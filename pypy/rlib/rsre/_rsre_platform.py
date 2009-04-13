
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.translator.tool.cbuild import ExternalCompilationInfo

eci = ExternalCompilationInfo(
    includes = ['ctype.h']
)

def external(name, args, result):
    return rffi.llexternal(name, args, result, compilation_info=eci)

tolower = external('tolower', [lltype.Signed], lltype.Signed)

