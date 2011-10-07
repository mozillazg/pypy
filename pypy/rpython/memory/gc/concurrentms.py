import time, sys
from pypy.rpython.lltypesystem import lltype, llmemory, llarena, llgroup, rffi
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.lltypesystem.llmemory import raw_malloc_usage
from pypy.rlib.objectmodel import we_are_translated, specialize
from pypy.rlib.debug import ll_assert
from pypy.rlib.rarithmetic import LONG_BIT, r_uint
from pypy.rpython.memory.gc.base import GCBase
from pypy.module.thread import ll_thread

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
first_gcflag = 1 << (LONG_BIT//2)

GCFLAG_MARK_TOGGLE = first_gcflag << 0
GCFLAG_FINALIZATION_ORDERING = first_gcflag << 1


class MostlyConcurrentMarkSweepGC(GCBase):
    _alloc_flavor_ = "raw"
    inline_simple_malloc = True
    inline_simple_malloc_varsize = True
    needs_write_barrier = True
    prebuilt_gc_objects_are_static_roots = False
    malloc_zero_filled = True
    gcflag_extra = GCFLAG_FINALIZATION_ORDERING

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
        self.current_mark = 0
        #
        # When the mutator thread wants to trigger the next collection,
        # it scans its own stack roots and prepares everything, then
        # sets 'collection_running' to True, and releases
        # 'ready_to_start_lock'.  This triggers the collector thread,
        # which re-acquires 'ready_to_start_lock' and does its job.
        # When done it releases 'finished_lock'.  The mutator thread is
        # responsible for resetting 'collection_running' to False.
        self.collection_running = False
        self.ready_to_start_lock = ll_thread.allocate_lock()
        self.finished_lock = ll_thread.allocate_lock()
        #
        # NOT_RPYTHON: set to non-empty in _teardown()
        self._teardown_now = []
        #
        def collector_start():
            self.collector_run()
        self.collector_start = collector_start
        #
        self.mutex_lock = ll_thread.allocate_lock()
        self.gray_objects = self.AddressStack()
        self.extra_objects_to_mark = self.AddressStack()
        #
        # Write barrier: actually a deletion barrier, triggered when there
        # is a collection running and the mutator tries to change an object
        # that was not scanned yet.
        self._init_writebarrier_logic()

    def setup(self):
        "Start the concurrent collector thread."
        self.acquire(self.finished_lock)
        self.acquire(self.ready_to_start_lock)
        self.collector_ident = ll_thread.start_new_thread(
            self.collector_start, ())

    def _teardown(self):
        "NOT_RPYTHON.  Stop the collector thread after tests have run."
        self.wait_for_the_end_of_collection()
        #
        # start the next collection, but with "stop" in _teardown_now,
        # which should shut down the collector thread
        self._teardown_now.append("stop")
        self.collect()

    def get_type_id(self, obj):
        tid = self.header(obj).tid
        return llop.extract_ushort(llgroup.HALFWORD, tid)

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
                hdr.tid = self.combine(typeid, self.current_mark)
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
            hdr.tid = self.combine(typeid, self.current_mark)
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


    def write_barrier(self, newvalue, addr_struct):
        flag = self.header(addr_struct).tid & GCFLAG_MARK_TOGGLE
        if flag != self.current_mark:
            self.force_scan(addr_struct)

    def _init_writebarrier_logic(self):
        #
        def force_scan(obj):
            self.mutex_lock.acquire(True)
            if self.current_mark:
                self.set_mark_flag(obj, GCFLAG_MARK_TOGGLE)
            else:
                self.set_mark_flag(obj, 0)
            self.trace(obj, self._barrier_add_extra, None)
            self.mutex_lock.release()
        #
        force_scan._dont_inline_ = True
        self.force_scan = force_scan

    def _barrier_add_extra(self, root, ignored):
        self.extra_objects_to_mark.append(root.address[0])


    def collect(self, gen=0):
        """Trigger a complete collection, and wait for it to finish."""
        self.trigger_next_collection()
        self.wait_for_the_end_of_collection()

    def wait_for_the_end_of_collection(self):
        """In the mutator thread: wait for the collection currently
        running (if any) to finish."""
        if self.collection_running:
            self.acquire(self.finished_lock)
            self.collection_running = False
            #
            # It's possible that an object was added to 'extra_objects_to_mark'
            # by the write barrier but not taken out by the collector thread,
            # because it finished in the meantime.  The result is still
            # correct, but we need to clear the list.
            self.extra_objects_to_mark.clear()

    def trigger_next_collection(self):
        """In the mutator thread: triggers the next collection."""
        #
        # In case the previous collection is not over yet, wait for it
        self.wait_for_the_end_of_collection()
        #
        # Scan the stack roots and the refs in non-GC objects
        self.root_walker.walk_roots(
            MostlyConcurrentMarkSweepGC._add_stack_root,  # stack roots
            MostlyConcurrentMarkSweepGC._add_stack_root,  # in prebuilt non-gc
            None)                         # static in prebuilt gc
        #
        # Invert this global variable, which has the effect that on all
        # objects' state go instantly from "marked" to "non marked"
        self.current_mark ^= GCFLAG_MARK_TOGGLE
        #
        # Start the collector thread
        self.collection_running = True
        self.ready_to_start_lock.release()

    def _add_stack_root(self, root):
        obj = root.address[0]
        self.gray_objects.append(obj)

    def acquire(self, lock):
        if we_are_translated():
            lock.acquire(True)
        else:
            while not lock.acquire(False):
                time.sleep(0.001)
                # ---------- EXCEPTION FROM THE COLLECTOR THREAD ----------
                if hasattr(self, '_exc_info'):
                    self._reraise_from_collector_thread()

    def _reraise_from_collector_thread(self):
        exc, val, tb = self._exc_info
        raise exc, val, tb


    def collector_run(self):
        """Main function of the collector's thread."""
        try:
            while True:
                #
                # Wait for the lock to be released
                self.acquire(self.ready_to_start_lock)
                #
                # For tests: detect when we have to shut down
                if not we_are_translated():
                    if self._teardown_now:
                        self.finished_lock.release()
                        break
                #
                # Mark
                self.collector_mark()
                #
                # Sweep
                self.collector_sweep()
        except Exception, e:
            print 'Crash!', e.__class__.__name__, e
            self._exc_info = sys.exc_info()

    @specialize.arg(2)
    def is_marked(self, obj, current_mark):
        return (self.header(obj).tid & GCFLAG_MARK_TOGGLE) == current_mark

    @specialize.arg(2)
    def set_mark_flag(self, obj, current_mark):
        if current_mark:
            self.header(obj).tid |= GCFLAG_MARK_TOGGLE
        else:
            self.header(obj).tid &= ~GCFLAG_MARK_TOGGLE

    def collector_mark(self):
        while True:
            #
            # Do marking.  The following function call is interrupted
            # if the mutator's write barrier adds new objects to
            # 'extra_objects_to_mark'.
            if self.current_mark:
                self._collect_mark(GCFLAG_MARK_TOGGLE)
            else:
                self._collect_mark(0)
            #
            # Move the objects from 'extra_objects_to_mark' to
            # 'gray_objects'.  This requires the mutex lock.
            # There are typically only a few objects to move here,
            # unless XXX we've hit the write barrier of a large array
            self.mutex_lock.acquire(True)
            while self.extra_objects_to_mark.non_empty():
                obj = self.extra_objects_to_mark.pop()
                self.gray_objects.append(obj)
            self.mutex_lock.release()
            #
            # If 'gray_objects' is empty, we are done: there should be
            # no possible case in which more objects are being added to
            # 'extra_objects_to_mark' concurrently, because 'gray_objects'
            # and 'extra_objects_to_mark' were already empty before we
            # acquired the 'mutex_lock', so all reachable objects have
            # been marked.
            if not self.gray_objects.non_empty():
                return

    @specialize.arg(1)
    def _collect_mark(self, current_mark):
        while self.gray_objects.non_empty():
            obj = self.gray_objects.pop()
            if not self.is_marked(obj, current_mark):
                self.set_mark_flag(obj, current_mark)
                self.trace(obj, self._collect_add_pending, None)
                #
                # Interrupt early if the mutator's write barrier adds stuff
                # to that list.  Note that the check is imprecise because
                # it is not lock-protected, but that's good enough.  The
                # idea is that we trace in priority objects flagged with
                # the write barrier, because they are more likely to
                # reference further objects that will soon be accessed too.
                if self.extra_objects_to_mark.non_empty():
                    return

    def _collect_add_pending(self, root, ignored):
        self.gray_objects.append(root.address[0])

    def collector_sweep(self):
        xxx
