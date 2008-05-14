from pypy.rpython.tool import rffi_pltform
from pypy.rpython.tool.rffi_platform import ConstantInteger
from pypy.rpython.tool.rffi_platform import SimpleType
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.rpython.lltypesystem import rffi

raise ImportError

class CConfig:
    _compilation_info_ = ExternalCompilationInfo(
        includes = "windows.h"
        )

    SIZE_T                 = SimpleType('SIZE_T', rffi.LONG)
    DWORD                  = SimpleType('DWORD', rffi.LONG)
    BOOL                   = SimpleType('BOOL', rffi.INT)
    MEM_COMMIT             = ConstantInteger('MEM_COMMIT')
    MEM_RESERVE            = ConstantInteger('MEM_RESERVE')
    MEM_RELEASE            = ConstantInteger('MEM_RELEASE')
    PAGE_EXECUTE_READWRITE = ConstantInteger('PAGE_EXECUTE_READWRITE')

globals().update(ctypes_platform.configure(CConfig))

# cannot use c_void_p as return value of functions :-(

# XXX how to get kernel32?
VirtualAlloc = ctypes.windll.kernel32.VirtualAlloc
VirtualAlloc.argtypes = [rffi.VOIDP, rffi.SIZE_T, DWORD, DWORD]
VirtualAlloc.restype = rffi.VOIDP

DWORD_P = rffi.CArrayPtr(DWORD)
VirtualProtect = ctypes.windll.kernel32.VirtualProtect
VirtualProtect.argtypes = [rffi.VOIDP, rffi.SIZE_T, DWORD, DWORD_P]
VirtualProtect.restype = BOOL

VirtualFree = ctypes.windll.kernel32.VirtualFree
VirtualFree.argtypes = [rffi.VOIDP, rffi.SIZE_T, DWORD]
VirtualFree.restype = BOOL

# ____________________________________________________________

def alloc(map_size):
    null = lltype.nullptr(rffi.VOIDP)
    res = VirtualAlloc(null, map_size, MEM_COMMIT|MEM_RESERVE,
                       PAGE_EXECUTE_READWRITE)
    if not res:
        raise MemoryError
    XXX # rewrite
    old = DWORD()
    VirtualProtect(res, map_size, PAGE_EXECUTE_READWRITE, ctypes.byref(old))
    # ignore errors, just try
    return res

def free(ptr, map_size):
    VirtualFree(ptr, 0, MEM_RELEASE)
