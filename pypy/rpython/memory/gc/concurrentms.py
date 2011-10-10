import time, sys
from pypy.rpython.lltypesystem import lltype, llmemory, llarena, llgroup, rffi
from pypy.rpython.lltypesystem.llmemory import raw_malloc_usage
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.annlowlevel import llhelper
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.rlib.objectmodel import we_are_translated, running_on_llinterp
from pypy.rlib.debug import ll_assert, debug_print, debug_start, debug_stop
from pypy.rlib.rarithmetic import ovfcheck, LONG_BIT, r_uint
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
WORD_POWER_2 = {32: 2, 64: 3}[LONG_BIT]
assert 1 << WORD_POWER_2 == WORD
MAXIMUM_SIZE = sys.maxint - (3*WORD-1)


# Objects start with an integer 'tid', which is decomposed as follows.
# Lowest byte: one of the the following values (which are all odd, so
# let us know if the 'tid' is valid or is just a word-aligned address):
MARK_VALUE_1      = 0x4D    # 'M', 77
MARK_VALUE_2      = 0x6B    # 'k', 107
MARK_VALUE_STATIC = 0x53    # 'S', 83
# Next lower byte: a combination of flags.
FL_WITHHASH              = 0x0100
FL_EXTRA                 = 0x0200
# And the high half of the word contains the numeric typeid.


class MostlyConcurrentMarkSweepGC(GCBase):
    _alloc_flavor_ = "raw"
    inline_simple_malloc = True
    inline_simple_malloc_varsize = True
    needs_write_barrier = True
    prebuilt_gc_objects_are_static_roots = False
    malloc_zero_filled = True
    gcflag_extra = FL_EXTRA

    HDR = lltype.Struct('header', ('tid', lltype.Signed))
    HDRPTR = lltype.Ptr(HDR)
    HDRSIZE = llmemory.sizeof(HDR)
    NULL = lltype.nullptr(HDR)
    typeid_is_in_field = 'tid', llgroup.HALFSHIFT
    withhash_flag_is_in_field = 'tid', FL_WITHHASH
    # ^^^ prebuilt objects may have the flag FL_WITHHASH;
    #     then they are one word longer, the extra word storing the hash.

    TRANSLATION_PARAMS = {'page_size': 16384,
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
        self.pagelists_length = small_request_threshold // WORD + 1
        #
        # The following are arrays of 36 linked lists: the linked lists
        # at indices 1 to 35 correspond to pages that store objects of
        # size  1 * WORD  to  35 * WORD,  and the linked list at index 0
        # is a list of all larger objects.
        def list_of_addresses_per_small_size():
            return lltype.malloc(rffi.CArray(self.HDRPTR),
                                 self.pagelists_length, flavor='raw',
                                 immortal=True)
        # 1-35: a linked list of all pages; 0: a linked list of all larger objs
        self.nonfree_pages = list_of_addresses_per_small_size()
        # a snapshot of 'nonfree_pages' done when the collection starts
        self.collect_pages = list_of_addresses_per_small_size()
        # 1-35: free list of non-allocated locations; 0: unused
        self.free_lists    = list_of_addresses_per_small_size()
        # 1-35: head and tail of the free list built by the collector thread
        # 0: head and tail of the linked list of surviving large objects
        self.collect_heads = list_of_addresses_per_small_size()
        self.collect_tails = list_of_addresses_per_small_size()
        #
        def collector_start():
            if we_are_translated():
                self.collector_run()
            else:
                self.collector_run_nontranslated()
        #
        collector_start._should_never_raise_ = True
        self.collector_start = collector_start
        #
        self.gray_objects = self.AddressStack()
        self.extra_objects_to_mark = self.AddressStack()
        self.prebuilt_root_objects = self.AddressStack()
        #
        self._initialize()
        #
        # Write barrier: actually a deletion barrier, triggered when there
        # is a collection running and the mutator tries to change an object
        # that was not scanned yet.
        self._init_writebarrier_logic()

    def _clear_list(self, array):
        i = 0
        while i < self.pagelists_length:
            array[i] = lltype.nullptr(self.HDR)
            i += 1

    def _initialize(self):
        self.free_pages = lltype.nullptr(self.HDR)
        #
        # Clear the lists
        self._clear_list(self.nonfree_pages)
        self._clear_list(self.collect_pages)
        self._clear_list(self.free_lists)
        self._clear_list(self.collect_heads)
        self._clear_list(self.collect_tails)
        #
        # The following character is either MARK_VALUE_1 or MARK_VALUE_2,
        # and represents the character that must be in the 'mark' field
        # of an object header in order for the object to be considered as
        # marked.  Objects whose 'mark' field have the opposite value are
        # not marked yet; the collector thread will mark them if they are
        # still alive, or sweep them away if they are not reachable.
        # The special value MARK_VALUE_STATIC is initially used in the
        # 'mark' field of static prebuilt GC objects.
        self.current_mark = MARK_VALUE_1
        #
        # When the mutator thread wants to trigger the next collection,
        # it scans its own stack roots and prepares everything, then
        # sets 'collection_running' to 1, and releases
        # 'ready_to_start_lock'.  This triggers the collector thread,
        # which re-acquires 'ready_to_start_lock' and does its job.
        # When done it releases 'finished_lock'.  The mutator thread is
        # responsible for resetting 'collection_running' to 0.
        self.collection_running = 0
        #self.ready_to_start_lock = ...built in setup()
        #self.finished_lock = ...built in setup()
        #
        #self.mutex_lock = ...built in setup()
        self.gray_objects.clear()
        self.extra_objects_to_mark.clear()
        self.prebuilt_root_objects.clear()

    def setup(self):
        "Start the concurrent collector thread."
        GCBase.setup(self)
        #
        self.main_thread_ident = ll_thread.get_ident()
        self.ready_to_start_lock = ll_thread.allocate_ll_lock()
        self.finished_lock = ll_thread.allocate_ll_lock()
        self.mutex_lock = ll_thread.allocate_ll_lock()
        #
        self.acquire(self.finished_lock)
        self.acquire(self.ready_to_start_lock)
        #
        self.collector_ident = ll_thread.c_thread_start_nowrapper(
            llhelper(ll_thread.CALLBACK, self.collector_start))
        assert self.collector_ident != -1

    def _teardown(self):
        "Stop the collector thread after tests have run."
        self.wait_for_the_end_of_collection()
        #
        # start the next collection, but with collection_running set to 42,
        # which should shut down the collector thread
        self.collection_running = 42
        debug_print("teardown!")
        self.release(self.ready_to_start_lock)
        self.acquire(self.finished_lock)
        self._initialize()

    def get_type_id(self, obj):
        tid = self.header(obj).tid
        return llop.extract_high_ushort(llgroup.HALFWORD, tid)

    def combine(self, typeid16, mark, flags):
        return llop.combine_high_ushort(lltype.Signed, typeid16, mark | flags)

    def init_gc_object_immortal(self, addr, typeid, flags=0):
        # 'flags' is ignored here
        hdr = llmemory.cast_adr_to_ptr(addr, lltype.Ptr(self.HDR))
        hdr.tid = self.combine(typeid, MARK_VALUE_STATIC, 0)

    def malloc_fixedsize_clear(self, typeid, size,
                               needs_finalizer=False, contains_weakptr=False):
        assert not needs_finalizer  # XXX
        # contains_weakptr: detected during collection
        size_gc_header = self.gcheaderbuilder.size_gc_header
        totalsize = size_gc_header + size
        rawtotalsize = raw_malloc_usage(totalsize)
        if rawtotalsize <= self.small_request_threshold:
            ll_assert(rawtotalsize & (WORD - 1) == 0,
                      "fixedsize not properly rounded")
            #
            n = rawtotalsize >> WORD_POWER_2
            result = self.free_lists[n]
            if result != self.NULL:
                self.free_lists[n] = self.cast_int_to_hdrptr(result.tid)
                obj = self.grow_reservation(result, totalsize)
                hdr = self.header(obj)
                hdr.tid = self.combine(typeid, self.current_mark, 0)
                return llmemory.cast_adr_to_ptr(obj, llmemory.GCREF)
                #
        return self._malloc_slowpath(typeid, size)

    def malloc_varsize_clear(self, typeid, length, size, itemsize,
                             offset_to_length):
        size_gc_header = self.gcheaderbuilder.size_gc_header
        nonvarsize = size_gc_header + size
        #
        # Compute the maximal length that makes the object still below
        # 'small_request_threshold'.  All the following logic is usually
        # constant-folded because size and itemsize are constants (due
        # to inlining).
        maxsize = self.small_request_threshold - raw_malloc_usage(nonvarsize)
        if maxsize < 0:
            toobig = r_uint(0)    # the nonvarsize alone is too big
        elif raw_malloc_usage(itemsize):
            toobig = r_uint(maxsize // raw_malloc_usage(itemsize)) + 1
        else:
            toobig = r_uint(sys.maxint) + 1

        if r_uint(length) < r_uint(toobig):
            # With the above checks we know now that totalsize cannot be more
            # than 'small_request_threshold'; in particular, the + and *
            # cannot overflow.
            totalsize = nonvarsize + itemsize * length
            totalsize = llarena.round_up_for_allocation(totalsize)
            rawtotalsize = raw_malloc_usage(totalsize)
            ll_assert(rawtotalsize & (WORD - 1) == 0,
                      "round_up_for_allocation failed")
            #
            n = rawtotalsize >> WORD_POWER_2
            result = self.free_lists[n]
            if result != self.NULL:
                self.free_lists[n] = self.cast_int_to_hdrptr(result.tid)
                obj = self.grow_reservation(result, totalsize)
                hdr = self.header(obj)
                hdr.tid = self.combine(typeid, self.current_mark, 0)
                (obj + offset_to_length).signed[0] = length
                return llmemory.cast_adr_to_ptr(obj, llmemory.GCREF)
        #
        # If the total size of the object would be larger than
        # 'small_request_threshold', or if the free_list is empty,
        # then allocate it externally.  We also go there if 'length'
        # is actually negative.
        return self._malloc_varsize_slowpath(typeid, length)

    def _malloc_slowpath(self, typeid, size):
        # Slow-path malloc.  Call this with 'size' being a valid and
        # rounded number, between WORD and up to MAXIMUM_SIZE.
        #
        # For now, we always start the next collection immediately.
        if self.collection_running <= 0:
            self.trigger_next_collection()
        #
        size_gc_header = self.gcheaderbuilder.size_gc_header
        totalsize = size_gc_header + size
        rawtotalsize = raw_malloc_usage(totalsize)
        ll_assert(rawtotalsize & (WORD - 1) == 0,
                  "malloc_slowpath: non-rounded size")
        #
        if rawtotalsize <= self.small_request_threshold:
            #
            # Case 1: unless trigger_next_collection() happened to get us
            # more locations in free_lists[n], we have run out of them
            n = rawtotalsize >> WORD_POWER_2
            head = self.free_lists[n]
            if head:
                self.free_lists[n] = self.cast_int_to_hdrptr(head.tid)
                obj = self.grow_reservation(head, totalsize)
                hdr = self.header(obj)
                hdr.tid = self.combine(typeid, self.current_mark, 0)
                return llmemory.cast_adr_to_ptr(obj, llmemory.GCREF)
            #
            # We really have run out of the free list corresponding to
            # the size.  Grab the next free page.
            newpage = self.free_pages
            if newpage == self.NULL:
                self.allocate_next_arena()
                newpage = self.free_pages
            self.free_pages = self.cast_int_to_hdrptr(newpage.tid)
            #
            # Put the free page in the list 'nonfree_pages[n]'.  This is
            # a linked list chained through the first word of each page.
            newpage.tid = self.cast_hdrptr_to_int(self.nonfree_pages[n])
            self.nonfree_pages[n] = newpage
            #
            # Initialize the free page to contain objects of the given
            # size.  This requires setting up all object locations in the
            # page, linking them in the free list.
            i = self.page_size - rawtotalsize
            limit = rawtotalsize + raw_malloc_usage(self.HDRSIZE)
            newpageadr = llmemory.cast_ptr_to_adr(newpage)
            newpageadr = llarena.getfakearenaaddress(newpageadr)
            while i >= limit:
                adr = newpageadr + i
                llarena.arena_reserve(adr, self.HDRSIZE)
                p = llmemory.cast_adr_to_ptr(adr, self.HDRPTR)
                p.tid = self.cast_hdrptr_to_int(head)
                head = p
                i -= rawtotalsize
            self.free_lists[n] = head
            result = newpageadr + i
            #
            # Done: all object locations are linked, apart from
            # 'result', which is the first object location in the page.
            # Note that if the size is not an exact divisor of
            # 4096-WORD, there are a few wasted WORDs, which we place at
            # the start of the page rather than at the end (Hans Boehm,
            # xxx ref).
            #
        else:
            # Case 2: the object is too large, so allocate it directly
            # with the system malloc().  xxx on 32-bit, we'll prefer 64-bit
            # alignment of the object by always allocating an 8-bytes header
            rawtotalsize += 8
            block = llarena.arena_malloc(rawtotalsize, 2)
            if not block:
                raise MemoryError
            llarena.arena_reserve(block, self.HDRSIZE)
            blockhdr = llmemory.cast_adr_to_ptr(block, self.HDRPTR)
            blockhdr.tid = self.cast_hdrptr_to_int(self.nonfree_pages[0])
            self.nonfree_pages[0] = blockhdr
            result = block + 8
        #
        llarena.arena_reserve(result, totalsize)
        hdr = llmemory.cast_adr_to_ptr(result, self.HDRPTR)
        hdr.tid = self.combine(typeid, self.current_mark, 0)
        #
        obj = result + size_gc_header
        return llmemory.cast_adr_to_ptr(obj, llmemory.GCREF)
        #
    _malloc_slowpath._dont_inline_ = True

    def _malloc_varsize_slowpath(self, typeid, length):
        #
        if length < 0:
            # negative length!  This likely comes from an overflow
            # earlier.  We will just raise MemoryError here.
            raise MemoryError
        #
        # Compute the total size, carefully checking for overflows.
        nonvarsize = self.fixed_size(typeid)
        itemsize = self.varsize_item_sizes(typeid)
        try:
            varsize = ovfcheck(itemsize * length)
            totalsize = ovfcheck(nonvarsize + varsize)
        except OverflowError:
            raise MemoryError
        #
        # Detect very rare cases of overflows
        if raw_malloc_usage(totalsize) > MAXIMUM_SIZE:
            raise MemoryError("rare case of overflow")
        #
        totalsize = llarena.round_up_for_allocation(totalsize)
        result = self._malloc_slowpath(typeid, totalsize)
        #
        offset_to_length = self.varsize_offset_to_length(typeid)
        obj = llmemory.cast_ptr_to_adr(result)
        (obj + offset_to_length).signed[0] = length
        return result
    _malloc_varsize_slowpath._dont_inline_ = True

    # ----------
    # Other functions in the GC API

    #def set_max_heap_size(self, size):
    #    XXX

    #def raw_malloc_memory_pressure(self, sizehint):
    #    XXX

    #def shrink_array(self, obj, smallerlength):
    #    return False

    def enumerate_all_roots(self, callback, arg):
        self.prebuilt_root_objects.foreach(callback, arg)
        GCBase.enumerate_all_roots(self, callback, arg)
    enumerate_all_roots._annspecialcase_ = 'specialize:arg(1)'

    def identityhash(self, obj):
        obj = llmemory.cast_ptr_to_adr(obj)
        if self.header(obj).tid & FL_WITHHASH:
            obj += self.get_size(obj)
            return obj.signed[0]
        else:
            return llmemory.cast_adr_to_int(obj)

    # ----------

    def allocate_next_arena(self):
        # xxx for now, allocate one page at a time with the system malloc()
        page = llarena.arena_malloc(self.page_size, 2)     # zero-filled
        if not page:
            raise MemoryError
        llarena.arena_reserve(page, self.HDRSIZE)
        page = llmemory.cast_adr_to_ptr(page, self.HDRPTR)
        page.tid = 0
        self.free_pages = page

    def grow_reservation(self, hdr, totalsize):
        # Transform 'hdr', which used to point to just a HDR,
        # into a pointer to a full object of size 'totalsize'.
        # This is a no-op after translation.  Returns the
        # address of the full object.
        adr = llmemory.cast_ptr_to_adr(hdr)
        adr = llarena.getfakearenaaddress(adr)
        llarena.arena_reset(adr, self.HDRSIZE, 0)
        llarena.arena_reserve(adr, totalsize)
        return adr + self.gcheaderbuilder.size_gc_header
    grow_reservation._always_inline_ = True

    def write_barrier(self, newvalue, addr_struct):
        mark = self.header(addr_struct).tid & 0xFF
        if mark != self.current_mark:
            self.force_scan(addr_struct)

    def writebarrier_before_copy(self, source_addr, dest_addr,
                                 source_start, dest_start, length):
        mark = self.header(dest_addr).tid & 0xFF
        if mark != self.current_mark:
            self.force_scan(dest_addr)
        return True

    def assume_young_pointers(self, addr_struct):
        pass # XXX

    def _init_writebarrier_logic(self):
        #
        def force_scan(obj):
            self.acquire(self.mutex_lock)
            mark = self.header(obj).tid & 0xFF
            if mark != self.current_mark:
                #
                if mark == MARK_VALUE_STATIC:
                    # This is the first write into a prebuilt GC object.
                    # Record it in 'prebuilt_root_objects'.  Even if a
                    # collection marking phase is running now, we can
                    # ignore this object, because at the snapshot-at-the-
                    # beginning it didn't contain any pointer to non-
                    # prebuilt objects.
                    self.prebuilt_root_objects.append(obj)
                    self.set_mark(obj, self.current_mark)
                    #
                else:
                    # it is only possible to reach this point if there is
                    # a collection running in collector_mark(), before it
                    # does mutex_lock itself.  Check this:
                    ll_assert(self.collection_running == 1,
                              "write barrier: wrong call?")
                    #
                    self.set_mark(obj, self.current_mark)
                    self.trace(obj, self._barrier_add_extra, None)
                #
            self.release(self.mutex_lock)
        #
        force_scan._dont_inline_ = True
        self.force_scan = force_scan

    def _barrier_add_extra(self, root, ignored):
        self.extra_objects_to_mark.append(root.address[0])


    def wait_for_the_end_of_collection(self):
        """In the mutator thread: wait for the collection currently
        running (if any) to finish."""
        if self.collection_running != 0:
            debug_start("gc-stop")
            #
            self.acquire(self.finished_lock)
            self.collection_running = 0
            #
            # Check invariants
            ll_assert(not self.extra_objects_to_mark.non_empty(),
                      "objs left behind in extra_objects_to_mark")
            ll_assert(not self.gray_objects.non_empty(),
                      "objs left behind in gray_objects")
            #
            # Grab the results of the last collection: read the collector's
            # 'collect_heads/collect_tails' and merge them with the mutator's
            # 'free_lists'.
            n = 1
            while n < self.pagelists_length:
                if self.collect_tails[n] != self.NULL:
                    self.collect_tails[n].tid = self.cast_hdrptr_to_int(
                        self.free_lists[n])
                    self.free_lists[n] = self.collect_heads[n]
                n += 1
            #
            # Do the same with 'collect_heads[0]/collect_tails[0]'.
            if self.collect_tails[0] != self.NULL:
                self.collect_tails[0].tid = self.cast_hdrptr_to_int(
                    self.nonfree_pages[0])
                self.nonfree_pages[0] = self.collect_heads[0]
            #
            if self.DEBUG:
                self.debug_check_lists()
            #
            debug_stop("gc-stop")


    def collect(self, gen=2):
        """
        gen=0: Trigger a collection if none is running.  Never blocks.
        
        gen=1: The same, but if a collection is running, wait for it
        to finish before triggering the next one.  Guarantees that
        objects not reachable when collect() is called will soon be
        freed.

        gen>=2: The same, but wait for the triggered collection to
        finish.  Guarantees that objects not reachable when collect()
        is called will be freed by the time collect() returns.
        """
        if gen >= 1 or self.collection_running <= 0:
            self.trigger_next_collection()
            if gen >= 2:
                self.wait_for_the_end_of_collection()

    def trigger_next_collection(self):
        """In the mutator thread: triggers the next collection."""
        #
        # In case the previous collection is not over yet, wait for it
        self.wait_for_the_end_of_collection()
        #
        debug_start("gc-start")
        #
        # Scan the stack roots and the refs in non-GC objects
        self.root_walker.walk_roots(
            MostlyConcurrentMarkSweepGC._add_stack_root,  # stack roots
            MostlyConcurrentMarkSweepGC._add_stack_root,  # in prebuilt non-gc
            None)                         # static in prebuilt gc
        #
        # Add the prebuilt root objects that have been written to
        self.prebuilt_root_objects.foreach(self._add_prebuilt_root, None)
        #
        # Invert this global variable, which has the effect that on all
        # objects' state go instantly from "marked" to "non marked"
        self.current_mark = self.other_mark(self.current_mark)
        #
        # Copy a few 'mutator' fields to 'collector' fields:
        # 'collect_pages' make linked lists of all nonfree pages at the
        # start of the collection (unlike the 'nonfree_pages' lists, which
        # the mutator will continue to grow).
        n = 0
        while n < self.pagelists_length:
            self.collect_pages[n] = self.nonfree_pages[n]
            n += 1
        self.nonfree_pages[0] = self.NULL
        #
        # Start the collector thread
        self.collection_running = 1
        self.release(self.ready_to_start_lock)
        #
        debug_stop("gc-start")

    def _add_stack_root(self, root):
        obj = root.address[0]
        self.gray_objects.append(obj)

    def _add_prebuilt_root(self, obj, ignored):
        self.gray_objects.append(obj)

    def debug_check_lists(self):
        # just check that they are correct, non-infinite linked lists
        self.debug_check_list(self.nonfree_pages[0])
        n = 1
        while n < self.pagelists_length:
            self.debug_check_list(self.free_lists[n])
            n += 1

    def debug_check_list(self, page):
        try:
            previous_page = self.NULL
            while page != self.NULL:
                # prevent constant-folding, and detects loops of length 1
                ll_assert(page != previous_page, "loop!")
                previous_page = page
                page = self.cast_int_to_hdrptr(page.tid)
        except KeyboardInterrupt:
            ll_assert(False, "interrupted")
            raise

    def acquire(self, lock):
        if (we_are_translated() or
                ll_thread.get_ident() != self.main_thread_ident):
            ll_thread.c_thread_acquirelock(lock, 1)
        else:
            while rffi.cast(lltype.Signed,
                            ll_thread.c_thread_acquirelock(lock, 0)) == 0:
                time.sleep(0.05)
                # ---------- EXCEPTION FROM THE COLLECTOR THREAD ----------
                if hasattr(self, '_exc_info'):
                    self._reraise_from_collector_thread()

    def release(self, lock):
        ll_thread.c_thread_releaselock(lock)

    def _reraise_from_collector_thread(self):
        exc, val, tb = self._exc_info
        raise exc, val, tb

    def cast_int_to_hdrptr(self, tid):
        return llmemory.cast_adr_to_ptr(llmemory.cast_int_to_adr(tid),
                                        self.HDRPTR)

    def cast_hdrptr_to_int(self, hdr):
        return llmemory.cast_adr_to_int(llmemory.cast_ptr_to_adr(hdr),
                                        "symbolic")


    def collector_run_nontranslated(self):
        try:
            if not hasattr(self, 'currently_running_in_rtyper'):
                self.collector_run()     # normal tests
            else:
                # this case is for test_transformed_gc: we need to spawn
                # another LLInterpreter for this new thread.
                from pypy.rpython.llinterp import LLInterpreter
                llinterp = LLInterpreter(self.currently_running_in_rtyper)
                # XXX FISH HORRIBLY for the graph...
                graph = sys._getframe(2).f_locals['self']._obj.graph
                llinterp.eval_graph(graph)
        except Exception, e:
            print 'Crash!', e.__class__.__name__, e
            self._exc_info = sys.exc_info()

    def collector_run(self):
        """Main function of the collector's thread."""
        #
        # hack: this is an infinite loop in practice.  During tests it can
        # be interrupted.  In all cases the annotator must not conclude that
        # it is an infinite loop: otherwise, the caller would automatically
        # end in a "raise AssertionError", annoyingly, because we don't want
        # any exception in this thread
        while True:
            #
            # Wait for the lock to be released
            self.acquire(self.ready_to_start_lock)
            #
            # For tests: detect when we have to shut down
            if self.collection_running == 42:
                self.release(self.finished_lock)
                break
            #
            # Mark
            self.collector_mark()
            self.collection_running = 2
            #
            # Sweep
            self.collector_sweep()
            #
            # Done!
            self.collection_running = -1
            self.release(self.finished_lock)


    def other_mark(self, mark):
        ll_assert(mark == MARK_VALUE_1 or mark == MARK_VALUE_2,
                  "bad mark value")
        return mark ^ (MARK_VALUE_1 ^ MARK_VALUE_2)

    def is_marked(self, obj, current_mark):
        mark = self.header(obj).tid & 0xFF
        ll_assert(mark in (MARK_VALUE_1, MARK_VALUE_2, MARK_VALUE_STATIC),
                  "bad mark byte in object")
        return mark == current_mark

    def set_mark(self, obj, newmark):
        _set_mark(self.header(obj), newmark)

    def collector_mark(self):
        while True:
            #
            # Do marking.  The following function call is interrupted
            # if the mutator's write barrier adds new objects to
            # 'extra_objects_to_mark'.
            self._collect_mark()
            #
            # Move the objects from 'extra_objects_to_mark' to
            # 'gray_objects'.  This requires the mutex lock.
            # There are typically only a few objects to move here,
            # unless XXX we've hit the write barrier of a large array
            self.acquire(self.mutex_lock)
            while self.extra_objects_to_mark.non_empty():
                obj = self.extra_objects_to_mark.pop()
                self.gray_objects.append(obj)
            self.release(self.mutex_lock)
            #
            # If 'gray_objects' is empty, we are done: there should be
            # no possible case in which more objects are being added to
            # 'extra_objects_to_mark' concurrently, because 'gray_objects'
            # and 'extra_objects_to_mark' were already empty before we
            # acquired the 'mutex_lock', so all reachable objects have
            # been marked.
            if not self.gray_objects.non_empty():
                break

    def _collect_mark(self):
        current_mark = self.current_mark
        while self.gray_objects.non_empty():
            obj = self.gray_objects.pop()
            if not self.is_marked(obj, current_mark):
                self.set_mark(obj, current_mark)
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
        n = 1
        while n < self.pagelists_length:
            self._collect_sweep_pages(n)
            n += 1
        # do this *after* the other one, so that objects are not free'd
        # before we get a chance to inspect if they contain objects that
        # are still alive (needed for weakrefs)
        self._collect_sweep_large_objects()

    def _collect_sweep_large_objects(self):
        block = self.collect_pages[0]
        nonmarked = self.other_mark(self.current_mark)
        linked_list = self.NULL
        first_block_in_linked_list = self.NULL
        while block != self.NULL:
            nextblock = self.cast_int_to_hdrptr(block.tid)
            blockadr = llmemory.cast_ptr_to_adr(block)
            blockadr = llarena.getfakearenaaddress(blockadr)
            hdr = llmemory.cast_adr_to_ptr(blockadr + 8, self.HDRPTR)
            mark = hdr.tid & 0xFF
            if mark == nonmarked:
                # the object is still not marked.  Free it.
                llarena.arena_free(blockadr)
                #
            else:
                # the object was marked: relink it
                ll_assert(mark == self.current_mark,
                          "bad mark in large object")
                block.tid = self.cast_hdrptr_to_int(linked_list)
                linked_list = block
                if first_block_in_linked_list == self.NULL:
                    first_block_in_linked_list = block
            block = nextblock
        #
        self.collect_heads[0] = linked_list
        self.collect_tails[0] = first_block_in_linked_list

    def _collect_sweep_pages(self, n):
        # sweep all pages from the linked list starting at 'page',
        # containing objects of fixed size 'object_size'.
        page = self.collect_pages[n]
        object_size = n << WORD_POWER_2
        linked_list = self.NULL
        first_loc_in_linked_list = self.NULL
        marked = self.current_mark
        nonmarked = self.other_mark(marked)
        while page != self.NULL:
            i = self.page_size - object_size
            limit = raw_malloc_usage(self.HDRSIZE)
            pageadr = llmemory.cast_ptr_to_adr(page)
            pageadr = llarena.getfakearenaaddress(pageadr)
            while i >= limit:
                adr = pageadr + i
                hdr = llmemory.cast_adr_to_ptr(adr, self.HDRPTR)
                mark = hdr.tid & 0xFF
                #
                if mark == nonmarked:
                    # the location contains really an object (and is not just
                    # part of a linked list of free locations), and moreover
                    # the object is still not marked.  Free it by inserting
                    # it into the linked list.
                    llarena.arena_reset(adr, object_size, 0)
                    llarena.arena_reserve(adr, self.HDRSIZE)
                    hdr = llmemory.cast_adr_to_ptr(adr, self.HDRPTR)
                    hdr.tid = self.cast_hdrptr_to_int(linked_list)
                    linked_list = hdr
                    if first_loc_in_linked_list == self.NULL:
                        first_loc_in_linked_list = hdr
                    # XXX detect when the whole page is freed again
                    #
                    # Clear the data, in prevision for the following
                    # malloc_fixedsize_clear().
                    size_of_int = raw_malloc_usage(
                        llmemory.sizeof(lltype.Signed))
                    llarena.arena_reset(adr + size_of_int,
                                        object_size - size_of_int, 2)
                #
                elif mark == marked:
                    # the location contains really an object, which is marked.
                    # check the typeid to see if it's a weakref.  XXX could
                    # be faster
                    tid = hdr.tid
                    type_id = llop.extract_high_ushort(llgroup.HALFWORD, tid)
                    wroffset = self.weakpointer_offset(type_id)
                    if wroffset >= 0:
                        size_gc_header = self.gcheaderbuilder.size_gc_header
                        obj = adr + size_gc_header
                        pointing_to = (obj + wroffset).address[0]
                        if pointing_to != llmemory.NULL:
                            pt_adr = pointing_to - size_gc_header
                            pt_hdr = llmemory.cast_adr_to_ptr(pt_adr,
                                                              self.HDRPTR)
                            if (pt_hdr.tid & 0xFF) == nonmarked:
                                # this weakref points to an object that is still
                                # not marked, so clear it
                                (obj + wroffset).address[0] = llmemory.NULL
                #
                i -= object_size
            #
            page = self.cast_int_to_hdrptr(page.tid)
        #
        self.collect_heads[n] = linked_list
        self.collect_tails[n] = first_loc_in_linked_list


# ____________________________________________________________
#
# Hack to write the 'mark' or the 'flags' bytes of an object header
# without overwriting the whole word.  Essential in the rare case where
# the other thread might be concurrently writing the other byte.

concurrent_setter_lock = ll_thread.allocate_lock()

def emulate_set_mark(p, v):
    "NOT_RPYTHON"
    assert v in (MARK_VALUE_1, MARK_VALUE_2, MARK_VALUE_STATIC)
    concurrent_setter_lock.acquire(True)
    p.tid = (p.tid &~ 0xFF) | v
    concurrent_setter_lock.release()

def emulate_set_flags(p, v):
    "NOT_RPYTHON"
    assert (v & ~0xFF00) == 0
    concurrent_setter_lock.acquire(True)
    p.tid = (p.tid &~ 0xFF00) | v
    concurrent_setter_lock.release()

if sys.byteorder == 'little':
    eci = ExternalCompilationInfo(
        post_include_bits = ["""
#define pypy_concurrentms_set_mark(p, v)   ((char*)p)[0] = v
#define pypy_concurrentms_set_flags(p, v)  ((char*)p)[1] = v
        """])
elif sys.byteorder == 'big':
    eci = ExternalCompilationInfo(
        post_include_bits = [r"""
#define pypy_concurrentms_set_mark(p, v)   ((char*)p)[sizeof(long)-1] = v
#define pypy_concurrentms_set_flags(p, v)  ((char*)p)[sizeof(long)-2] = v
        """])
else:
    raise NotImplementedError(sys.byteorder)

_set_mark = rffi.llexternal("pypy_concurrentms_set_mark",
                           [MostlyConcurrentMarkSweepGC.HDRPTR, lltype.Signed],
                           lltype.Void, compilation_info=eci, _nowrapper=True,
                           _callable=emulate_set_mark)
_set_flags = rffi.llexternal("pypy_concurrentms_set_flags",
                           [MostlyConcurrentMarkSweepGC.HDRPTR, lltype.Signed],
                           lltype.Void, compilation_info=eci, _nowrapper=True,
                           _callable=emulate_set_flags)
