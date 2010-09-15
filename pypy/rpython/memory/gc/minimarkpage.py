
# Terminology: the memory is subdivided into "pages".
# A page contains a number of allocated objects, called "blocks".

# The actual allocation occurs in whole arenas, which are subdivided
# into pages.  We don't keep track of the arenas.  A page can be:
#
# - uninitialized: never touched so far.
#
# - allocated: contains some objects (all of the same size).  Starts with a
#   PAGE_HEADER.  The page is on the chained list of pages that still have
#   room for objects of that size, unless it is completely full.
#
# - free: used to be partially full, and is now free again.  The page is
#   on the chained list of free pages.

# Similarily, each allocated page contains blocks of a given size, which can
# be either uninitialized, allocated or free.

PAGE_PTR = lltype.Ptr(lltype.ForwardReference())
PAGE_HEADER = lltype.Struct('PageHeader',
    # -- The following two pointers make a chained list of pages with the same
    #    size class.  Warning, 'prevpage' contains random garbage for the first
    #    entry in the list.
    ('nextpage', PAGE_PTR),
    ('prevpage', PAGE_PTR),
    # -- The number of free blocks, and the number of uninitialized blocks.
    #    The number of allocated blocks is the rest.
    ('nuninitialized', lltype.Signed),
    ('nfree', lltype.Signed),
    # -- The chained list of free blocks.  If there are none, points to the
    #    first uninitialized block.
    ('freeblock', llmemory.Address),
    )
PAGE_PTR.TO.become(PAGE_HEADER)
PAGE_NULL = lltype.nullptr(PAGE_HEADER)

# ----------


class ArenaCollection(object):
    _alloc_flavor_ = "raw"

    def __init__(self, arena_size, page_size, small_request_threshold):
        self.arena_size = arena_size
        self.page_size = page_size
        self.small_request_threshold = small_request_threshold
        #
        # 'pageaddr_for_size': for each size N between WORD and
        # small_request_threshold (included), contains either NULL or
        # a pointer to a page that has room for at least one more
        # allocation of the given size.
        length = small_request_threshold / WORD + 1
        self.page_for_size = lltype.malloc(rffi.CArray(PAGE_PTR), length,
                                           flavor='raw', zero=True)
        self.nblocks_for_size = lltype.malloc(rffi.CArray(lltype.Signed),
                                              length, flavor='raw')
        hdrsize = llmemory.raw_malloc_usage(llmemory.sizeof(PAGE_HEADER))
        for i in range(1, length):
            self.nblocks_for_size[i] = (page_size - hdrsize) // (WORD * i)
        #
        self.uninitialized_pages = PAGE_NULL
        self.num_uninitialized_pages = 0
        self.free_pages = PAGE_NULL


    def malloc(self, size):
        """Allocate a block from a page in an arena."""
        nsize = llmemory.raw_malloc_usage(size)
        ll_assert(nsize > 0, "malloc: size is null or negative")
        ll_assert(nsize <= self.small_request_threshold,"malloc: size too big")
        ll_assert((nsize & (WORD-1)) == 0, "malloc: size is not aligned")
        #
        # Get the page to use from the size
        size_class = nsize / WORD
        page = self.page_for_size[size_class]
        if page == PAGE_NULL:
            page = self.allocate_new_page(size_class)
        #
        # The result is simply 'page.freeblock'
        result = page.freeblock
        if page.nfree > 0:
            #
            # The 'result' was part of the chained list; read the next.
            page.nfree -= 1
            page.freeblock = result.address[0]
            llarena.arena_reset(result,
                                llmemory.sizeof(llmemory.Address),
                                False)
            #
        else:
            # The 'result' is part of the uninitialized blocks.
            ll_assert(page.nuninitialized > 0,
                      "fully allocated page found in the page_for_size list")
            page.freeblock = result + nsize
            page.nuninitialized -= 1
            if page.nuninitialized == 0:
                #
                # This was the last free block, so unlink the page from the
                # chained list.
                self.page_for_size[size_class] = page.nextpage
        #
        llarena.arena_reserve(result, _dummy_size(size), False)
        return result


    def allocate_new_page(self, size_class):
        """Allocate and return a new page for the given size_class."""
        #
        if self.free_pages != PAGE_NULL:
            #
            # Get the page from the chained list 'free_pages'.
            page = self.free_pages
            self.free_pages = page.address[0]
            llarena.arena_reset(self.free_pages,
                                llmemory.sizeof(llmemory.Address),
                                False)
        else:
            # Get the next free page from the uninitialized pages.
            if self.num_uninitialized_pages == 0:
                self.allocate_new_arena()   # Out of memory.  Get a new arena.
            page = self.uninitialized_pages
            self.uninitialized_pages += self.page_size
            self.num_uninitialized_pages -= 1
        #
        # Initialize the fields of the resulting page
        llarena.arena_reserve(page, llmemory.sizeof(PAGE_HEADER))
        result = llmemory.cast_adr_to_ptr(page, PAGE_PTR)
        #
        hdrsize = llmemory.raw_malloc_usage(llmemory.sizeof(PAGE_HEADER))
        result.nuninitialized = self.nblocks_for_size[size_class]
        result.nfree = 0
        result.freeblock = page + hdrsize
        result.nextpage = PAGE_NULL
        ll_assert(self.page_for_size[size_class] == PAGE_NULL,
                  "allocate_new_page() called but a page is already waiting")
        self.page_for_size[size_class] = result
        return result


    def allocate_new_arena(self):
        ll_assert(self.num_uninitialized_pages == 0,
                  "some uninitialized pages are already waiting")
        #
        # 'arena_base' points to the start of malloced memory; it might not
        # be a page-aligned address
        arena_base = llarena.arena_malloc(self.arena_size, False)
        if not arena_base:
            raise MemoryError("couldn't allocate the next arena")
        arena_end = arena_base + self.arena_size
        #
        # 'firstpage' points to the first unused page
        firstpage = start_of_page(arena_base + self.page_size - 1,
                                  self.page_size)
        # 'npages' is the number of full pages just allocated
        npages = (arena_end - firstpage) // self.page_size
        #
        # add these pages to the list
        self.uninitialized_pages = firstpage
        self.num_uninitialized_pages = npages
        #
        # increase a bit arena_size for the next time
        self.arena_size = (self.arena_size // 4 * 5) + (self.page_size - 1)
        self.arena_size = (self.arena_size // self.page_size) * self.page_size
    allocate_new_arena._dont_inline_ = True


    def free(self, obj, size):
        """Free a previously malloc'ed block."""
        ll_assert(size > 0, "free: size is null or negative")
        ll_assert(size <= self.small_request_threshold, "free: size too big")
        ll_assert((size & (WORD-1)) == 0, "free: size is not aligned")
        #
        llarena.arena_reset(obj, _dummy_size(size), False)
        pageaddr = start_of_page(obj, self.page_size)
        if not we_are_translated():
            hdrsize = llmemory.raw_malloc_usage(llmemory.sizeof(PAGE_HEADER))
            assert obj - pageaddr >= hdrsize
            assert (obj - pageaddr - hdrsize) % size == 0
        page = llmemory.cast_adr_to_ptr(pageaddr, PAGE_PTR)
        size_class = size / WORD
        #
        # Increment the number of known free objects
        nfree = page.nfree + 1
        if nfree < self.nblocks_for_size[size_class]:
            #
            # Not all objects in this page are freed yet.
            # Add the free block to the chained list.
            page.nfree = nfree
            llarena.arena_reserve(obj, llmemory.sizeof(llmemory.Address),
                                  False)
            obj.address[0] = page.freeblock
            page.freeblock = obj
            #
            # If the page was full, then it now has space and should be
            # linked back in the page_for_size[] linked list.
            if nfree == 1:
                page.nextpage = self.page_for_size[size_class]
                if page.nextpage != PAGE_NULL:
                    page.nextpage.prevpage = page
                self.page_for_size[size_class] = page
            #
        else:
            # The page becomes completely free.  Remove it from
            # the page_for_size[] linked list.
            if page == self.page_for_size[size_class]:
                self.page_for_size[size_class] = page.nextpage
            else:
                prev = page.prevpage
                next = page.nextpage
                prev.nextpage = next
                next.prevpage = prev
            #
            # Free the page, putting it back in the chained list of the arena
            # where it belongs
            xxx#...


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
    ofs = ((addr.offset - shift) // page_size) * page_size + shift
    return llarena.fakearenaaddress(addr.arena, ofs)

def _dummy_size(size):
    if we_are_translated():
        return size
    if isinstance(size, int):
        size = llmemory.sizeof(lltype.Char) * size
    return size
