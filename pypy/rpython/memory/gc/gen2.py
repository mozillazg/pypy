from pypy.rpython.lltypesystem import lltype, llarena
from pypy.rpython.memory.gc.base import MovingGCBase
from pypy.rpython.memory.support import DEFAULT_CHUNK_SIZE
from pypy.rlib.rarithmetic import LONG_BIT
from pypy.rlib.objectmodel import we_are_translated

WORD = LONG_BIT // 8

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
        # 'freepages' points to the first unused page
        self.freepages = start_of_page(self.arena_base + page_size - 1,
                                       page_size)
        # 'nfreepages' is the number of unused pages
        arena_end = self.arena_base + self.arena_size
        self.nfreepages = (arena_end - self.freepages) / page_size

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
    shift = page_size // 2     # for testing, assuming the whole arena is not
                               # on a page boundary
    ofs = ((addr.offset - shift) & ~(page_size-1)) + shift
    return llarena.fakearenaaddress(addr.arena, ofs)

# ____________________________________________________________

def nursery_size_from_env():
    return read_from_env('PYPY_GENERATIONGC_NURSERY')
