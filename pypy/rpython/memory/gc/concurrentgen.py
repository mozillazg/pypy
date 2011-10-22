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
from pypy.rpython.memory import gctypelayout
from pypy.module.thread import ll_thread

#
# A "3/4th concurrent" generational mark&sweep GC.
#
# This uses a separate thread to run the minor collections in parallel,
# as well as half of the major collections (the sweep phase).  The mark
# phase is not parallelized.  See concurrentgen.txt for some details.
#
# Based on observations that the timing of collections with "minimark"
# (on translate.py) is: about 15% of the time in minor collections
# (including 2% in walk_roots), and about 7% in major collections (with
# probably 3-4% in the marking phase).  So out of a total of 22% this
# should parallelize 16-17%, i.e. 3/4th.
#
# This is an entirely non-moving collector, with a generational write
# barrier adapted to the concurrent marking done by the collector thread.
#

WORD = LONG_BIT // 8
WORD_POWER_2 = {32: 2, 64: 3}[LONG_BIT]
assert 1 << WORD_POWER_2 == WORD
MAXIMUM_SIZE = sys.maxint - (3*WORD-1)


# Objects start with an integer 'tid', which is decomposed as follows.
# Lowest byte: one of the following values (which are all odd, so
# let us know if the 'tid' is valid or is just a word-aligned address):
MARK_BYTE_1       = 0x6D    # 'm', 109
MARK_BYTE_2       = 0x4B    # 'K', 75
MARK_BYTE_OLD     = 0x23    # '#', 35
MARK_BYTE_STATIC  = 0x53    # 'S', 83
# Next lower byte: a combination of flags.
FL_WITHHASH       = 0x0100
FL_EXTRA          = 0x0200
# And the high half of the word contains the numeric typeid.


class ConcurrentGenGC(GCBase):
    _alloc_flavor_ = "raw"
    inline_simple_malloc = True
    inline_simple_malloc_varsize = True
    needs_deletion_barrier = True
    needs_weakref_read_barrier = True
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
        self.addressstack_lock_object = SyncLock()
        kwds['lock'] = self.addressstack_lock_object
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
        self.flagged_objects = self.AddressStack()
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
            array[i] = self.NULL
            i += 1

    def _initialize(self):
        self.free_pages = self.NULL
        #
        # Clear the lists
        self._clear_list(self.nonfree_pages)
        self._clear_list(self.collect_pages)
        self._clear_list(self.free_lists)
        self._clear_list(self.collect_heads)
        self._clear_list(self.collect_tails)
        #
        self.finalizer_pages = self.NULL
        self.collect_finalizer_pages = self.NULL
        self.collect_finalizer_tails = self.NULL
        self.collect_run_finalizers_head = self.NULL
        self.collect_run_finalizers_tail = self.NULL
        self.objects_with_finalizers_to_run = self.NULL
        #
        self.weakref_pages = self.NULL
        self.collect_weakref_pages = self.NULL
        self.collect_weakref_tails = self.NULL
        #
        # See concurrentgen.txt for more information about these fields.
        self.current_young_marker = MARK_BYTE_1
        self.current_aging_marker = MARK_BYTE_2
        #
        # When the mutator thread wants to trigger the next collection,
        # it scans its own stack roots and prepares everything, then
        # sets 'collection_running' to 1, and releases
        # 'ready_to_start_lock'.  This triggers the collector thread,
        # which re-acquires 'ready_to_start_lock' and does its job.
        # When done it releases 'finished_lock'.  The mutator thread is
        # responsible for resetting 'collection_running' to 0.
        #
        # The collector thread's state can be found (with careful locking)
        # by inspecting the same variable from the mutator thread:
        #   * collection_running == 1: Marking.  [Deletion barrier active.]
        #   * collection_running == 2: Clearing weakrefs.
        #   * collection_running == 3: Marking from unreachable finalizers.
        #   * collection_running == 4: Sweeping.
        #   * collection_running == -1: Done.
        # The mutex_lock is acquired to go from 1 to 2, and from 2 to 3.
        self.collection_running = 0
        #self.ready_to_start_lock = ...built in setup()
        #self.finished_lock = ...built in setup()
        #
        #self.mutex_lock = ...built in setup()
        self.gray_objects.clear()
        self.extra_objects_to_mark.clear()
        self.flagged_objects.clear()
        self.prebuilt_root_objects.clear()

    def setup(self):
        "Start the concurrent collector thread."
        # don't call GCBase.setup(self), because we don't need
        # 'run_finalizers' as a deque
        self.finalizer_lock_count = 0
        #
        self.main_thread_ident = ll_thread.get_ident()
        self.ready_to_start_lock = ll_thread.allocate_ll_lock()
        self.finished_lock = ll_thread.allocate_ll_lock()
        self.mutex_lock = ll_thread.allocate_ll_lock()
        self.addressstack_lock_object.setup()
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
        hdr.tid = self.combine(typeid, MARK_BYTE_STATIC, 0)

    def malloc_fixedsize_clear(self, typeid, size,
                               needs_finalizer=False, contains_weakptr=False):
        # contains_weakptr: detected during collection
        #
        # Case of finalizers (test constant-folded)
        if needs_finalizer:
            ll_assert(not contains_weakptr,
                     "'needs_finalizer' and 'contains_weakptr' both specified")
            return self._malloc_with_finalizer(typeid, size)
        #
        # Case of weakreferences (test constant-folded)
        if contains_weakptr:
            return self._malloc_weakref(typeid, size)
        #
        # Regular case
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
                self.free_lists[n] = list_next(result)
                obj = self.grow_reservation(result, totalsize)
                hdr = self.header(obj)
                hdr.tid = self.combine(typeid, self.current_young_marker, 0)
                #debug_print("malloc_fixedsize_clear", obj)
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
                self.free_lists[n] = list_next(result)
                obj = self.grow_reservation(result, totalsize)
                hdr = self.header(obj)
                hdr.tid = self.combine(typeid, self.current_young_marker, 0)
                (obj + offset_to_length).signed[0] = length
                #debug_print("malloc_varsize_clear", obj)
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
        #
        if rawtotalsize <= self.small_request_threshold:
            #
            # Case 1: unless trigger_next_collection() happened to get us
            # more locations in free_lists[n], we have run out of them
            ll_assert(rawtotalsize & (WORD - 1) == 0,
                      "malloc_slowpath: non-rounded size")
            n = rawtotalsize >> WORD_POWER_2
            head = self.free_lists[n]
            if head:
                self.free_lists[n] = list_next(head)
                obj = self.grow_reservation(head, totalsize)
                hdr = self.header(obj)
                hdr.tid = self.combine(typeid, self.current_young_marker, 0)
                return llmemory.cast_adr_to_ptr(obj, llmemory.GCREF)
            #
            # We really have run out of the free list corresponding to
            # the size.  Grab the next free page.
            newpage = self.free_pages
            if newpage == self.NULL:
                self.allocate_next_arena()
                newpage = self.free_pages
            self.free_pages = list_next(newpage)
            #
            # Put the free page in the list 'nonfree_pages[n]'.  This is
            # a linked list chained through the first word of each page.
            set_next(newpage, self.nonfree_pages[n])
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
                set_next(p, head)
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
            return self._malloc_result(typeid, totalsize, result)
        else:
            # Case 2: the object is too large, so allocate it directly
            # with the system malloc().
            return self._malloc_large_object(typeid, size, 0)
        #
    _malloc_slowpath._dont_inline_ = True

    def _malloc_result(self, typeid, totalsize, result):
        llarena.arena_reserve(result, totalsize)
        hdr = llmemory.cast_adr_to_ptr(result, self.HDRPTR)
        hdr.tid = self.combine(typeid, self.current_young_marker, 0)
        obj = result + self.gcheaderbuilder.size_gc_header
        #debug_print("malloc_slowpath", obj)
        return llmemory.cast_adr_to_ptr(obj, llmemory.GCREF)

    def _malloc_large_object(self, typeid, size, linked_list):
        # xxx on 32-bit, we'll prefer 64-bit alignment of the object by
        # always allocating an 8-bytes header
        totalsize = self.gcheaderbuilder.size_gc_header + size
        rawtotalsize = raw_malloc_usage(totalsize)
        rawtotalsize += 8
        block = llarena.arena_malloc(rawtotalsize, 2)
        if not block:
            raise MemoryError
        llarena.arena_reserve(block, self.HDRSIZE)
        blockhdr = llmemory.cast_adr_to_ptr(block, self.HDRPTR)
        if linked_list == 0:
            set_next(blockhdr, self.nonfree_pages[0])
            self.nonfree_pages[0] = blockhdr
        elif linked_list == 1:
            set_next(blockhdr, self.finalizer_pages)
            self.finalizer_pages = blockhdr
        elif linked_list == 2:
            set_next(blockhdr, self.weakref_pages)
            self.weakref_pages = blockhdr
        else:
            ll_assert(0, "bad linked_list")
        return self._malloc_result(typeid, totalsize, block + 8)
    _malloc_large_object._annspecialcase_ = 'specialize:arg(3)'
    _malloc_large_object._dont_inline_ = True

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

    def _malloc_with_finalizer(self, typeid, size):
        return self._malloc_large_object(typeid, size, 1)

    def _malloc_weakref(self, typeid, size):
        return self._malloc_large_object(typeid, size, 2)

    # ----------
    # Other functions in the GC API

    #def set_max_heap_size(self, size):
    #    XXX

    #def raw_malloc_memory_pressure(self, sizehint):
    #    XXX

    #def shrink_array(self, obj, smallerlength):
    #    no real point in supporting this, but if you think it's a good
    #    idea, remember that changing the array length at run-time needs
    #    extra care for the collector thread

    def enumerate_all_roots(self, callback, arg):
        self.flagged_objects.foreach(callback, arg)
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
        llarena.arena_reserve(adr, totalsize)
        return adr + self.gcheaderbuilder.size_gc_header
    grow_reservation._always_inline_ = True

    def deletion_barrier(self, addr_struct):
        # XXX check the assembler
        mark = self.header(addr_struct).tid & 0xFF
        if mark != self.current_young_marker:
            self.force_scan(addr_struct)
        #else:
        #    debug_print("deletion_barrier (off)", addr_struct)

    def assume_young_pointers(self, addr_struct):
        pass # XXX

    def _init_writebarrier_logic(self):
        #
        def force_scan(obj):
            #debug_print("deletion_barrier  ON  ", obj)
            cym = self.current_young_marker
            mark = self.get_mark(obj)
            #
            if mark == MARK_BYTE_OLD:
                #
                self.set_mark(obj, cym)
                #
            elif mark == MARK_BYTE_STATIC:
                # This is the first write into a prebuilt GC object.
                # Record it in 'prebuilt_root_objects'.
                self.set_mark(obj, cym)
                self.prebuilt_root_objects.append(obj)
                #
            else:
                #
                # Only acquire the mutex_lock if necessary
                self.acquire(self.mutex_lock)
                #
                # Reload the possibly changed marker from the object header,
                # and set it to 'cym'
                mark = self.get_mark(obj)
                self.set_mark(obj, cym)
                #
                if mark == self.current_aging_marker:
                    #
                    # it is only possible to reach this point if there is
                    # a collection running in collector_mark(), before it
                    # does mutex_lock itself.  Check this:
                    ll_assert(self.collection_running == 1,
                              "write barrier: wrong call?")
                    #
                    # It's fine to set the mark before tracing, because
                    # we are anyway in a 'mutex_lock' critical section.
                    # The collector thread will not exit from the phase
                    # 'collection_running == 1' here.
                    self.trace(obj, self._barrier_add_extra, None)
                    #
                    # Still at 1:
                    ll_assert(self.collection_running == 1,
                              "write barrier: oups!?")
                    #
                else:
                    # MARK_BYTE_OLD is possible here: the collector thread
                    # sets it in parallel to objects.  In that case it has
                    # been handled already.
                    ll_assert(mark == MARK_BYTE_OLD,
                              "write barrier: bogus object mark")
                #
                self.release(self.mutex_lock)
            #
            # In all cases, the object is now flagged
            self.flagged_objects.append(obj)
        #
        force_scan._dont_inline_ = True
        self.force_scan = force_scan

    def _barrier_add_extra(self, root, ignored):
        obj = root.address[0]
        self.get_mark(obj)
        self.extra_objects_to_mark.append(obj)


    def wait_for_the_end_of_collection(self):
        """In the mutator thread: wait for the minor collection currently
        running (if any) to finish."""
        if self.collection_running != 0:
            debug_start("gc-stop")
            #
            self.acquire(self.finished_lock)
            self.collection_running = 0
            #debug_print("collection_running = 0")
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
                self.free_lists[n] = self.join_lists(self.free_lists[n],
                                                     self.collect_heads[n],
                                                     self.collect_tails[n])
                n += 1
            #
            # Do the same with 'collect_heads[0]/collect_tails[0]'.
            self.nonfree_pages[0] = self.join_lists(self.nonfree_pages[0],
                                                    self.collect_heads[0],
                                                    self.collect_tails[0])
            #
            # Do the same with 'collect_weakref_pages/tails'
            self.weakref_pages = self.join_lists(self.weakref_pages,
                                                 self.collect_weakref_pages,
                                                 self.collect_weakref_tails)
            #
            # Do the same with 'collect_finalizer_pages/tails'
            self.finalizer_pages = self.join_lists(self.finalizer_pages,
                                                  self.collect_finalizer_pages,
                                                  self.collect_finalizer_tails)
            #
            # Do the same with 'collect_run_finalizers_head/tail'
            self.objects_with_finalizers_to_run = self.join_lists(
                self.objects_with_finalizers_to_run,
                self.collect_run_finalizers_head,
                self.collect_run_finalizers_tail)
            #
            if self.DEBUG:
                self.debug_check_lists()
            #
            debug_stop("gc-stop")
            #
            # We must *not* run execute_finalizers_ll() here, because it
            # can start the next collection, and then this function returns
            # with a collection in progress, which it should not.  Be careful
            # to call execute_finalizers_ll() in the caller somewhere.
            ll_assert(self.collection_running == 0,
                      "collector thread not paused?")

    def join_lists(self, list1, list2head, list2tail):
        if list2tail == self.NULL:
            ll_assert(list2head == self.NULL, "join_lists/1")
            return list1
        else:
            ll_assert(list2head != self.NULL, "join_lists/2")
            set_next(list2tail, list1)
            return list2head


    def execute_finalizers_ll(self):
        self.finalizer_lock_count += 1
        try:
            while self.objects_with_finalizers_to_run != self.NULL:
                if self.finalizer_lock_count > 1:
                    # the outer invocation of execute_finalizers() will do it
                    break
                #
                x = llmemory.cast_ptr_to_adr(
                        self.objects_with_finalizers_to_run)
                x = llarena.getfakearenaaddress(x) + 8
                obj = x + self.gcheaderbuilder.size_gc_header
                self.objects_with_finalizers_to_run = list_next(
                    self.objects_with_finalizers_to_run)
                #
                finalizer = self.getfinalizer(self.get_type_id(obj))
                finalizer(obj, llmemory.NULL)
        finally:
            self.finalizer_lock_count -= 1


    def collect(self, gen=3):
        """
        gen=0: Trigger a minor collection if none is running.  Never blocks.
        
        gen=1: The same, but if a minor collection is running, wait for
        it to finish before triggering the next one.  Guarantees that
        young objects not reachable when collect() is called will soon
        be freed.

        gen=2: The same, but wait for the triggered collection to
        finish.  Guarantees that young objects not reachable when
        collect() is called will be freed by the time collect() returns.

        gen>=3: Do a (synchronous) major collection.
        """
        if gen >= 1 or self.collection_running <= 0:
            self.trigger_next_collection()
            if gen >= 2:
                self.wait_for_the_end_of_collection()
                if gen >= 3:
                    self.major_collection()
        self.execute_finalizers_ll()

    def trigger_next_collection(self):
        """In the mutator thread: triggers the next minor collection."""
        #
        # In case the previous collection is not over yet, wait for it
        self.wait_for_the_end_of_collection()
        #
        debug_start("gc-start")
        #
        # Scan the stack roots and the refs in non-GC objects
        self.root_walker.walk_roots(
            ConcurrentGenGC._add_stack_root,  # stack roots
            ConcurrentGenGC._add_stack_root,  # in prebuilt non-gc
            None)                         # static in prebuilt gc
        #
        # Add the prebuilt root objects that have been written to
        self.flagged_objects.foreach(self._add_prebuilt_root, None)
        #
        # Add the objects still waiting in 'objects_with_finalizers_to_run'
        p = self.objects_with_finalizers_to_run
        while p != self.NULL:
            x = llmemory.cast_ptr_to_adr(p)
            x = llarena.getfakearenaaddress(x) + 8
            obj = x + self.gcheaderbuilder.size_gc_header
            #debug_print("_objects_with_finalizers_to_run", obj)
            self.get_mark(obj)
            self.gray_objects.append(obj)
            p = list_next(p)
        #
        # Exchange the meanings of 'cym' and 'cam'
        other = self.current_young_marker
        self.current_young_marker = self.current_aging_marker
        self.current_aging_marker = other
        #
        # Copy a few 'mutator' fields to 'collector' fields:
        # 'collect_pages' make linked lists of all nonfree pages at the
        # start of the collection (unlike the 'nonfree_pages' lists, which
        # the mutator will continue to grow).
        n = 0
        while n < self.pagelists_length:
            self.collect_pages[n] = self.nonfree_pages[n]
            n += 1
        self.collect_weakref_pages = self.weakref_pages
        self.collect_finalizer_pages = self.finalizer_pages
        #
        # Clear the following lists.  When the collector thread finishes,
        # it will give back (in collect_{pages,tails}[0] and
        # collect_finalizer_{pages,tails}) all the original items that survive.
        self.nonfree_pages[0] = self.NULL
        self.weakref_pages = self.NULL
        self.finalizer_pages = self.NULL
        #
        # Start the collector thread
        self.collection_running = 1
        #debug_print("collection_running = 1")
        self.release(self.ready_to_start_lock)
        #
        debug_stop("gc-start")
        #
        self.execute_finalizers_ll()

    def _add_stack_root(self, root):
        obj = root.address[0]
        #debug_print("_add_stack_root", obj)
        self.get_mark(obj)
        self.gray_objects.append(obj)

    def _add_prebuilt_root(self, obj, ignored):
        #debug_print("_add_prebuilt_root", obj)
        self.get_mark(obj)
        self.gray_objects.append(obj)

    def debug_check_lists(self):
        # just check that they are correct, non-infinite linked lists
        self.debug_check_list(self.nonfree_pages[0])
        n = 1
        while n < self.pagelists_length:
            self.debug_check_list(self.free_lists[n])
            n += 1
        self.debug_check_list(self.weakref_pages)
        self.debug_check_list(self.finalizer_pages)
        self.debug_check_list(self.objects_with_finalizers_to_run)

    def debug_check_list(self, page):
        try:
            previous_page = self.NULL
            count = 0
            while page != self.NULL:
                # prevent constant-folding, and detects loops of length 1
                ll_assert(page != previous_page, "loop!")
                previous_page = page
                page = list_next(page)
                count += 1
            return count
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
            #import pdb; pdb.post_mortem(sys.exc_info()[2])
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
            # Mark                                # collection_running == 1
            self.collector_mark()
            #                                     # collection_running == 2
            self.deal_with_weakrefs()
            #                                     # collection_running == 3
            self.deal_with_objects_with_finalizers()
            # Sweep                               # collection_running == 4
            self.collector_sweep()
            # Done!                               # collection_running == -1
            self.release(self.finished_lock)


    def set_mark(self, obj, newmark):
        _set_mark(self.header(obj), newmark)

    def get_mark(self, obj):
        mark = self.header(obj).tid & 0xFF
        ll_assert(mark == MARK_BYTE_1 or
                  mark == MARK_BYTE_2 or
                  mark == MARK_BYTE_OLD or
                  mark == MARK_BYTE_STATIC, "bad mark byte in object")
        return mark

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
            #debug_print("...collector thread has mutex_lock")
            while self.extra_objects_to_mark.non_empty():
                obj = self.extra_objects_to_mark.pop()
                self.get_mark(obj)
                self.gray_objects.append(obj)
            #
            # If 'gray_objects' is empty, we are done: there should be
            # no possible case in which more objects are being added to
            # 'extra_objects_to_mark' concurrently, because 'gray_objects'
            # and 'extra_objects_to_mark' were already empty before we
            # acquired the 'mutex_lock', so all reachable objects have
            # been marked.
            if not self.gray_objects.non_empty():
                break
            #
            # Else release mutex_lock and try again.
            self.release(self.mutex_lock)
        #
        self.collection_running = 2
        #debug_print("collection_running = 2")
        self.release(self.mutex_lock)

    def _collect_mark(self):
        cam = self.current_aging_marker
        while self.gray_objects.non_empty():
            obj = self.gray_objects.pop()
            if self.get_mark(obj) == cam:
                #
                # Scan the content of 'obj'.  We use a snapshot-at-the-
                # beginning order, meaning that we want to scan the state
                # of the object as it was at the beginning of the current
                # collection --- and not the current state, which might have
                # been modified.  That's why we have a deletion barrier:
                # when the mutator thread is about to change an object that
                # is not yet marked, it will itself do the scanning of just
                # this object, and mark the object.  But this function is not
                # synchronized, which means that in some rare cases it's
                # possible that the object is scanned a second time here
                # (harmlessly).
                #
                # The order of the next two lines is essential!  *First*
                # scan the object, adding all objects found to gray_objects;
                # and *only then* set the mark.  This is essential, because
                # otherwise, we might set the mark, then the main thread
                # thinks a force_scan() is not necessary and modifies the
                # content of 'obj', and then here in the collector thread
                # we scan a modified content --- and the original content
                # is never scanned.
                #
                self.trace(obj, self._collect_add_pending, None)
                self.set_mark(obj, MARK_BYTE_OLD)
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
        obj = root.address[0]
        self.get_mark(obj)
        self.gray_objects.append(obj)

    def collector_sweep(self):
        self._collect_sweep_large_objects()
        #
        n = 1
        while n < self.pagelists_length:
            self._collect_sweep_pages(n)
            n += 1
        #
        self.collection_running = -1
        #debug_print("collection_running = -1")

    def _collect_sweep_large_objects(self):
        block = self.collect_pages[0]
        cam = self.current_aging_marker
        linked_list = self.NULL
        first_block_in_linked_list = self.NULL
        while block != self.NULL:
            nextblock = list_next(block)
            blockadr = llmemory.cast_ptr_to_adr(block)
            blockadr = llarena.getfakearenaaddress(blockadr)
            hdr = llmemory.cast_adr_to_ptr(blockadr + 8, self.HDRPTR)
            mark = hdr.tid & 0xFF
            if mark == cam:
                # the object is still not marked.  Free it.
                llarena.arena_free(blockadr)
                #
            else:
                # the object was marked: relink it
                ll_assert(mark == MARK_BYTE_OLD,
                          "bad mark in large object")
                set_next(block, linked_list)
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
        size_gc_header = self.gcheaderbuilder.size_gc_header
        page = self.collect_pages[n]
        object_size = n << WORD_POWER_2
        linked_list = self.NULL
        first_loc_in_linked_list = self.NULL
        cam = self.current_aging_marker
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
                if mark == cam:
                    # the location contains really an object (and is not just
                    # part of a linked list of free locations), and moreover
                    # the object is still not marked.  Free it by inserting
                    # it into the linked list.
                    #debug_print("sweeps", adr + size_gc_header)
                    llarena.arena_reset(adr, object_size, 0)
                    llarena.arena_reserve(adr, self.HDRSIZE)
                    hdr = llmemory.cast_adr_to_ptr(adr, self.HDRPTR)
                    set_next(hdr, linked_list)
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
                i -= object_size
            #
            page = list_next(page)
        #
        self.collect_heads[n] = linked_list
        self.collect_tails[n] = first_loc_in_linked_list


    # ----------
    # Major collections

    def major_collection(self):
        pass #XXX


    # ----------
    # Weakrefs

    def weakref_deref(self, wrobj):
        # Weakrefs need some care.  This code acts as a read barrier.
        # The only way I found is to acquire the mutex_lock to prevent
        # the collection thread from going from collection_running==1
        # to collection_running==2, or from collection_running==2 to
        # collection_running==3.
        #
        self.acquire(self.mutex_lock)
        #
        targetobj = gctypelayout.ll_weakref_deref(wrobj)
        if targetobj != llmemory.NULL:
            #
            if self.collection_running == 1:
                # If we are in the phase collection_running==1, we don't
                # know if the object will be scanned a bit later or
                # not; so we have to assume that it survives, and
                # force it to be scanned.
                self.get_mark(targetobj)
                self.extra_objects_to_mark.append(targetobj)
                #
            elif self.collection_running == 2:
                # In the phase collection_running==2, if the object is
                # not marked it's too late; we have to detect that case
                # and return NULL instead here, as if the corresponding
                # collector phase was already finished (deal_with_weakrefs).
                # Otherwise we would be returning an object that is about to
                # be swept away.
                if not self.is_marked_or_static(targetobj, self.current_mark):
                    targetobj = llmemory.NULL
                #
            else:
                # In other phases we are fine.
                pass
        #
        self.release(self.mutex_lock)
        #
        return targetobj

    def deal_with_weakrefs(self):
        self.collection_running = 3; return
        # ^XXX^
        size_gc_header = self.gcheaderbuilder.size_gc_header
        current_mark = self.current_mark
        weakref_page = self.collect_weakref_pages
        self.collect_weakref_pages = self.NULL
        self.collect_weakref_tails = self.NULL
        while weakref_page != self.NULL:
            next_page = list_next(weakref_page)
            #
            # If the weakref points to a dead object, make it point to NULL.
            x = llmemory.cast_ptr_to_adr(weakref_page)
            x = llarena.getfakearenaaddress(x) + 8
            hdr = llmemory.cast_adr_to_ptr(x, self.HDRPTR)
            type_id = llop.extract_high_ushort(llgroup.HALFWORD, hdr.tid)
            offset = self.weakpointer_offset(type_id)
            ll_assert(offset >= 0, "bad weakref")
            obj = x + size_gc_header
            pointing_to = (obj + offset).address[0]
            ll_assert(pointing_to != llmemory.NULL, "null weakref?")
            if not self.is_marked_or_static(pointing_to, current_mark):
                # 'pointing_to' dies: relink to self.collect_pages[0]
                (obj + offset).address[0] = llmemory.NULL
                set_next(weakref_page, self.collect_pages[0])
                self.collect_pages[0] = weakref_page
            else:
                # the weakref stays alive
                set_next(weakref_page, self.collect_weakref_pages)
                self.collect_weakref_pages = weakref_page
                if self.collect_weakref_tails == self.NULL:
                    self.collect_weakref_tails = weakref_page
            #
            weakref_page = next_page
        #
        self.acquire(self.mutex_lock)
        self.collection_running = 3
        #debug_print("collection_running = 3")
        self.release(self.mutex_lock)


    # ----------
    # Finalizers

    def deal_with_objects_with_finalizers(self):
        self.collection_running = 4; return
        # ^XXX^
        
        # XXX needs to be done correctly; for now we'll call finalizers
        # in random order
        size_gc_header = self.gcheaderbuilder.size_gc_header
        marked = self.current_mark
        finalizer_page = self.collect_finalizer_pages
        self.collect_run_finalizers_head = self.NULL
        self.collect_run_finalizers_tail = self.NULL
        self.collect_finalizer_pages = self.NULL
        self.collect_finalizer_tails = self.NULL
        while finalizer_page != self.NULL:
            next_page = list_next(finalizer_page)
            #
            x = llmemory.cast_ptr_to_adr(finalizer_page)
            x = llarena.getfakearenaaddress(x) + 8
            hdr = llmemory.cast_adr_to_ptr(x, self.HDRPTR)
            if (hdr.tid & 0xFF) != marked:
                # non-marked: add to collect_run_finalizers,
                # and mark the object and its dependencies
                set_next(finalizer_page, self.collect_run_finalizers_head)
                self.collect_run_finalizers_head = finalizer_page
                if self.collect_run_finalizers_tail == self.NULL:
                    self.collect_run_finalizers_tail = finalizer_page
                obj = x + size_gc_header
                self.get_mark(obj)
                self.gray_objects.append(obj)
            else:
                # marked: relink into the collect_finalizer_pages list
                set_next(finalizer_page, self.collect_finalizer_pages)
                self.collect_finalizer_pages = finalizer_page
                if self.collect_finalizer_tails == self.NULL:
                    self.collect_finalizer_tails = finalizer_page
            #
            finalizer_page = next_page
        #
        self._collect_mark()
        #
        ll_assert(not self.extra_objects_to_mark.non_empty(),
                  "should not see objects only reachable from finalizers "
                  "before we run them")
        #
        self.collection_running = 4
        #debug_print("collection_running = 4")


# ____________________________________________________________
#
# Support for linked lists (used here because AddressStack is not thread-safe)

def list_next(hdr):
    return llmemory.cast_adr_to_ptr(llmemory.cast_int_to_adr(hdr.tid),
                                    ConcurrentGenGC.HDRPTR)

def set_next(hdr, nexthdr):
    hdr.tid = llmemory.cast_adr_to_int(llmemory.cast_ptr_to_adr(nexthdr),
                                       "symbolic")


# ____________________________________________________________
#
# Hack to write the 'mark' or the 'flags' bytes of an object header
# without overwriting the whole word.  Essential in the rare case where
# the other thread might be concurrently writing the other byte.

concurrent_setter_lock = ll_thread.allocate_lock()

def emulate_set_mark(p, v):
    "NOT_RPYTHON"
    assert v in (MARK_BYTE_1, MARK_BYTE_2, MARK_BYTE_OLD, MARK_BYTE_STATIC)
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
                           [ConcurrentGenGC.HDRPTR, lltype.Signed],
                           lltype.Void, compilation_info=eci, _nowrapper=True,
                           _callable=emulate_set_mark)
_set_flags = rffi.llexternal("pypy_concurrentms_set_flags",
                           [ConcurrentGenGC.HDRPTR, lltype.Signed],
                           lltype.Void, compilation_info=eci, _nowrapper=True,
                           _callable=emulate_set_flags)

# ____________________________________________________________
#
# A lock to synchronize access to AddressStack's free pages

class SyncLock:
    _alloc_flavor_ = "raw"
    _lock = lltype.nullptr(ll_thread.TLOCKP.TO)
    def setup(self):
        self._lock = ll_thread.allocate_ll_lock()
    def acquire(self):
        if self._lock:
            ll_thread.c_thread_acquirelock(self._lock, 1)
    def release(self):
        if self._lock:
            ll_thread.c_thread_releaselock(self._lock)
