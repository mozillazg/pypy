import array, weakref
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

class InaccessibleArenaError(ArenaError):
    pass

class Arena(object):
    object_arena_location = {}     # {container: (arena, offset)}
    old_object_arena_location = weakref.WeakKeyDictionary()

    def __init__(self, nbytes, zero):
        self.nbytes = nbytes
        self.usagemap = array.array('c')
        self.objectptrs = {}        # {offset: ptr-to-container}
        self.objectsizes = {}       # {offset: size}
        self.freed = False
        self.reset(zero)

    def reset(self, zero, start=0, size=None):
        self.check()
        if size is None:
            stop = self.nbytes
        else:
            stop = start + llmemory.raw_malloc_usage(size)
        assert 0 <= start <= stop <= self.nbytes
        for offset, ptr in self.objectptrs.items():
            size = self.objectsizes[offset]
            if offset < start:   # object is before the cleared area
                assert offset + size <= start, "object overlaps cleared area"
            elif offset + size > stop:  # object is after the cleared area
                assert offset >= stop, "object overlaps cleared area"
            else:
                obj = ptr._obj
                del Arena.object_arena_location[obj]
                del self.objectptrs[offset]
                del self.objectsizes[offset]
                obj._free()
        if zero == Z_DONT_CLEAR:
            initialbyte = "#"
        elif zero in (Z_CLEAR_LARGE_AREA, Z_CLEAR_SMALL_AREA):
            initialbyte = "0"
        elif zero == Z_INACCESSIBLE:
            prev  = self.usagemap[start:stop].tostring()
            assert '!' not in prev, (
                "Z_INACCESSIBLE must be called only on a "
                "previously-accessible memory range")
            initialbyte = "!"
        elif zero == Z_ACCESSIBLE:
            prev  = self.usagemap[start:stop].tostring()
            assert prev == '!'*len(prev), (
                "Z_ACCESSIBLE must be called only on a "
                "previously-inaccessible memory range")
            initialbyte = "0"
        else:
            raise ValueError("argument 'zero' got bogus value %r" % (zero,))
        self.usagemap[start:stop] = array.array('c', initialbyte*(stop-start))

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

    def allocate_object(self, offset, size):
        self.check()
        bytes = llmemory.raw_malloc_usage(size)
        if offset + bytes > self.nbytes:
            raise ArenaError("object overflows beyond the end of the arena")
        zero = True
        for c in self.usagemap[offset:offset+bytes]:
            if c == '0':
                pass
            elif c == '#':
                zero = False
            elif c == '!':
                raise InaccessibleArenaError
            else:
                raise ArenaError("new object overlaps a previous object")
        assert offset not in self.objectptrs
        addr2 = size._raw_malloc([], zero=zero)
        pattern = 'X' + 'x'*(bytes-1)
        self.usagemap[offset:offset+bytes] = array.array('c', pattern)
        self.setobject(addr2, offset, bytes)
        # common case: 'size' starts with a GCHeaderOffset.  In this case
        # we can also remember that the real object starts after the header.
        while isinstance(size, RoundedUpForAllocation):
            size = size.basesize
        if (isinstance(size, llmemory.CompositeOffset) and
            isinstance(size.offsets[0], llmemory.GCHeaderOffset)):
            objaddr = addr2 + size.offsets[0]
            hdrbytes = llmemory.raw_malloc_usage(size.offsets[0])
            objoffset = offset + hdrbytes
            self.setobject(objaddr, objoffset, bytes - hdrbytes)
        return addr2

    def setobject(self, objaddr, offset, bytes):
        assert bytes > 0, ("llarena does not support GcStructs with no field"
                           " or empty arrays")
        assert offset not in self.objectptrs
        self.objectptrs[offset] = objaddr.ptr
        self.objectsizes[offset] = bytes
        container = objaddr.ptr._obj
        Arena.object_arena_location[container] = self, offset
        Arena.old_object_arena_location[container] = self, offset

class fakearenaaddress(llmemory.fakeaddress):

    def __init__(self, arena, offset):
        self.arena = arena
        self.offset = offset

    def _getptr(self):
        try:
            return self.arena.objectptrs[self.offset]
        except KeyError:
            self.arena.check()
            raise ArenaError("don't know yet what type of object "
                             "is at offset %d" % (self.offset,))
    ptr = property(_getptr)

    def __repr__(self):
        return '<arenaaddr %s + %d>' % (self.arena, self.offset)

    def __add__(self, other):
        if isinstance(other, (int, long)):
            position = self.offset + other
        elif isinstance(other, llmemory.AddressOffset):
            # this is really some Do What I Mean logic.  There are two
            # possible meanings: either we want to go past the current
            # object in the arena, or we want to take the address inside
            # the current object.  Try to guess...
            bytes = llmemory.raw_malloc_usage(other)
            if (self.offset in self.arena.objectsizes and
                bytes < self.arena.objectsizes[self.offset]):
                # looks like we mean "inside the object"
                return llmemory.fakeaddress.__add__(self, other)
            position = self.offset + bytes
        else:
            return NotImplemented
        return self.arena.getaddr(position)

    def __sub__(self, other):
        if isinstance(other, llmemory.AddressOffset):
            other = llmemory.raw_malloc_usage(other)
        if isinstance(other, (int, long)):
            return self.arena.getaddr(self.offset - other)
        if isinstance(other, fakearenaaddress):
            if self.arena is not other.arena:
                raise ArenaError("The two addresses are from different arenas")
            return self.offset - other.offset
        return NotImplemented

    def __nonzero__(self):
        return True

    def compare_with_fakeaddr(self, other):
        other = other._fixup()
        if not other:
            return None, None
        obj = other.ptr._obj
        innerobject = False
        while obj not in Arena.object_arena_location:
            obj = obj._parentstructure()
            if obj is None:
                return None, None     # not found in the arena
            innerobject = True
        arena, offset = Arena.object_arena_location[obj]
        if innerobject:
            # 'obj' is really inside the object allocated from the arena,
            # so it's likely that its address "should be" a bit larger than
            # what 'offset' says.
            # We could estimate the correct offset but it's a bit messy;
            # instead, let's check the answer doesn't depend on it
            if self.arena is arena:
                objectsize = arena.objectsizes[offset]
                if offset < self.offset < offset+objectsize:
                    raise AssertionError(
                        "comparing an inner address with a "
                        "fakearenaaddress that points in the "
                        "middle of the same object")
                offset += objectsize // 2      # arbitrary
        return arena, offset

    def __eq__(self, other):
        if isinstance(other, fakearenaaddress):
            arena = other.arena
            offset = other.offset
        elif isinstance(other, llmemory.fakeaddress):
            arena, offset = self.compare_with_fakeaddr(other)
        else:
            return llmemory.fakeaddress.__eq__(self, other)
        return self.arena is arena and self.offset == offset

    def __lt__(self, other):
        if isinstance(other, fakearenaaddress):
            arena = other.arena
            offset = other.offset
        elif isinstance(other, llmemory.fakeaddress):
            arena, offset = self.compare_with_fakeaddr(other)
            if arena is None:
                return False       # self < other-not-in-any-arena  => False
                                   # (arbitrarily)
        else:
            raise TypeError("comparing a %s and a %s" % (
                self.__class__.__name__, other.__class__.__name__))
        if self.arena is arena:
            return self.offset < offset
        else:
            return self.arena._getid() < arena._getid()

    def _cast_to_int(self):
        return self.arena._getid() + self.offset


def _getfakearenaaddress(addr):
    """Logic to handle test_replace_object_with_stub()."""
    if isinstance(addr, fakearenaaddress):
        return addr
    else:
        assert isinstance(addr, llmemory.fakeaddress)
        assert addr, "NULL address"
        # it must be possible to use the address of an already-freed
        # arena object
        obj = addr.ptr._getobj(check=False)
        return _oldobj_to_address(obj)

def _oldobj_to_address(obj):
    obj = obj._normalizedcontainer(check=False)
    try:
        arena, offset = Arena.old_object_arena_location[obj]
    except KeyError:
        if obj._was_freed():
            msg = "taking address of %r, but it was freed"
        else:
            msg = "taking address of %r, but it is not in an arena"
        raise RuntimeError(msg % (obj,))
    return arena.getaddr(offset)

class RoundedUpForAllocation(llmemory.AddressOffset):
    """A size that is rounded up in order to preserve alignment of objects
    following it.  For arenas containing heterogenous objects.
    """
    def __init__(self, basesize, minsize):
        assert isinstance(basesize, llmemory.AddressOffset)
        assert isinstance(minsize, llmemory.AddressOffset) or minsize == 0
        self.basesize = basesize
        self.minsize = minsize

    def __repr__(self):
        return '< RoundedUpForAllocation %r %r >' % (self.basesize,
                                                     self.minsize)

    def known_nonneg(self):
        return self.basesize.known_nonneg()

    def ref(self, ptr):
        return self.basesize.ref(ptr)

    def _raw_malloc(self, rest, zero):
        return self.basesize._raw_malloc(rest, zero=zero)

    def raw_memcopy(self, srcadr, dstadr):
        self.basesize.raw_memcopy(srcadr, dstadr)

# ____________________________________________________________
#
# Public interface: arena_malloc(), arena_free(), arena_reset()
# are similar to raw_malloc(), raw_free() and raw_memclear(), but
# work with fakearenaaddresses on which arbitrary arithmetic is
# possible even on top of the llinterpreter.

# arena_malloc() and arena_reset() take as argument one of the
# following values:

Z_DONT_CLEAR       = 0   # it's ok to keep random bytes in the area
Z_CLEAR_LARGE_AREA = 1   # clear, optimized for a large area of memory
Z_CLEAR_SMALL_AREA = 2   # clear, optimized for a small or medium area of mem
Z_INACCESSIBLE     = 3   # make the memory inaccessible (not reserved)
Z_ACCESSIBLE       = 4   # make the memory accessible again

# Note that Z_CLEAR_LARGE_AREA, Z_INACCESSIBLE and Z_ACCESSIBLE are
# restricted to whole pages (at least one), and you must not try to make
# inaccessible pages that are already inaccessible, nor make accessible
# pages that are already accessible.
# When they go through the Z_INACCESSIBLE-Z_ACCESSIBLE trip, pages are
# cleared.

def arena_malloc(nbytes, zero):
    """Allocate and return a new arena, optionally zero-initialized.
    The value of 'zero' is one the Z_xxx values.
    """
    return Arena(nbytes, zero).getaddr(0)

def arena_free(arena_addr, nbytes):
    """Release an arena."""
    assert isinstance(arena_addr, fakearenaaddress)
    assert arena_addr.offset == 0
    assert nbytes == arena_addr.arena.nbytes
    arena_addr.arena.reset(Z_DONT_CLEAR)
    arena_addr.arena.freed = True

def arena_reset(arena_addr, size, zero):
    """Free all objects in the arena, which can then be reused.
    This can also be used on a subrange of the arena.
    The value of 'zero' is one of the Z_xxx values.
    """
    arena_addr = _getfakearenaaddress(arena_addr)
    arena_addr.arena.reset(zero, arena_addr.offset, size)

def arena_reserve(addr, size, check_alignment=True):
    """Mark some bytes in an arena as reserved, and returns addr.
    For debugging this can check that reserved ranges of bytes don't
    overlap.  The size must be symbolic; in non-translated version
    this is used to know what type of lltype object to allocate."""
    from pypy.rpython.memory.lltypelayout import memory_alignment
    addr = _getfakearenaaddress(addr)
    if check_alignment and (addr.offset & (memory_alignment-1)) != 0:
        raise ArenaError("object at offset %d would not be correctly aligned"
                         % (addr.offset,))
    addr.arena.allocate_object(addr.offset, size)

def round_up_for_allocation(size, minsize=0):
    """Round up the size in order to preserve alignment of objects
    following an object.  For arenas containing heterogenous objects.
    If minsize is specified, it gives a minimum on the resulting size."""
    return internal_round_up_for_allocation(size, minsize)

def internal_round_up_for_allocation(size, minsize):    # internal
    return RoundedUpForAllocation(size, minsize)

def arena_new_view(ptr):
    """This is a no-op when translated, returns fresh view
    on previous arena when run on top of llinterp.
    """
    return Arena(ptr.arena.nbytes, False).getaddr(0)
