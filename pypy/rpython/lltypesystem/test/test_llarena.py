import py
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.lltypesystem.llmemory import cast_adr_to_ptr
from pypy.rpython.lltypesystem.llarena import arena_malloc, arena_reset
from pypy.rpython.lltypesystem.llarena import ArenaError

def test_arena():
    S = lltype.Struct('S', ('x',lltype.Signed))
    SPTR = lltype.Ptr(S)
    ssize = llmemory.raw_malloc_usage(llmemory.sizeof(S))
    myarenasize = 2*ssize+1
    a = arena_malloc(myarenasize, False)
    assert a != llmemory.NULL
    assert a + 3 != llmemory.NULL

    s1_ptr1 = cast_adr_to_ptr(a, SPTR)
    s1_ptr1.x = 1
    s1_ptr2 = cast_adr_to_ptr(a, SPTR)
    assert s1_ptr2.x == 1
    assert s1_ptr1 == s1_ptr2

    s2_ptr1 = cast_adr_to_ptr(a + ssize + 1, SPTR)
    py.test.raises(lltype.UninitializedMemoryAccess, 's2_ptr1.x')
    s2_ptr1.x = 2
    s2_ptr2 = cast_adr_to_ptr(a + ssize + 1, SPTR)
    assert s2_ptr2.x == 2
    assert s2_ptr1 == s2_ptr2
    assert s1_ptr1 != s2_ptr1
    assert not (s2_ptr2 == s1_ptr2)
    assert s1_ptr1 == cast_adr_to_ptr(a, SPTR)

    S2 = lltype.Struct('S2', ('y',lltype.Char))
    S2PTR = lltype.Ptr(S2)
    py.test.raises(TypeError, cast_adr_to_ptr, a, S2PTR)
    py.test.raises(ArenaError, cast_adr_to_ptr, a+1, SPTR)
    py.test.raises(ArenaError, cast_adr_to_ptr, a+ssize, SPTR)
    py.test.raises(ArenaError, cast_adr_to_ptr, a+2*ssize, SPTR)
    py.test.raises(ArenaError, cast_adr_to_ptr, a+2*ssize+1, SPTR)

    arena_reset(a, myarenasize, True)
    s1_ptr1 = cast_adr_to_ptr(a, SPTR)
    assert s1_ptr1.x == 0
    s1_ptr1.x = 5

    s2_ptr1 = cast_adr_to_ptr(a + ssize, S2PTR)
    assert s2_ptr1.y == '\x00'
    s2_ptr1.y = 'X'

    assert cast_adr_to_ptr(a + 0, SPTR).x == 5
    assert cast_adr_to_ptr((a + ssize + 1) - 1, S2PTR).y == 'X'
