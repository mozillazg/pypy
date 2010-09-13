from pypy.rpython.lltypesystem import lltype, llmemory, llarena, rffi
from pypy.rpython.memory.gc.base import MovingGCBase
from pypy.rpython.memory.support import DEFAULT_CHUNK_SIZE
from pypy.rlib.rarithmetic import LONG_BIT
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.debug import ll_assert

WORD = LONG_BIT // 8
NULL = llmemory.NULL

first_gcflag = 1 << (LONG_BIT//2)
GCFLAG_BIG   = first_gcflag

# ____________________________________________________________

class Gen2GC(MovingGCBase):
    _alloc_flavor_ = "raw"
    inline_simple_malloc = True
    inline_simple_malloc_varsize = True
    malloc_zero_filled = True

    HDR = lltype.Struct('header', ('tid', lltype.Signed))
    typeid_is_in_field = 'tid'
    #withhash_flag_is_in_field = 'tid', _GCFLAG_HASH_BASE * 0x2

    TRANSLATION_PARAMS = {
        # The size of the nursery.  -1 means "auto", which means that it
        # will look it up in the env var PYPY_GENERATIONGC_NURSERY and
        # fall back to half the size of the L2 cache.
        "nursery_size": -1,

        # The system page size.  Like obmalloc.c, we assume that it is 4K,
        # which is OK for most systems.
        "page_size": 4096,

        # The size of an arena.  Arenas are groups of pages allocated
        # together.
        "arena_size": 65536*WORD,

        # The maximum size of an object allocated compactly.  All objects
        # that are larger are just allocated with raw_malloc().
        "small_request_threshold": 32*WORD,
        }

    def __init__(self, config, chunk_size=DEFAULT_CHUNK_SIZE,
                 nursery_size=32*WORD,
                 page_size=16*WORD,
                 arena_size=48*WORD,
                 small_request_threshold=5*WORD):
        MovingGCBase.__init__(self, config, chunk_size)
        self.nursery_size = nursery_size
        self.page_size = page_size
        self.arena_size = arena_size
        self.small_request_threshold = small_request_threshold

    def setup(self):
        pass

# ____________________________________________________________

# Terminology: Arenas are collection of pages; both are fixed-size.
# A page contains a number of allocated objects, called "blocks".


class Arena(object):
    _alloc_flavor_ = "raw"

    def __init__(self, arena_size, page_size):
        self.page_size = page_size
        self.arena_size = arena_size
        # 'arena_base' points to the start of malloced memory; it might not
        # be a page-aligned address
        self.arena_base = llarena.arena_malloc(self.arena_size, False)
        if not self.arena_base:
            raise MemoryError("couldn't allocate the next arena")
        # 'freepage' points to the first unused page
        # 'nfreepages' is the number of unused pages
        self.freepage = start_of_page(self.arena_base + page_size - 1,
                                      page_size)
        arena_end = self.arena_base + self.arena_size
        self.nfreepages = (arena_end - self.freepage) // page_size
        self.nuninitializedpages = self.nfreepages
        #
        # The arenas containing at least one free page are linked in a
        # doubly-linked list.  We keep this chained list in order: it
        # starts with the arenas with the most number of allocated
        # pages, so that the least allocated arenas near the end of the
        # list have a chance to become completely empty and be freed.
        self.nextarena = None
        self.prevarena = None


# Each initialized page in the arena starts with a PAGE_HEADER.  The
# arena typically also contains uninitialized pages at the end.
# Similarily, each page contains blocks of a given size, which can be
# either allocated or freed, and a number of free blocks at the end of
# the page are uninitialized.  The free but initialized blocks contain a
# pointer to the next free block, forming a chained list.

PAGE_PTR = lltype.Ptr(lltype.ForwardReference())
PAGE_HEADER = lltype.Struct('page_header',
    ('nfree', lltype.Signed),   # number of free blocks in this page
    ('nuninitialized', lltype.Signed),   # num. uninitialized blocks (<= nfree)
    ('freeblock', llmemory.Address),  # first free block, chained list
    ('prevpage', PAGE_PTR),  # chained list of pages with the same size class
    )
PAGE_PTR.TO.become(PAGE_HEADER)
PAGE_NULL = lltype.nullptr(PAGE_HEADER)


class ArenaCollection(object):
    _alloc_flavor_ = "raw"

    def __init__(self, arena_size, page_size, small_request_threshold):
        self.arena_size = arena_size
        self.page_size = page_size
        #
        # 'pageaddr_for_size': for each size N between WORD and
        # small_request_threshold (included), contains either NULL or
        # a pointer to a page that has room for at least one more
        # allocation of the given size.
        length = small_request_threshold / WORD + 1
        self.page_for_size = lltype.malloc(rffi.CArray(PAGE_PTR), length,
                                           flavor='raw', zero=True)
        self.arenas_start = None   # the most allocated (but not full) arena
        self.arenas_end   = None   # the least allocated (but not empty) arena


    def malloc(self, size):
        """Allocate a block from a page in an arena."""
        ll_assert(size > 0, "malloc: size is null or negative")
        ll_assert(size <= self.small_request_threshold, "malloc: size too big")
        ll_assert((size & (WORD-1)) == 0, "malloc: size is not aligned")
        #
        # Get the page to use from the size
        size_class = size / WORD
        page = self.page_for_size[size_class]
        if page == PAGE_NULL:
            page = self.allocate_new_page(size_class)
        #
        # The result is simply 'page.freeblock'
        ll_assert(page.nfree > 0, "page_for_size lists a page with nfree <= 0")
        result = page.freeblock
        page.nfree -= 1
        if page.nfree == 0:
            #
            # This was the last free block, so unlink the page from the
            # chained list.
            self.page_for_size[size_class] = page.prevpage
            #
        else:
            # This was not the last free block, so update 'page.freeblock'
            # to point to the next free block.  Two cases here...
            if page.nfree < page.nuninitialized:
                # The 'result' was not initialized at all.  We must compute
                # the next free block by adding 'size' to 'page.freeblock'.
                page.freeblock = result + size
                page.nuninitialized -= 1
                ll_assert(page.nfree == page.nuninitialized,
                          "bad value of page.nuninitialized")
            else:
                # The 'result' was part of the chained list; read the next.
                page.freeblock = result.address[0]
        #
        return result


    def allocate_new_page(self, size_class):
        """Allocate a new page for the given size_class."""
        #
        # Get the arena with the highest number of pages already allocated
        arena = self.arenas_start
        if arena is None:
            # No arenas.  Get a fresh new arena.
            ll_assert(self.arenas_end is None, "!arenas_start && arenas_end")
            arena = Arena(self.arena_size, self.page_size)
            self.arenas_start = arena
            self.arenas_end = arena
        #
        # Get the page from there (same logic as in malloc() except on
        # pages instead of on blocks)
        result = arena.freepage
        arena.nfreepages -= 1
        if arena.nfreepages == 0:
            #
            # This was the last free page, so unlink the arena from the
            # chained list.
            self.arenas_start = arena.nextarena
            if self.arenas_start is None:
                self.arenas_end = None
            else:
                self.arenas_start.prevarena = None
            #
        else:
            # This was not the last free page, so update 'arena.freepage'
            # to point to the next free page.  Two cases here...
            if arena.nfreepages < arena.nuninitializedpages:
                # The 'result' was not initialized at all.  We must compute
                # the next free page by adding 'page_size' to 'arena.freepage'.
                arena.freepage = result + self.page_size
                arena.nuninitializedpages -= 1
                ll_assert(arena.nfreepages == arena.nuninitializedpages,
                          "bad value of page.nuninitialized")
            else:
                # The 'result' was part of the chained list; read the next.
                arena.freepage = result.address[0]
                llarena.arena_reset(result,
                                    llmemory.sizeof(llmemory.Address),
                                    False)
        #
        # Initialize the fields of the resulting page
        llarena.arena_reserve(result, llmemory.sizeof(PAGE_HEADER))
        page = llmemory.cast_adr_to_ptr(result, PAGE_PTR)
        #
        hdrsize = llmemory.raw_malloc_usage(llmemory.sizeof(PAGE_HEADER))
        page.nfree = ((self.page_size - hdrsize) / WORD) // size_class
        #
        page.nuninitialized = page.nfree
        page.freeblock = result + hdrsize
        page.prevpage = PAGE_NULL
        ll_assert(self.page_for_size[size_class] == PAGE_NULL,
                  "allocate_new_page() called but a page is already waiting")
        self.page_for_size[size_class] = page
        return page

# ____________________________________________________________
# Helpers to go from a pointer to the start of its page

def start_of_page(addr, page_size):
    """Return the address of the start of the page that contains 'addr'."""
    if we_are_translated():
        xxx
    else:
        return _start_of_page_untranslated(addr, page_size)

def _start_of_page_untranslated(addr, page_size):
    assert isinstance(addr, llarena.fakearenaaddress)
    shift = 4     # for testing, we assume that the whole arena is not
                  # on a page boundary
    ofs = ((addr.offset - shift) & ~(page_size-1)) + shift
    return llarena.fakearenaaddress(addr.arena, ofs)

# ____________________________________________________________

def nursery_size_from_env():
    return read_from_env('PYPY_GENERATIONGC_NURSERY')
