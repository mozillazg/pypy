
# An "arena" is a large area of memory which can hold a number of
# objects, not necessarily all of the same type or size.  It's used by
# some of our framework GCs.
#
# See further comments in llarena_llinterp.py.

from pypy.rpython.lltypesystem.llarena_llinterp import *

# ____________________________________________________________
#
# Translation support: the functions above turn into the code below.
# We can tweak these implementations to be more suited to very large
# chunks of memory.

import os
from pypy.rpython.extfunc import register_external
from pypy.rpython.lltypesystem import rffi

if os.name == 'posix':
    from pypy.rpython.lltypesystem import llarena_posix as llarena_impl
elif os.name == 'nt':
    from pypy.rpython.lltypesystem import llarena_nt as llarena_impl
else:
    from pypy.rpython.lltypesystem import llarena_generic as llarena_impl


implements_inaccessible = llarena_impl.implements_inaccessible
getpagesize = llarena_impl.getpagesize
OutOfMemoryError = llarena_impl.OutOfMemoryError

register_external(arena_malloc, [int, int], llmemory.Address,
                  'll_arena.arena_malloc',
                  llimpl=llarena_impl.llimpl_arena_malloc,
                  llfakeimpl=arena_malloc,
                  sandboxsafe=True)

register_external(arena_free, [llmemory.Address, int], None,
                  'll_arena.arena_free',
                  llimpl=llarena_impl.llimpl_arena_free,
                  llfakeimpl=arena_free,
                  sandboxsafe=True)

register_external(arena_reset, [llmemory.Address, int, int], None,
                  'll_arena.arena_reset',
                  llimpl=llarena_impl.llimpl_arena_reset,
                  llfakeimpl=arena_reset,
                  sandboxsafe=True)

def llimpl_arena_reserve(addr, size):
    pass
register_external(arena_reserve, [llmemory.Address, int], None,
                  'll_arena.arena_reserve',
                  llimpl=llimpl_arena_reserve,
                  llfakeimpl=arena_reserve,
                  sandboxsafe=True)

llimpl_round_up_for_allocation = rffi.llexternal('ROUND_UP_FOR_ALLOCATION',
                                                [lltype.Signed, lltype.Signed],
                                                 lltype.Signed,
                                                 sandboxsafe=True,
                                                 _nowrapper=True)
register_external(internal_round_up_for_allocation, [int, int], int,
                  'll_arena.round_up_for_allocation',
                  llimpl=llimpl_round_up_for_allocation,
                  llfakeimpl=round_up_for_allocation,
                  sandboxsafe=True)

def llimpl_arena_new_view(addr):
    return addr
register_external(arena_new_view, [llmemory.Address], llmemory.Address,
                  'll_arena.arena_new_view', llimpl=llimpl_arena_new_view,
                  llfakeimpl=arena_new_view, sandboxsafe=True)
