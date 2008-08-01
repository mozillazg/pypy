from pypy.rpython.tool import rffi_platform
from pypy.rpython.tool.rffi_platform import ConstantInteger
from pypy.rpython.tool.rffi_platform import SimpleType
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.rpython.lltypesystem import rffi, lltype

eci = ExternalCompilationInfo(
    includes = ["windows.h"]
    )

class CConfig:
    _compilation_info_ = eci

    SIZE_T                 = SimpleType('SIZE_T', rffi.LONG)
    DWORD                  = SimpleType('DWORD', rffi.LONG)
    BOOL                   = SimpleType('BOOL', rffi.INT)
    MEM_COMMIT             = ConstantInteger('MEM_COMMIT')
    MEM_RESERVE            = ConstantInteger('MEM_RESERVE')
    MEM_RELEASE            = ConstantInteger('MEM_RELEASE')
    PAGE_EXECUTE_READWRITE = ConstantInteger('PAGE_EXECUTE_READWRITE')

globals().update(rffi_platform.configure(CConfig))

def external(name, args, result):
    return rffi.llexternal(name, args, result, compilation_info=eci,
                           calling_conv='win')

DWORDP = rffi.CArrayPtr(DWORD)
PTR = rffi.VOIDP

# kernel32 is already part of the ExternalCompilationInfo
VirtualAlloc = external('VirtualAlloc',
                        [rffi.VOIDP, rffi.SIZE_T, DWORD, DWORD], rffi.VOIDP)
VirtualProtect = external('VirtualProtect',
                          [rffi.VOIDP, rffi.SIZE_T, DWORD, DWORDP], BOOL)
VirtualFree = external('VirtualFree',
                       [rffi.VOIDP, rffi.SIZE_T, DWORD], BOOL)

# ____________________________________________________________

def alloc(map_size):
    null = lltype.nullptr(rffi.VOIDP.TO)
    res = VirtualAlloc(null, map_size, MEM_COMMIT|MEM_RESERVE,
                       PAGE_EXECUTE_READWRITE)
    if not res:
        raise MemoryError
    arg = lltype.malloc(DWORDP.TO, 1, zero=True, flavor='raw')
    VirtualProtect(res, map_size, PAGE_EXECUTE_READWRITE, arg)
    lltype.free(arg, flavor='raw')
    # ignore errors, just try
    return res

def free(ptr, map_size):
    VirtualFree(ptr, 0, MEM_RELEASE)
