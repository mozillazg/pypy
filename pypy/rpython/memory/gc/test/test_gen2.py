from pypy.rpython.memory.gc import gen2

def test_arena():
    SHIFT = 4
    #
    a = gen2.Arena(SHIFT + 8*20, 8)
    assert a.freepages == a.arena_base + SHIFT
    assert a.nfreepages == 20
    #
    a = gen2.Arena(SHIFT + 8*20 + 7, 8)
    assert a.freepages == a.arena_base + SHIFT
    assert a.nfreepages == 20
