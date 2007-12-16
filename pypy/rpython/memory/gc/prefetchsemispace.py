from pypy.rpython.memory.gc.semispace import SemiSpaceGC
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.rpython.extfunc import register_external
from pypy.rpython.lltypesystem.llmemory import NULL

def prefetch(addr):
    """This function is used to minimize cache-miss latency by moving
    data into a cache before it is accessed.  You can insert calls to
    it into code for which you know addresses of data in memory that
    is likely to be accessed soon.

    XXX requires gcc.
    XXX You also need to tweak the Makefile to set
                       CFLAGS = -O2 -pthread -march=pentium3m
    XXX and recompile.
    """

__builtin_prefetch = rffi.llexternal(
    '__builtin_prefetch',
    [llmemory.Address, lltype.Signed, lltype.Signed],
    lltype.Void,
    sandboxsafe=True, _nowrapper=True)

def llimpl_prefetch(addr):
    __builtin_prefetch(addr, 0, 3)
register_external(prefetch, [llmemory.Address], lltype.Void,
                  'll_hack.builtin_prefetch',
                  llimpl=llimpl_prefetch,
                  llfakeimpl=prefetch,
                  sandboxsafe=True)

# ____________________________________________________________

# The prefetch_queue is a circular first-in first-out buffer.
# prefetch_queue_next is the index of the next item in prefetch_queue
# that needs to be removed from the queue, processed, and replaced
# by the incoming element.  At the beginning, the queue is empty,
# which we represent by filling it with NULLs.


class PrefetchSemiSpaceGC(SemiSpaceGC):

    def __init__(self, *args, **kwds):
        prefetch_queue_size = kwds.pop('prefetch_queue_size', 4)
        SemiSpaceGC.__init__(self, *args, **kwds)
        assert prefetch_queue_size & (prefetch_queue_size-1) == 0, (
            "prefetch_queue_size must be a power of 2")
        self.prefetch_queue = lltype.malloc(
            lltype.FixedSizeArray(llmemory.Address, prefetch_queue_size),
            immortal=True)
        self.prefetch_queue_mask = prefetch_queue_size - 1

    def scan_copied(self, scan):
        # prepare the prefetch queue
        i = self.prefetch_queue_mask
        while i >= 0:
            self.prefetch_queue[i] = NULL
            i -= 1
        self.prefetch_queue_next = 0
        # scan
        while True:
            if scan == self.free:
                # flush the remaining items in the prefetch queue
                i = self.prefetch_queue_mask
                while i >= 0:
                    self.record_pointer_for_tracing(NULL)
                    i -= 1
                if scan == self.free:
                    break     # finished
            curr = scan + self.size_gc_header()
            self.trace_and_copy_lazy(curr)
            scan += self.size_gc_header() + self.get_size(curr)
        return scan

    def trace_and_copy_lazy(self, obj):
        self.trace(obj, self._trace_copy_lazy, None)

    def _trace_copy_lazy(self, pointer, ignored):
        if pointer.address[0] != NULL:
            prefetch(pointer.address[0])
            self.record_pointer_for_tracing(pointer)

    def record_pointer_for_tracing(self, pointer):
        i = self.prefetch_queue_next
        oldpointer = self.prefetch_queue[i]
        self.prefetch_queue[i] = pointer
        self.prefetch_queue_next = (i + 1) & self.prefetch_queue_mask
        if oldpointer != NULL:
            oldpointer.address[0] = self.copy(oldpointer.address[0])
    record_pointer_for_tracing.dont_inline = True
