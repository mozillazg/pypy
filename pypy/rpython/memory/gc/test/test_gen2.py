from pypy.rpython.memory.gc import gen2
from pypy.rpython.memory.gc.gen2 import WORD, PAGE_NULL, PAGE_HEADER, PAGE_PTR
from pypy.rpython.memory.gc.gen2 import ARENA, ARENA_NULL
from pypy.rpython.lltypesystem import lltype, llmemory, llarena

SHIFT = 4
hdrsize = llmemory.raw_malloc_usage(llmemory.sizeof(PAGE_HEADER))
arenasize = llmemory.raw_malloc_usage(llmemory.sizeof(ARENA))


def test_allocate_arena():
    a = gen2.allocate_arena(SHIFT + 8*20 + arenasize, 8)
    assert a.freepage == a.arena_base + SHIFT
    assert a.nfreepages == 20
    assert a.nuninitializedpages == 20
    assert a.prevarena == ARENA_NULL
    assert a.nextarena == ARENA_NULL
    #
    a = gen2.allocate_arena(SHIFT + 8*20 + 7 + arenasize, 8)
    assert a.freepage == a.arena_base + SHIFT
    assert a.nfreepages == 20
    assert a.nuninitializedpages == 20
    assert a.prevarena == ARENA_NULL
    assert a.nextarena == ARENA_NULL


def test_allocate_new_page():
    pagesize = hdrsize + 16
    arenasize = pagesize * 4 - 1
    #
    def checknewpage(page, size_class):
        size = WORD * size_class
        assert page.nfree == (pagesize - hdrsize) // size
        assert page.nuninitialized == page.nfree
        page2 = page.freeblock - hdrsize
        assert llmemory.cast_ptr_to_adr(page) == page2
        assert page.nextpage == PAGE_NULL
    #
    ac = gen2.ArenaCollection(arenasize, pagesize, 99)
    assert ac.arenas_start == ac.arenas_end == ARENA_NULL
    #
    page = ac.allocate_new_page(5)
    checknewpage(page, 5)
    a = ac.arenas_start
    assert a != ARENA_NULL
    assert a == ac.arenas_end
    assert a.nfreepages == 2
    assert a.freepage == a.arena_base + SHIFT + pagesize
    assert ac.page_for_size[5] == page
    #
    page = ac.allocate_new_page(3)
    checknewpage(page, 3)
    assert a == ac.arenas_start == ac.arenas_end
    assert a.nfreepages == 1
    assert a.freepage == a.arena_base + SHIFT + 2*pagesize
    assert ac.page_for_size[3] == page
    #
    page = ac.allocate_new_page(4)
    checknewpage(page, 4)
    assert ac.arenas_start == ac.arenas_end == ARENA_NULL  # has been unlinked
    assert ac.page_for_size[4] == page


def arena_collection_for_test(pagesize, *pagelayouts):
    nb_pages = len(pagelayouts[0])
    arenasize = pagesize * (nb_pages + 1) - 1
    ac = gen2.ArenaCollection(arenasize, pagesize, 9*WORD)
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
        a = gen2.allocate_arena(arenasize, pagesize)
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
    # Test supposing that we have two partially-used arenas
    pagesize = hdrsize + 16
    ac = arena_collection_for_test(pagesize,
                                   "##.. ",
                                   ".#   ")
    assert ac.arenas_start.nfreepages == 3
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
