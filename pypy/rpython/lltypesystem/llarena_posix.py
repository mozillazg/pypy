import os, sys
from pypy.rpython.lltypesystem import rffi, lltype, llmemory
from pypy.rpython.lltypesystem.llarena_llinterp import Z_CLEAR_LARGE_AREA
from pypy.rpython.lltypesystem.llarena_llinterp import Z_CLEAR_SMALL_AREA
from pypy.rpython.lltypesystem.llarena_llinterp import Z_INACCESSIBLE
from pypy.rpython.lltypesystem.llarena_llinterp import Z_ACCESSIBLE

implements_inaccessible = True

# ____________________________________________________________

posix_getpagesize = rffi.llexternal('getpagesize', [], rffi.INT,
                                    sandboxsafe=True, _nowrapper=True)
class PosixPageSize:
    def __init__(self):
        self.pagesize = 0
    _freeze_ = __init__
posix_pagesize = PosixPageSize()

def getpagesize():
    pagesize = posix_pagesize.pagesize
    if pagesize == 0:
        pagesize = rffi.cast(lltype.Signed, posix_getpagesize())
        posix_pagesize.pagesize = pagesize
    return pagesize

# ____________________________________________________________

if sys.platform == 'linux2':
    # This only works with linux's madvise(), which is really not a memory
    # usage hint but a real command.  It guarantees that after MADV_DONTNEED
    # the pages are cleared again.
    from pypy.rpython.tool import rffi_platform
    MADV_DONTNEED = rffi_platform.getconstantinteger('MADV_DONTNEED',
                                                     '#include <sys/mman.h>')
    linux_madvise = rffi.llexternal('madvise',
                                    [llmemory.Address, rffi.SIZE_T, rffi.INT],
                                    rffi.INT,
                                    sandboxsafe=True, _nowrapper=True)

    def clear_large_memory_chunk(baseaddr, size):
        madv_length = rffi.cast(rffi.SIZE_T, size)
        madv_flags = rffi.cast(rffi.INT, MADV_DONTNEED)
        err = linux_madvise(baseaddr, madv_length, madv_flags)
        if rffi.cast(lltype.Signed, err) != 0:       # did not work!
            llmemory.raw_memclear(baseaddr, size)    # clear manually...

else:
    READ_MAX = (sys.maxint//4) + 1    # upper bound on reads to avoid surprises
    raw_os_open = rffi.llexternal('open',
                                  [rffi.CCHARP, rffi.INT, rffi.MODE_T],
                                  rffi.INT,
                                  sandboxsafe=True, _nowrapper=True)
    raw_os_read = rffi.llexternal('read',
                                  [rffi.INT, llmemory.Address, rffi.SIZE_T],
                                  rffi.SIZE_T,
                                  sandboxsafe=True, _nowrapper=True)
    raw_os_close = rffi.llexternal('close',
                                   [rffi.INT],
                                   rffi.INT,
                                   sandboxsafe=True, _nowrapper=True)
    _dev_zero = rffi.str2charp('/dev/zero')   # prebuilt

    def clear_large_memory_chunk(baseaddr, size):
        # on some Unixy platforms, reading from /dev/zero is the fastest way
        # to clear arenas, because the kernel knows that it doesn't
        # need to even allocate the pages before they are used.

        # NB.: careful, don't do anything that could malloc here!
        # this code is called during GC initialization.
        fd = raw_os_open(_dev_zero,
                         rffi.cast(rffi.INT, os.O_RDONLY),
                         rffi.cast(rffi.MODE_T, 0644))
        if rffi.cast(lltype.Signed, fd) != -1:
            while size > 0:
                size1 = rffi.cast(rffi.SIZE_T, min(READ_MAX, size))
                count = raw_os_read(fd, baseaddr, size1)
                count = rffi.cast(lltype.Signed, count)
                if count <= 0:
                    break
                size -= count
                baseaddr += count
            raw_os_close(fd)

        if size > 0:     # reading from /dev/zero failed, fallback
            llmemory.raw_memclear(baseaddr, size)

# ____________________________________________________________

# llimpl_arena_*() functions based on mmap
from pypy.rpython.tool import rffi_platform
from pypy.translator.tool.cbuild import ExternalCompilationInfo
class CConfig:
    _compilation_info_ = ExternalCompilationInfo(
        includes=['sys/mman.h'])
    off_t = rffi_platform.SimpleType('off_t')
    PROT_NONE     = rffi_platform.ConstantInteger('PROT_NONE')
    PROT_READ     = rffi_platform.ConstantInteger('PROT_READ')
    PROT_WRITE    = rffi_platform.ConstantInteger('PROT_WRITE')
    MAP_PRIVATE   = rffi_platform.ConstantInteger('MAP_PRIVATE')
    MAP_ANON      = rffi_platform.DefinedConstantInteger('MAP_ANON')
    MAP_ANONYMOUS = rffi_platform.DefinedConstantInteger('MAP_ANONYMOUS')
    MAP_NORESERVE = rffi_platform.DefinedConstantInteger('MAP_NORESERVE')
globals().update(rffi_platform.configure(CConfig))
if MAP_ANONYMOUS is None:
    MAP_ANONYMOUS = MAP_ANON
    assert MAP_ANONYMOUS is not None
del MAP_ANON

posix_mmap = rffi.llexternal('mmap',
                             [llmemory.Address, rffi.SIZE_T, rffi.INT,
                              rffi.INT, rffi.INT, off_t],
                             llmemory.Address,
                             sandboxsafe=True, _nowrapper=True)
posix_munmap = rffi.llexternal('munmap',
                               [llmemory.Address, rffi.SIZE_T],
                               rffi.INT,
                               sandboxsafe=True, _nowrapper=True)
posix_mprotect = rffi.llexternal('mprotect',
                                 [llmemory.Address, rffi.SIZE_T,
                                  rffi.INT],
                                 rffi.INT,
                                 sandboxsafe=True, _nowrapper=True)

class MMapMemoryError(Exception):
    pass

def llimpl_arena_malloc(nbytes, zero):
    flags = MAP_PRIVATE | MAP_ANONYMOUS
    if zero == Z_INACCESSIBLE:
        prot = PROT_NONE
        if MAP_NORESERVE is not None:
            flags |= MAP_NORESERVE
    else:
        prot = PROT_READ | PROT_WRITE
    result = posix_mmap(llmemory.NULL,
                        rffi.cast(rffi.SIZE_T, nbytes),
                        rffi.cast(rffi.INT, prot),
                        rffi.cast(rffi.INT, flags),
                        rffi.cast(rffi.INT, -1),
                        rffi.cast(off_t, 0))
    if rffi.cast(lltype.Signed, result) == -1:
        raise MMapMemoryError
    return result

def llimpl_arena_free(arena_addr, nbytes):
    result = posix_munmap(arena_addr, rffi.cast(rffi.SIZE_T, nbytes))
    if rffi.cast(lltype.Signed, result) == -1:
        raise MMapMemoryError

def _arena_protect(arena_addr, size, flags):
    res = posix_mprotect(arena_addr,
                         rffi.cast(rffi.SIZE_T, size),
                         rffi.cast(rffi.INT, flags))
    if rffi.cast(lltype.Signed, res) != 0:
        raise MMapMemoryError

def llimpl_arena_reset(arena_addr, size, zero):
    if zero == Z_CLEAR_LARGE_AREA:
        clear_large_memory_chunk(arena_addr, size)
    elif zero == Z_CLEAR_SMALL_AREA:
        llmemory.raw_memclear(arena_addr, size)
    elif zero == Z_ACCESSIBLE:
        _arena_protect(arena_addr, size, PROT_READ | PROT_WRITE)
    elif zero == Z_INACCESSIBLE:
        clear_large_memory_chunk(arena_addr, size)
        _arena_protect(arena_addr, size, PROT_NONE)
