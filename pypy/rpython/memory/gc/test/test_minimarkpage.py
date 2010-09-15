import py
from pypy.rpython.memory.gc.minimarkpage import ArenaCollection
from pypy.rpython.memory.gc.minimarkpage import PAGE_HEADER, PAGE_PTR
from pypy.rpython.memory.gc.minimarkpage import PAGE_NULL, WORD
from pypy.rpython.memory.gc.minimarkpage import _dummy_size
from pypy.rpython.lltypesystem import lltype, llmemory, llarena
from pypy.rpython.lltypesystem.llmemory import cast_ptr_to_adr

NULL = llmemory.NULL
SHIFT = 4
hdrsize = llmemory.raw_malloc_usage(llmemory.sizeof(PAGE_HEADER))


def test_allocate_arena():
    ac = ArenaCollection(SHIFT + 8*20, 8, 1)
    ac.allocate_new_arena()
    assert ac.num_uninitialized_pages == 20
    ac.uninitialized_pages + 8*20   # does not raise
    py.test.raises(llarena.ArenaError, "ac.uninitialized_pages + 8*20 + 1")
    #
    ac = ArenaCollection(SHIFT + 8*20 + 7, 8, 1)
    ac.allocate_new_arena()
    assert ac.num_uninitialized_pages == 20
    ac.uninitialized_pages + 8*20 + 7   # does not raise
    py.test.raises(llarena.ArenaError, "ac.uninitialized_pages + 8*20 + 8")


def test_allocate_new_page():
    pagesize = hdrsize + 16
    arenasize = pagesize * 4 - 1
    #
    def checknewpage(page, size_class):
        size = WORD * size_class
        assert page.nuninitialized == (pagesize - hdrsize) // size
        assert page.nfree == 0
        page1 = page.freeblock - hdrsize
        assert llmemory.cast_ptr_to_adr(page) == page1
        assert page.nextpage == PAGE_NULL
    #
    ac = ArenaCollection(arenasize, pagesize, 99)
    assert ac.num_uninitialized_pages == 0
    #
    page = ac.allocate_new_page(5)
    checknewpage(page, 5)
    assert ac.num_uninitialized_pages == 2
    assert ac.uninitialized_pages - pagesize == cast_ptr_to_adr(page)
    assert ac.page_for_size[5] == page
    #
    page = ac.allocate_new_page(3)
    checknewpage(page, 3)
    assert ac.num_uninitialized_pages == 1
    assert ac.uninitialized_pages - pagesize == cast_ptr_to_adr(page)
    assert ac.page_for_size[3] == page
    #
    page = ac.allocate_new_page(4)
    checknewpage(page, 4)
    assert ac.num_uninitialized_pages == 0
    assert ac.page_for_size[4] == page


def arena_collection_for_test(pagesize, pagelayout, fill_with_objects=False):
    assert " " not in pagelayout.rstrip(" ")
    nb_pages = len(pagelayout)
    arenasize = pagesize * (nb_pages + 1) - 1
    ac = ArenaCollection(arenasize, pagesize, 9*WORD)
    #
    def link(pageaddr, size_class, size_block, nblocks, nusedblocks):
        llarena.arena_reserve(pageaddr, llmemory.sizeof(PAGE_HEADER))
        page = llmemory.cast_adr_to_ptr(pageaddr, PAGE_PTR)
        page.nfree = 0
        page.nuninitialized = nblocks - nusedblocks
        page.freeblock = pageaddr + hdrsize + nusedblocks * size_block
        if nusedblocks < nblocks:
            chainedlists = ac.page_for_size
        else:
            chainedlists = ac.full_page_for_size
        page.nextpage = chainedlists[size_class]
        chainedlists[size_class] = page
        if fill_with_objects:
            for i in range(nusedblocks):
                objaddr = pageaddr + hdrsize + i * size_block
                llarena.arena_reserve(objaddr, _dummy_size(size_block))
    #
    ac.allocate_new_arena()
    num_initialized_pages = len(pagelayout.rstrip(" "))
    ac._startpageaddr = ac.uninitialized_pages
    ac.uninitialized_pages += pagesize * num_initialized_pages
    ac.num_uninitialized_pages -= num_initialized_pages
    #
    for i in reversed(range(num_initialized_pages)):
        pageaddr = pagenum(ac, i)
        c = pagelayout[i]
        if '1' <= c <= '9':   # a partially used page (1 block free)
            size_class = int(c)
            size_block = WORD * size_class
            nblocks = (pagesize - hdrsize) // size_block
            link(pageaddr, size_class, size_block, nblocks, nblocks-1)
        elif c == '.':    # a free, but initialized, page
            llarena.arena_reserve(pageaddr, llmemory.sizeof(llmemory.Address))
            pageaddr.address[0] = ac.free_pages
            ac.free_pages = pageaddr
        elif c == '#':    # a random full page, in the list 'full_pages'
            size_class = fill_with_objects or 1
            size_block = WORD * size_class
            nblocks = (pagesize - hdrsize) // size_block
            link(pageaddr, size_class, size_block, nblocks, nblocks)
    #
    ac.allocate_new_arena = lambda: should_not_allocate_new_arenas
    return ac


def pagenum(ac, i):
    return ac._startpageaddr + ac.page_size * i

def getpage(ac, i):
    return llmemory.cast_adr_to_ptr(pagenum(ac, i), PAGE_PTR)

def checkpage(ac, page, expected_position):
    assert llmemory.cast_ptr_to_adr(page) == pagenum(ac, expected_position)


def test_simple_arena_collection():
    pagesize = hdrsize + 16
    ac = arena_collection_for_test(pagesize, "##....#   ")
    #
    assert ac.free_pages == pagenum(ac, 2)
    page = ac.allocate_new_page(1); checkpage(ac, page, 2)
    assert ac.free_pages == pagenum(ac, 3)
    page = ac.allocate_new_page(2); checkpage(ac, page, 3)
    assert ac.free_pages == pagenum(ac, 4)
    page = ac.allocate_new_page(3); checkpage(ac, page, 4)
    assert ac.free_pages == pagenum(ac, 5)
    page = ac.allocate_new_page(4); checkpage(ac, page, 5)
    assert ac.free_pages == NULL and ac.num_uninitialized_pages == 3
    page = ac.allocate_new_page(5); checkpage(ac, page, 7)
    assert ac.free_pages == NULL and ac.num_uninitialized_pages == 2
    page = ac.allocate_new_page(6); checkpage(ac, page, 8)
    assert ac.free_pages == NULL and ac.num_uninitialized_pages == 1
    page = ac.allocate_new_page(7); checkpage(ac, page, 9)
    assert ac.free_pages == NULL and ac.num_uninitialized_pages == 0


def chkob(ac, num_page, pos_obj, obj):
    pageaddr = pagenum(ac, num_page)
    assert obj == pageaddr + hdrsize + pos_obj


def test_malloc_common_case():
    pagesize = hdrsize + 7*WORD
    ac = arena_collection_for_test(pagesize, "#23..2 ")
    obj = ac.malloc(2*WORD); chkob(ac, 1, 4*WORD, obj)
    obj = ac.malloc(2*WORD); chkob(ac, 5, 4*WORD, obj)
    obj = ac.malloc(2*WORD); chkob(ac, 3, 0*WORD, obj)
    obj = ac.malloc(2*WORD); chkob(ac, 3, 2*WORD, obj)
    obj = ac.malloc(2*WORD); chkob(ac, 3, 4*WORD, obj)
    obj = ac.malloc(2*WORD); chkob(ac, 4, 0*WORD, obj)
    obj = ac.malloc(2*WORD); chkob(ac, 4, 2*WORD, obj)
    obj = ac.malloc(2*WORD); chkob(ac, 4, 4*WORD, obj)
    obj = ac.malloc(2*WORD); chkob(ac, 6, 0*WORD, obj)
    obj = ac.malloc(2*WORD); chkob(ac, 6, 2*WORD, obj)
    obj = ac.malloc(2*WORD); chkob(ac, 6, 4*WORD, obj)

def test_malloc_mixed_sizes():
    pagesize = hdrsize + 7*WORD
    ac = arena_collection_for_test(pagesize, "#23..2 ")
    obj = ac.malloc(2*WORD); chkob(ac, 1, 4*WORD, obj)
    obj = ac.malloc(3*WORD); chkob(ac, 2, 3*WORD, obj)
    obj = ac.malloc(2*WORD); chkob(ac, 5, 4*WORD, obj)
    obj = ac.malloc(3*WORD); chkob(ac, 3, 0*WORD, obj)  # 3rd page -> size 3
    obj = ac.malloc(2*WORD); chkob(ac, 4, 0*WORD, obj)  # 4th page -> size 2
    obj = ac.malloc(3*WORD); chkob(ac, 3, 3*WORD, obj)
    obj = ac.malloc(2*WORD); chkob(ac, 4, 2*WORD, obj)
    obj = ac.malloc(3*WORD); chkob(ac, 6, 0*WORD, obj)  # 6th page -> size 3
    obj = ac.malloc(2*WORD); chkob(ac, 4, 4*WORD, obj)
    obj = ac.malloc(3*WORD); chkob(ac, 6, 3*WORD, obj)

def test_malloc_new_arena():
    pagesize = hdrsize + 7*WORD
    ac = arena_collection_for_test(pagesize, "### ")
    obj = ac.malloc(2*WORD); chkob(ac, 3, 0*WORD, obj)  # 3rd page -> size 2
    #
    del ac.allocate_new_arena    # restore the one from the class
    arena_size = ac.arena_size
    obj = ac.malloc(3*WORD)                             # need a new arena
    assert ac.num_uninitialized_pages == (arena_size // ac.page_size
                                          - 1    # for start_of_page()
                                          - 1    # the just-allocated page
                                          )

class OkToFree(object):
    def __init__(self, ac, answer):
        self.ac = ac
        self.answer = answer
        self.seen = []

    def __call__(self, addr):
        self.seen.append(addr - self.ac._startpageaddr)
        if isinstance(self.answer, bool):
            return self.answer
        else:
            return self.answer(addr)

def test_mass_free_partial_remains():
    pagesize = hdrsize + 7*WORD
    ac = arena_collection_for_test(pagesize, "2", fill_with_objects=2)
    ok_to_free = OkToFree(ac, False)
    ac.mass_free(ok_to_free)
    assert ok_to_free.seen == [hdrsize + 0*WORD,
                               hdrsize + 2*WORD]
    page = getpage(ac, 0)
    assert page == ac.page_for_size[2]
    assert page.nextpage == PAGE_NULL
    assert page.nuninitialized == 1
    assert page.nfree == 0
    chkob(ac, 0, 4*WORD, page.freeblock)
    assert ac.free_pages == NULL

def test_mass_free_emptied_page():
    pagesize = hdrsize + 7*WORD
    ac = arena_collection_for_test(pagesize, "2", fill_with_objects=2)
    ok_to_free = OkToFree(ac, True)
    ac.mass_free(ok_to_free)
    assert ok_to_free.seen == [hdrsize + 0*WORD,
                               hdrsize + 2*WORD]
    pageaddr = pagenum(ac, 0)
    assert pageaddr == ac.free_pages
    assert pageaddr.address[0] == NULL
    assert ac.page_for_size[2] == PAGE_NULL
