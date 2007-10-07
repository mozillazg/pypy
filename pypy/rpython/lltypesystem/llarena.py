import array
from pypy.rpython.lltypesystem import lltype, llmemory

# An "arena" is a large area of memory which can hold a number of
# objects, not necessarily all of the same type or size.  It's used by
# some of our framework GCs.  Addresses that point inside arenas support
# direct arithmetic: adding and subtracting integers, and taking the
# difference of two addresses.  When not translated to C, the arena
# keeps track of which bytes are used by what object to detect GC bugs;
# it internally uses raw_malloc_usage() to estimate the number of bytes
# it needs to reserve.

class ArenaError(Exception):
    pass

class Arena(object):

    def __init__(self, nbytes, zero):
        self.nbytes = nbytes
        self.usagemap = array.array('c')
        self.objects = {}
        self.freed = False
        self.reset(zero)

    def reset(self, zero):
        self.check()
        for obj in self.objects.itervalues():
            obj._free()
        self.objects.clear()
        if zero:
            initialbyte = "0"
        else:
            initialbyte = "#"
        self.usagemap[:] = array.array('c', initialbyte * self.nbytes)

    def check(self):
        if self.freed:
            raise ArenaError("arena was already freed")

    def _getid(self):
        address, length = self.usagemap.buffer_info()
        return address

    def getaddr(self, offset):
        if not (0 <= offset <= self.nbytes):
            raise ArenaError("Address offset is outside the arena")
        return fakearenaaddress(self, offset)

    def allocate_object(self, offset, TYPE):
        self.check()
        size = llmemory.raw_malloc_usage(llmemory.sizeof(TYPE))
        if offset + size > self.nbytes:
            raise ArenaError("object overflows beyond the end of the arena")
        zero = True
        for c in self.usagemap[offset:offset+size]:
            if c == '0':
                pass
            elif c == '#':
                zero = False
            else:
                raise ArenaError("new object overlaps a previous object")
        p = lltype.malloc(TYPE, flavor='raw', zero=zero)
        self.usagemap[offset:offset+size] = array.array('c', 'X' * size)
        self.objects[offset] = p._obj

class fakearenaaddress(llmemory.fakeaddress):

    def __init__(self, arena, offset):
        self.arena = arena
        self.offset = offset

    def _getptr(self):
        try:
            obj = self.arena.objects[self.offset]
        except KeyError:
            self.arena.check()
            raise ArenaError("don't know yet what type of object "
                             "is at offset %d" % (self.offset,))
        return obj._as_ptr()
    ptr = property(_getptr)

    def __repr__(self):
        return '<arenaaddr %s + %d>' % (self.arena, self.offset)

    def __add__(self, other):
        if isinstance(other, llmemory.AddressOffset):
            other = llmemory.raw_malloc_usage(other)
        if isinstance(other, (int, long)):
            return self.arena.getaddr(self.offset + other)
        return NotImplemented

    def __sub__(self, other):
        if isinstance(other, llmemory.AddressOffset):
            other = llmemory.raw_malloc_usage(other)
        if isinstance(other, (int, long)):
            return self.arena.getaddr(self.offset - other)
        if isinstance(other, fakearenaaddress):
            if self.other is not other.arena:
                raise ArenaError("The two addresses are from different arenas")
            return other.offset - self.offset
        return NotImplemented

    def __nonzero__(self):
        return True

    def __eq__(self, other):
        if isinstance(other, fakearenaaddress):
            return self.arena is other.arena and self.offset == other.offset
        elif isinstance(other, llmemory.fakeaddress) and not other:
            return False      # 'self' can't be equal to NULL
        else:
            return llmemory.fakeaddress.__eq__(self, other)

    def _cast_to_ptr(self, EXPECTED_TYPE):
        # the first cast determines what object type is at this address
        if self.offset not in self.arena.objects:
            self.arena.allocate_object(self.offset, EXPECTED_TYPE.TO)
        return llmemory.fakeaddress._cast_to_ptr(self, EXPECTED_TYPE)

    def _cast_to_int(self):
        return self.arena._getid() + self.offset

# ____________________________________________________________
#
# Public interface: arena_malloc(), arena_free() and arena_reset()
# which directly correspond to lloperations.  Although the operations
# are similar to raw_malloc(), raw_free() and raw_memclear(), the
# backend can choose a different implementation for arenas, one that
# is more suited to very large chunks of memory.

def arena_malloc(nbytes, zero):
    """Allocate and return a new arena, optionally zero-initialized."""
    return Arena(nbytes, zero).getaddr(0)

def arena_free(arena_addr):
    """Release an arena."""
    assert isinstance(arena_addr, fakearenaaddress)
    assert arena_addr.offset == 0
    arena_addr.arena.reset(False)
    arena_addr.arena.freed = True

def arena_reset(arena_addr, myarenasize, zero):
    """Free all objects in the arena, which can then be reused.
    The arena is filled with zeroes if 'zero' is True."""
    assert isinstance(arena_addr, fakearenaaddress)
    assert arena_addr.offset == 0
    assert myarenasize == arena_addr.arena.nbytes
    arena_addr.arena.reset(zero)
