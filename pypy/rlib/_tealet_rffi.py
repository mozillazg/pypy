import os
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.translator.tool.cbuild import ExternalCompilationInfo

eci = ExternalCompilationInfo(
    includes=['src/tealet/tealet.h'],
    separate_module_sources=['#include "src/tealet/tealet.c"\n'],
    pre_include_bits=['#define TEALET_NO_SHARING'],
    )

def llexternal(funcname, args, restype):
    return rffi.llexternal(funcname, args, restype,
                           compilation_info=eci,
                           sandboxsafe=True, _nowrapper=True)

TEALET_P = rffi.COpaquePtr('tealet_t', compilation_info=eci)
TEALET_RUN_P = lltype.Ptr(lltype.FuncType([TEALET_P, rffi.VOIDP], TEALET_P))
NULL = lltype.nullptr(rffi.VOIDP.TO)
NULL_TEALET = lltype.nullptr(TEALET_P.TO)

tealet_initialize = llexternal("tealet_initialize", [rffi.VOIDP], TEALET_P)
tealet_finalize   = llexternal("tealet_finalize", [TEALET_P], lltype.Void)
tealet_new        = llexternal("tealet_new", [TEALET_P, TEALET_RUN_P,
                                              rffi.VOIDP], rffi.INT)
tealet_switch     = llexternal("tealet_switch", [TEALET_P], rffi.INT)
tealet_current    = llexternal("tealet_current", [TEALET_P], TEALET_P)

_tealet_translate_pointer = llexternal("_tealet_translate_pointer",
                                       [TEALET_P, llmemory.Address],
                                       llmemory.Address)
