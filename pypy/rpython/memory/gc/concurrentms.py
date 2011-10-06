from pypy.rpython.lltypesystem import lltype, llmemory, llarena, rffi
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.lltypesystem.llmemory import raw_malloc_usage
from pypy.rlib.debug import ll_assert
from pypy.rlib.rarithmetic import LONG_BIT
from pypy.rpython.memory.gc.base import GCBase

#
# A "mostly concurrent" mark&sweep GC.  It can delegate most of the GC
# operations to a separate thread, which runs concurrently with the
# mutator (i.e. the rest of the program).  Based on the idea that the
# concurrent collection should be relatively fast --- 20-25% of the
# time? after which the collector thread just sleeps --- it uses a
# snapshot-at-the-beginning technique with a "deletion barrier", i.e. a
# write barrier that prevents changes to objects that have not been
# scanned yet (Abraham and Patel, Yuasa).
#
# Reference: The Garbage Collection Handbook, Richard Jones and Antony
# Hosking and Eliot Moss.
#

WORD = LONG_BIT // 8
NULL = llmemory.NULL
WORD_POWER_2 = {32: 2, 64: 3}[LONG_BIT]
assert 1 << WORD_POWER_2 == WORD
size_of_addr = llmemory.sizeof(llmemory.Address)


class MostlyConcurrentMarkSweepGC(GCBase):
    _alloc_flavor_ = "raw"
    inline_simple_malloc = True
    inline_simple_malloc_varsize = True
    needs_write_barrier = True
    prebuilt_gc_objects_are_static_roots = False
    malloc_zero_filled = True
    #gcflag_extra = GCFLAG_FINALIZATION_ORDERING

    HDR = lltype.Struct('header', ('tid', lltype.Signed))
    typeid_is_in_field = 'tid'

    TRANSLATION_PARAMS = {'page_size': 4096,
                          'small_request_threshold': 35*WORD,
                          }

    def __init__(self, config, page_size=64, small_request_threshold=24,
                 **kwds):
        # 'small_request_threshold' is the largest size that we will
        # satisfy using our own pages mecanism.  Larger requests just
        # go to the system malloc().
        GCBase.__init__(self, config, **kwds)
        assert small_request_threshold % WORD == 0
        self.small_request_threshold = small_request_threshold
        self.page_size = page_size
        self.free_pages = NULL
        length = small_request_threshold // WORD + 1
        self.free_lists = lltype.malloc(rffi.CArray(llmemory.Address),
                                        length, flavor='raw', zero=True,
                                        immortal=True)

    def combine(self, typeid16, flags):
        return llop.combine_ushort(lltype.Signed, typeid16, flags)

    def malloc_fixedsize_clear(self, typeid, size,
                               needs_finalizer=False, contains_weakptr=False):
        assert not needs_finalizer  # XXX
        assert not contains_weakptr # XXX
        size_gc_header = self.gcheaderbuilder.size_gc_header
        totalsize = size_gc_header + size
        rawtotalsize = raw_malloc_usage(totalsize)
        if rawtotalsize <= self.small_request_threshold:
            n = (rawtotalsize + WORD - 1) >> WORD_POWER_2
            result = self.free_lists[n]
            if result != llmemory.NULL:
                self.free_lists[n] = result.address[0]
                #
                llarena.arena_reset(result, size_of_addr, 0)
                llarena.arena_reserve(result, totalsize)
                hdr = llmemory.cast_adr_to_ptr(result, lltype.Ptr(self.HDR))
                hdr.tid = self.combine(typeid, flags=0)
                #
                obj = result + size_gc_header
                return llmemory.cast_adr_to_ptr(obj, llmemory.GCREF)
                #
        return self._malloc_slowpath(typeid, size)

    def _malloc_slowpath(self, typeid, size):
        size_gc_header = self.gcheaderbuilder.size_gc_header
        totalsize = size_gc_header + size
        rawtotalsize = raw_malloc_usage(totalsize)
        if rawtotalsize <= self.small_request_threshold:
            #
            # Case 1: we have run out of the free list corresponding to
            # the size.  Grab the next free page.
            newpage = self.free_pages
            if newpage == llmemory.NULL:
                self.allocate_next_arena()
                newpage = self.free_pages
            self.free_pages = newpage.address[0]
            llarena.arena_reset(newpage, size_of_addr, 0)
            #
            # Initialize the free page to contain objects of the given
            # size.  This requires setting up all object locations in the
            # page, linking them in the free list.
            n = (rawtotalsize + WORD - 1) >> WORD_POWER_2
            head = self.free_lists[n]
            ll_assert(not head, "_malloc_slowpath: unexpected free_lists[n]")
            i = self.page_size - rawtotalsize
            while i >= rawtotalsize:
                llarena.arena_reserve(newpage + i, size_of_addr)
                (newpage + i).address[0] = head
                head = newpage + i
                i -= rawtotalsize
            self.free_lists[n] = head
            result = head - rawtotalsize
            #
            # Done: all object locations are linked, apart from 'result',
            # which is the first object location in the page.  Note that
            # if the size is not a multiple of 2, there are a few wasted
            # WORDs, which we place at the start of the page rather than
            # at the end (Hans Boehm, xxx ref).
            llarena.arena_reserve(result, totalsize)
            hdr = llmemory.cast_adr_to_ptr(result, lltype.Ptr(self.HDR))
            hdr.tid = self.combine(typeid, flags=0)
            #
            obj = result + size_gc_header
            return llmemory.cast_adr_to_ptr(obj, llmemory.GCREF)
            #
        else:
            # Case 2: the object is too big, so allocate it directly
            # with the system malloc().
            xxxxx
    _malloc_slowpath._dont_inline_ = True

    def allocate_next_arena(self):
        # xxx for now, allocate one page at a time with the system malloc()
        page = llarena.arena_malloc(self.page_size, 2)     # zero-filled
        ll_assert(bool(page), "out of memory!")
        llarena.arena_reserve(page, size_of_addr)
        page.address[0] = NULL
        self.free_pages = page
    allocate_next_arena._dont_inline_ = True
