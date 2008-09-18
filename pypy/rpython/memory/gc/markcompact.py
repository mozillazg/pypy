
from pypy.rpython.lltypesystem import lltype, llmemory, llarena
from pypy.rpython.memory.gc.base import MovingGCBase
from pypy.rpython.memory.gcheader import GCHeaderBuilder
from pypy.rlib.debug import ll_assert
from pypy.rpython.memory.support import DEFAULT_CHUNK_SIZE
from pypy.rpython.memory.support import get_address_stack, get_address_deque
from pypy.rpython.memory.support import AddressDict
from pypy.rpython.lltypesystem.llmemory import NULL, raw_malloc_usage
from pypy.rlib.rarithmetic import ovfcheck
from pypy.rpython.lltypesystem.lloperation import llop

GCFLAG_MARKBIT = MovingGCBase.first_unused_gcflag

memoryError = MemoryError()

class MarkCompactGC(MovingGCBase):
    HDR = lltype.Struct('header', ('tid', lltype.Signed))

    def __init__(self, chunk_size=DEFAULT_CHUNK_SIZE, space_size=16*(1024**2)):
        # space_size should be maximal available virtual memory.
        # this way we'll never need to copy anything nor implement
        # paging on our own
        self.space_size = space_size
        self.gcheaderbuilder = GCHeaderBuilder(self.HDR)
        self.AddressStack = get_address_stack(chunk_size)
        self.AddressDeque = get_address_deque(chunk_size)
        self.AddressDict = AddressDict
        self.counter = 0

    def setup(self):
        self.space = llarena.arena_malloc(self.space_size, True)
        ll_assert(bool(self.space), "couldn't allocate arena")
        self.spaceptr = self.space

    def init_gc_object(self, addr, typeid, flags=0):
        hdr = llmemory.cast_adr_to_ptr(addr, lltype.Ptr(self.HDR))
        hdr.tid = typeid | flags

    def malloc_fixedsize_clear(self, typeid, size, can_collect,
                               has_finalizer=False, contains_weakptr=False):
        assert can_collect
        size_gc_header = self.gcheaderbuilder.size_gc_header
        totalsize = size_gc_header + size
        self.eventually_collect()
        result = self.spaceptr
        llarena.arena_reserve(result, totalsize)
        self.init_gc_object(result, typeid)
        self.spaceptr += totalsize
        return llmemory.cast_adr_to_ptr(result+size_gc_header, llmemory.GCREF)
    
    def malloc_varsize_clear(self, typeid, length, size, itemsize,
                             offset_to_length, can_collect,
                             has_finalizer=False):
        assert can_collect
        size_gc_header = self.gcheaderbuilder.size_gc_header
        nonvarsize = size_gc_header + size
        try:
            varsize = ovfcheck(itemsize * length)
            totalsize = ovfcheck(nonvarsize + varsize)
        except OverflowError:
            raise memoryError
        self.eventually_collect()
        result = self.spaceptr
        llarena.arena_reserve(result, totalsize)
        self.init_gc_object(result, typeid)
        (result + size_gc_header + offset_to_length).signed[0] = length
        self.spaceptr = result + llarena.round_up_for_allocation(totalsize)
        # XXX has_finalizer etc.
        return llmemory.cast_adr_to_ptr(result+size_gc_header, llmemory.GCREF)

    def eventually_collect(self):
        # XXX this is a very bad idea, come up with better heuristics
        # XXX it also does not check can_collect flag
        self.counter += 1
        if self.counter == 1000:
            self.collect()
            self.counter = 0

    def collect(self):
        self.debug_check_consistency()
        self.mark()
        self.compact()
        self.update_forward_refs()
        self.debug_check_consistency()

    def compact(self):
        self.forwardrefs = self.AddressDict()
        fromaddr = self.space
        toaddr = self.space
        size_gc_header = self.gcheaderbuilder.size_gc_header
        while fromaddr < self.spaceptr:
            hdr = llmemory.cast_adr_to_ptr(fromaddr, lltype.Ptr(self.HDR))
            obj = fromaddr + size_gc_header
            objsize = self.get_size(obj)
            totalsize = size_gc_header + objsize
            if not hdr.tid & GCFLAG_MARKBIT: 
                # this object dies, clear arena                
                llarena.arena_reset(fromaddr, totalsize, True)
            else:
                # this objects survives, clear MARKBIT
                hdr.tid &= ~GCFLAG_MARKBIT
                if fromaddr != toaddr:
                    # this object needs to be copied somewhere

                    # first approach - copy object if possible, otherwise
                    # copy it somewhere else and keep track of that
                    self.forwardrefs.setitem(fromaddr, toaddr)
                    if toaddr + totalsize > fromaddr:
                        # this is the worst possible scenario: object does
                        # not fit inside space to copy
                        xxx
                    else:
                        # object fits there: copy
                        llop.debug_print(lltype.Void, fromaddr, "copied to", toaddr,
                                         "tid", self.header(obj).tid,
                                         "size", totalsize)
                        llarena.arena_reserve(toaddr, totalsize)
                        llmemory.raw_memcopy(obj - size_gc_header, toaddr, totalsize)
                        llarena.arena_reset(fromaddr, totalsize, True)
                toaddr += size_gc_header + objsize
            fromaddr += size_gc_header + objsize
        self.spaceptr = toaddr

    def update_forward_refs(self):
        ptr = self.space
        size_gc_header = self.gcheaderbuilder.size_gc_header
        while ptr < self.spaceptr:
            obj = ptr + size_gc_header
            objsize = self.get_size(obj)
            totalsize = size_gc_header + objsize
            self.trace(obj, self._trace_copy, None)
            ptr += totalsize
        self.forwardrefs = None

    def _trace_copy(self, pointer, ignored):
        addr = pointer.address[0]
        if addr != NULL:
            pointer.address[0] = self.forwardrefs.get(addr, addr)

    def mark(self):
        self.root_walker.walk_roots(
            MarkCompactGC._mark_object,  # stack roots
            MarkCompactGC._mark_object,  # static in prebuilt non-gc structures
            MarkCompactGC._mark_object)  # static in prebuilt gc objects

    def _mark_object(self, pointer, ignored=None):
        obj = pointer.address[0]
        if obj != NULL:
            self.header(obj).tid |= GCFLAG_MARKBIT
            self.trace(obj, self._mark_object, None)
