import os, sys
from pypy.rpython.tool import rffi_platform
from pypy.rpython.lltypesystem import rffi, lltype, llmemory
from pypy.rpython.lltypesystem.llarena_llinterp import Z_CLEAR_LARGE_AREA
from pypy.rpython.lltypesystem.llarena_llinterp import Z_CLEAR_SMALL_AREA
from pypy.rpython.lltypesystem.llarena_llinterp import Z_INACCESSIBLE
from pypy.rpython.lltypesystem.llarena_llinterp import Z_ACCESSIBLE
from pypy.rlib.rwin32 import DWORD, BOOL

implements_inaccessible = True

# ____________________________________________________________

class CConfig:
    _compilation_info_ = rffi_platform.ExternalCompilationInfo(
        includes=['windows.h'])

    SYSTEM_INFO = rffi_platform.Struct(
        'SYSTEM_INFO', [
            ("dwPageSize", DWORD),
            ])

config = rffi_platform.configure(CConfig)

SYSTEM_INFO = config['SYSTEM_INFO']
SYSTEM_INFO_P = lltype.Ptr(SYSTEM_INFO)

def winexternal(name, args, result):
    return rffi.llexternal(name, args, result,
                           compilation_info=CConfig._compilation_info_,
                           calling_conv='win')

# ____________________________________________________________

GetSystemInfo = winexternal('GetSystemInfo', [SYSTEM_INFO_P], lltype.Void)

class WinPageSize:
    def __init__(self):
        self.pagesize = 0
    _freeze_ = __init__
win_pagesize = WinPageSize()

def getpagesize():
    pagesize = win_pagesize.pagesize
    if pagesize == 0:
        si = rffi.make(SYSTEM_INFO)
        try:
            GetSystemInfo(si)
            pagesize = rffi.cast(lltype.Signed, si.c_dwPageSize)
        finally:
            lltype.free(si, flavor="raw")
        win_pagesize.pagesize = pagesize
    return pagesize

# ____________________________________________________________

VirtualAlloc = winexternal('VirtualAlloc', [llmemory.Address,
                                            rffi.SIZE_T, DWORD, DWORD],
                           llmemory.Address)
VirtualFree = winexternal('VirtualFree', [llmemory.Address,
                                          rffi.SIZE_T, DWORD],
                          BOOL)

MEM_COMMIT     = 0x1000
MEM_RESERVE    = 0x2000
MEM_DECOMMIT   = 0x4000
MEM_RELEASE    = 0x8000
PAGE_READWRITE = 0x04

class VirtualAllocMemoryError(Exception):
    pass

def _virtual_alloc(arena_addr, nbytes, flags, protect):
    result = VirtualFree(arena_addr,
                         rffi.cast(rffi.SIZE_T, nbytes),
                         rffi.cast(DWORD, flags),
                         rffi.cast(DWORD, protect))
    if result == llmemory.NULL:
        raise VirtualAllocMemoryError
    return result

def _virtual_free(arena_addr, nbytes, flags):
    result = VirtualFree(arena_addr,
                         rffi.cast(rffi.SIZE_T, nbytes),
                         rffi.cast(DWORD, flags))
    if rffi.cast(lltype.Signed, result) == 0:
        raise VirtualAllocMemoryError

def llimpl_arena_malloc(nbytes, zero):
    flAllocationType = MEM_RESERVE
    if zero != Z_INACCESSIBLE:
        flAllocationType |= MEM_COMMIT
    return _virtual_alloc(llmemory.NULL, nbytes,
                          flAllocationType, PAGE_READWRITE)

def llimpl_arena_free(arena_addr, nbytes):
    _virtual_free(arena_addr, 0, MEM_RELEASE)

def llimpl_arena_reset(arena_addr, size, zero):
    if zero == Z_CLEAR_LARGE_AREA:
        _virtual_free(arena_addr, size, MEM_DECOMMIT)
        _virtual_alloc(arena_addr, size, MEM_COMMIT, PAGE_READWRITE)
    elif zero == Z_CLEAR_SMALL_AREA:
        llmemory.raw_memclear(arena_addr, size)
    elif zero == Z_ACCESSIBLE:
        _virtual_alloc(arena_addr, size, MEM_COMMIT, PAGE_READWRITE)
    elif zero == Z_INACCESSIBLE:
        _virtual_free(arena_addr, size, MEM_DECOMMIT)
