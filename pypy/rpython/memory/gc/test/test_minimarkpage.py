import py
from pypy.rpython.memory.gc import minimark
from pypy.rpython.memory.gc.minimark import PAGE_NULL, PAGE_HEADER, PAGE_PTR
from pypy.rpython.memory.gc.minimark import WORD
from pypy.rpython.lltypesystem import lltype, llmemory, llarena
from pypy.rpython.lltypesystem.llmemory import cast_ptr_to_adr

SHIFT = 4
hdrsize = llmemory.raw_malloc_usage(llmemory.sizeof(PAGE_HEADER))


def test_allocate_arena():
    ac = minimark.ArenaCollection(SHIFT + 8*20, 8, 1)
    ac.allocate_new_arena()
    assert ac.num_uninitialized_pages == 20
    ac.uninitialized_pages + 8*20   # does not raise
    py.test.raises(llarena.ArenaError, "ac.uninitialized_pages + 8*20 + 1")
    #
    ac = minimark.ArenaCollection(SHIFT + 8*20 + 7, 8, 1)
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
    ac = minimark.ArenaCollection(arenasize, pagesize, 99)
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


def arena_collection_for_test(pagesize, *pagelayouts):
    nb_pages = len(pagelayouts[0])
    arenasize = pagesize * (nb_pages + 1) - 1
    ac = minimark.ArenaCollection(arenasize, pagesize, 9*WORD)
    #
    def link(pageaddr, size_class, size_block, nblocks, nusedblocks):
        llarena.arena_reserve(pageaddr, llmemory.sizeof(PAGE_HEADER))
        page = llmemory.cast_adr_to_ptr(pageaddr, PAGE_PTR)
        page.nfree = nblocks - nusedblocks
        page.nuninitialized = page.nfree
        page.freeblock = pageaddr + hdrsize + nusedblocks * size_block
        page.nextpage = ac.page_for_size[size_class]
        ac.page_for_size[size_class] = page
        if page.nextpage:
            page.nextpage.prevpage = page
    #
    alist = []
    for layout in pagelayouts:
        assert len(layout) == nb_pages
        assert " " not in layout.rstrip(" ")
        a = minimark.allocate_arena(arenasize, pagesize)
        alist.append(a)
        assert lltype.typeOf(a.freepage) == llmemory.Address
        startpageaddr = a.freepage
        a.freepage += pagesize * min((layout + " ").index(" "),
                                     (layout + ".").index("."))
        a.nfreepages = layout.count(" ") + layout.count(".")
        a.nuninitializedpages = layout.count(" ")
        #
        pageaddr = startpageaddr
        for i, c in enumerate(layout):
            if '1' <= c <= '9':   # a partially used page (1 block free)
                size_class = int(c)
                size_block = WORD * size_class
                nblocks = (pagesize - hdrsize) // size_block
                link(pageaddr, size_class, size_block, nblocks, nblocks-1)
            elif c == '.':    # a free, but initialized, page
                next_free_num = min((layout + " ").find(" ", i+1),
                                    (layout + ".").find(".", i+1))
                addr = startpageaddr + pagesize * next_free_num
                llarena.arena_reserve(pageaddr,
                                      llmemory.sizeof(llmemory.Address))
                pageaddr.address[0] = addr
            elif c == '#':    # a random full page, not in any linked list
                pass
            elif c == ' ':    # the tail is uninitialized free pages
                break
            pageaddr += pagesize
    #
    assert alist == sorted(alist, key=lambda a: a.nfreepages)
    #
    ac.arenas_start = alist[0]
    ac.arenas_end   = alist[-1]
    for a, b in zip(alist[:-1], alist[1:]):
        a.nextarena = b
        b.prevarena = a
    return ac


def getarena(ac, num, total=None):
    if total is not None:
        a = getarena(ac, total-1)
        assert a == ac.arenas_end
        assert a.nextarena == ARENA_NULL
    prev = ARENA_NULL
    a = ac.arenas_start
    for i in range(num):
        assert a.prevarena == prev
        prev = a
        a = a.nextarena
    return a

def checkpage(ac, page, arena, nb_page):
    pageaddr = llmemory.cast_ptr_to_adr(page)
    assert pageaddr == arena.arena_base + SHIFT + nb_page * ac.page_size


def test_simple_arena_collection():
    pagesize = hdrsize + 16
    ac = arena_collection_for_test(pagesize, "##....#   ")
    #assert ac....
    assert ac.arenas_end.nfreepages == 4
    #
    a0 = getarena(ac, 0, total=2)
    a1 = getarena(ac, 1, total=2)
    page = ac.allocate_new_page(1); checkpage(ac, page, a0, 2)
    page = ac.allocate_new_page(2); checkpage(ac, page, a0, 3)
    assert getarena(ac, 0, total=2) == a0
    page = ac.allocate_new_page(3); checkpage(ac, page, a0, 4)
    assert getarena(ac, 0, total=1) == a1
    page = ac.allocate_new_page(4); checkpage(ac, page, a1, 0)
    page = ac.allocate_new_page(5); checkpage(ac, page, a1, 2)
    page = ac.allocate_new_page(6); checkpage(ac, page, a1, 3)
    page = ac.allocate_new_page(7); checkpage(ac, page, a1, 4)
    assert ac.arenas_start == ac.arenas_end == ARENA_NULL


def ckob(ac, arena, num_page, pos_obj, obj):
    pageaddr = arena.arena_base + SHIFT + num_page * ac.page_size
    assert obj == pageaddr + hdrsize + pos_obj


def test_malloc_common_case():
    pagesize = hdrsize + 7*WORD
    ac = arena_collection_for_test(pagesize, "#23..2 ")
    a0 = getarena(ac, 0, total=1)
    obj = ac.malloc(2*WORD); ckob(ac, a0, 5, 4*WORD, obj)
    obj = ac.malloc(2*WORD); ckob(ac, a0, 1, 4*WORD, obj)
    obj = ac.malloc(2*WORD); ckob(ac, a0, 3, 0*WORD, obj)
    obj = ac.malloc(2*WORD); ckob(ac, a0, 3, 2*WORD, obj)
    obj = ac.malloc(2*WORD); ckob(ac, a0, 3, 4*WORD, obj)
    obj = ac.malloc(2*WORD); ckob(ac, a0, 4, 0*WORD, obj)
    obj = ac.malloc(2*WORD); ckob(ac, a0, 4, 2*WORD, obj)
    obj = ac.malloc(2*WORD); ckob(ac, a0, 4, 4*WORD, obj)
    obj = ac.malloc(2*WORD); ckob(ac, a0, 6, 0*WORD, obj)
    obj = ac.malloc(2*WORD); ckob(ac, a0, 6, 2*WORD, obj)
    obj = ac.malloc(2*WORD); ckob(ac, a0, 6, 4*WORD, obj)

def test_malloc_mixed_sizes():
    pagesize = hdrsize + 7*WORD
    ac = arena_collection_for_test(pagesize, "#23..2 ")
    a0 = getarena(ac, 0, total=1)
    obj = ac.malloc(2*WORD); ckob(ac, a0, 5, 4*WORD, obj)
    obj = ac.malloc(3*WORD); ckob(ac, a0, 2, 3*WORD, obj)
    obj = ac.malloc(2*WORD); ckob(ac, a0, 1, 4*WORD, obj)
    obj = ac.malloc(3*WORD); ckob(ac, a0, 3, 0*WORD, obj)  # 3rd page -> size 3
    obj = ac.malloc(2*WORD); ckob(ac, a0, 4, 0*WORD, obj)  # 4th page -> size 2
    obj = ac.malloc(3*WORD); ckob(ac, a0, 3, 3*WORD, obj)
    obj = ac.malloc(2*WORD); ckob(ac, a0, 4, 2*WORD, obj)
    obj = ac.malloc(3*WORD); ckob(ac, a0, 6, 0*WORD, obj)  # 6th page -> size 3
    obj = ac.malloc(2*WORD); ckob(ac, a0, 4, 4*WORD, obj)
    obj = ac.malloc(3*WORD); ckob(ac, a0, 6, 3*WORD, obj)

def test_malloc_new_arena():
    pagesize = hdrsize + 7*WORD
    ac = arena_collection_for_test(pagesize, "#23..2 ")
    a0 = getarena(ac, 0, total=1)
    obj = ac.malloc(5*WORD); ckob(ac, a0, 3, 0*WORD, obj)  # 3rd page -> size 5
    obj = ac.malloc(4*WORD); ckob(ac, a0, 4, 0*WORD, obj)  # 4th page -> size 4
    obj = ac.malloc(1*WORD); ckob(ac, a0, 6, 0*WORD, obj)  # 6th page -> size 1
    assert ac.arenas_start == ac.arenas_end == ARENA_NULL  # no more free page
    obj = ac.malloc(1*WORD); ckob(ac, a0, 6, 1*WORD, obj)
    obj = ac.malloc(5*WORD)
    a1 = getarena(ac, 0, total=1)
    pass;                    ckob(ac, a1, 0, 0*WORD, obj)  # a1/0 -> size 5
    obj = ac.malloc(1*WORD); ckob(ac, a0, 6, 2*WORD, obj)
    obj = ac.malloc(5*WORD); ckob(ac, a1, 1, 0*WORD, obj)  # a1/1 -> size 5
    obj = ac.malloc(1*WORD); ckob(ac, a0, 6, 3*WORD, obj)
    obj = ac.malloc(2*WORD); ckob(ac, a0, 5, 4*WORD, obj)
    obj = ac.malloc(2*WORD); ckob(ac, a0, 1, 4*WORD, obj)
    obj = ac.malloc(2*WORD); ckob(ac, a1, 2, 0*WORD, obj)  # a1/2 -> size 2
