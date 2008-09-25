
from pypy.rpython.lltypesystem import lltype, llmemory, llarena
from pypy.rpython.memory.gc.base import MovingGCBase, \
     TYPEID_MASK, GCFLAG_FINALIZATION_ORDERING
from pypy.rlib.debug import ll_assert
from pypy.rpython.memory.support import DEFAULT_CHUNK_SIZE
from pypy.rpython.memory.support import get_address_stack, get_address_deque
from pypy.rpython.memory.support import AddressDict
from pypy.rpython.lltypesystem.llmemory import NULL, raw_malloc_usage
from pypy.rlib.rarithmetic import ovfcheck
from pypy.rpython.lltypesystem.lloperation import llop

GCFLAG_MARKBIT = MovingGCBase.first_unused_gcflag

memoryError = MemoryError()

# Mark'n'compact garbage collector
#
# main point of this GC is to save as much memory as possible
# (not to be worse than semispace), but avoid having peaks of
# memory during collection. Inspired, at least partly by squeak's
# garbage collector

# so, the idea as now is:

# we allocate space (full of zeroes) which is big enough to handle
# all possible cases. Because it's full of zeroes, we never allocate
# it really, unless we start using it

# for each collection we mark objects which are alive, also marking all
# for which we want to run finalizers. we mark them by storing forward
# pointer, which will be a place to copy them. After that, we copy all
# using memmove to another view of the same space, hence compacting
# everything

class MarkCompactGC(MovingGCBase):
    HDR = lltype.Struct('header', ('tid', lltype.Signed),
                        ('forward_ptr', llmemory.Address))

    def __init__(self, chunk_size=DEFAULT_CHUNK_SIZE, space_size=16*(1024**2)):
        # space_size should be maximal available virtual memory.
        # this way we'll never need to copy anything nor implement
        # paging on our own
        self.space_size = space_size
        MovingGCBase.__init__(self, chunk_size)
        self.counter = 0

    def setup(self):
        self.space = llarena.arena_malloc(self.space_size, True)
        ll_assert(bool(self.space), "couldn't allocate arena")
        self.spaceptr = self.space
        MovingGCBase.setup(self)

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
        if has_finalizer:
            self.objects_with_finalizers.append(result + size_gc_header)
        if contains_weakptr:
            self.objects_with_weakrefs.append(result + size_gc_header)
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
        if has_finalizer:
            self.objects_with_finalizers.append(result + size_gc_header)
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
        if self.run_finalizers.non_empty():
            self.update_run_finalizers()
        if self.objects_with_finalizers.non_empty():
            self.deal_with_objects_with_finalizers(None)
        if self.objects_with_weakrefs.non_empty():
            self.invalidate_weakrefs()
        self.debug_check_consistency()
        toaddr = llarena.arena_new_view(self.space)
        self.debug_check_consistency()
        self.compact(toaddr)
        self.space = toaddr
        self.debug_check_consistency()

    def get_type_id(self, addr):
        return self.header(addr).tid & TYPEID_MASK

    def compact(self, toaddr):
        fromaddr = self.space
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
                if hdr.tid & GCFLAG_FORWARDED:
                    # this object needs to be copied somewhere
                    # first approach - copy object if possible, otherwise
                    # copy it somewhere else and keep track of that
                    if toaddr + totalsize > fromaddr:
                        # this is the worst possible scenario: object does
                        # not fit inside space to copy
                        xxx
                    else:
                        # object fits there: copy
                        hdr.tid &= ~(GCFLAG_MARKBIT|GCFLAG_FORWARDED)
                        #llop.debug_print(lltype.Void, fromaddr, "copied to", toaddr,
                        #                 "tid", self.header(obj).tid,
                        #                 "size", totalsize)
                        llmemory.raw_memcopy(obj - size_gc_header, toaddr, totalsize)
                        llarena.arena_reset(fromaddr, totalsize, True)
                else:
                    hdr.tid &= ~(GCFLAG_MARKBIT|GCFLAG_FORWARDED)
                    # XXX this is here only to make llarena happier, makes no
                    #     sense whatsoever, need to disable it when translated
                    llarena.arena_reserve(toaddr, totalsize)
                    llmemory.raw_memcopy(obj - size_gc_header, toaddr, totalsize)
                toaddr += size_gc_header + objsize
            fromaddr += size_gc_header + objsize
        self.spaceptr = toaddr

    def update_forward_refs(self):
        self.root_walker.walk_roots(
            MarkCompactGC._trace_copy,  # stack roots
            MarkCompactGC._trace_copy,  # static in prebuilt non-gc structures
            MarkCompactGC._trace_copy)  # static in prebuilt gc objects
        ptr = self.space
        size_gc_header = self.gcheaderbuilder.size_gc_header
        while ptr < self.spaceptr:
            obj = ptr + size_gc_header
            objsize = self.get_size(obj)
            totalsize = size_gc_header + objsize
            self.trace(obj, self._trace_copy, None)
            ptr += totalsize

    def _trace_copy(self, pointer, ignored=None):
        addr = pointer.address[0]
        size_gc_header = self.gcheaderbuilder.size_gc_header
        if addr != NULL:
            hdr = llmemory.cast_adr_to_ptr(addr - size_gc_header,
                                            lltype.Ptr(self.HDR))
            pointer.address[0] = hdr.forward_ptr

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

    def deal_with_objects_with_finalizers(self, ignored):
        new_with_finalizer = self.AddressDeque()
        while self.objects_with_finalizers.non_empty():
            obj = self.objects_with_finalizers.popleft()
            if self.surviving(obj):
                new_with_finalizer.append(obj)
                break
            finalizers_to_run.append(obj)
            xxxx

    def debug_check_object(self, obj):
        # XXX write it down
        pass

    def surviving(self, obj):
        hdr = self.header(obj)
        return hdr.tid & GCFLAG_MARKBIT

    def _finalization_state(self, obj):
        hdr = self.header(obj)
        if self.surviving(obj):
            if hdr.tid & GCFLAG_FINALIZATION_ORDERING:
                return 2
            else:
                return 3
        else:
            if hdr.tid & GCFLAG_FINALIZATION_ORDERING:
                return 1
            else:
                return 0

    def _recursively_bump_finalization_state_from_1_to_2(self, obj, scan):
        # it's enough to leave mark bit here
        hdr = self.header(obj)
        if hdr.tid & GCFLAG_MARKBIT:
            return # cycle
        self.header(obj).tid |= GCFLAG_MARKBIT
        self.trace(obj, self._mark_object, None)

    def get_forwarding_address(self, obj):
        return obj
