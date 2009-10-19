from pypy.rpython.lltypesystem import llmemory
from pypy.rpython.lltypesystem.llarena_llinterp import Z_CLEAR_LARGE_AREA
from pypy.rpython.lltypesystem.llarena_llinterp import Z_CLEAR_SMALL_AREA
from pypy.rpython.lltypesystem.llarena_llinterp import Z_INACCESSIBLE

implements_inaccessible = False

# a random value, but nothing really depends on it
def getpagesize():
    return 4096

# llimpl_arena_*() functions based on raw_malloc
def llimpl_arena_malloc(nbytes, zero):
    addr = llmemory.raw_malloc(nbytes)
    if bool(addr):
        llimpl_arena_reset(addr, nbytes, zero)
    return addr

def llimpl_arena_free(arena_addr, nbytes):
    llmemory.raw_free(arena_addr)

def llimpl_arena_reset(arena_addr, size, zero):
    if zero in (Z_CLEAR_LARGE_AREA, Z_CLEAR_SMALL_AREA, Z_INACCESSIBLE):
        llmemory.raw_memclear(arena_addr, size)
