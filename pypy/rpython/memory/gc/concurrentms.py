import time, sys
from pypy.rpython.lltypesystem import lltype, llmemory, llarena, llgroup, rffi
from pypy.rpython.lltypesystem.llmemory import raw_malloc_usage
from pypy.rlib.objectmodel import we_are_translated, running_on_llinterp
from pypy.rlib.debug import ll_assert
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
NULL = llmemory.NULL
WORD_POWER_2 = {32: 2, 64: 3}[LONG_BIT]
assert 1 << WORD_POWER_2 == WORD
size_of_addr = llmemory.sizeof(llmemory.Address)

# XXX assumes little-endian machines for now: the byte at offset 0 in
# the object is either a mark byte (equal to an odd value), or if the
# location is free, it is the low byte of a pointer to the next free
# location (and then it is an even value, by pointer alignment).
assert sys.byteorder == 'little'


MARK_VALUE_1      = 'M'     #  77, 0x4D
MARK_VALUE_2      = 'k'     # 107, 0x6B
MARK_VALUE_STATIC = 'S'     #  83, 0x53
GCFLAG_WITH_HASH  = 0x01


class MostlyConcurrentMarkSweepGC(GCBase):
    _alloc_flavor_ = "raw"
    inline_simple_malloc = True
    inline_simple_malloc_varsize = True
    needs_write_barrier = True
    prebuilt_gc_objects_are_static_roots = False
    malloc_zero_filled = True
    #gcflag_extra = GCFLAG_FINALIZATION_ORDERING

    HDR = lltype.Struct('header', ('mark', lltype.Char),  # MARK_VALUE_{1,2}
                                  ('flags', lltype.Char),
                                  ('typeid16', llgroup.HALFWORD))
    typeid_is_in_field = 'typeid16'
    withhash_flag_is_in_field = 'flags', GCFLAG_WITH_HASH

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
        self.pagelists_length = small_request_threshold // WORD + 1
        #
        # The following are arrays of 36 linked lists: the linked lists
        # at indices 1 to 35 correspond to pages that store objects of
        # size  1 * WORD  to  35 * WORD,  and the linked list at index 0
        # is a list of all larger objects.
        def list_of_addresses_per_small_size():
            return lltype.malloc(rffi.CArray(llmemory.Address),
                                 self.pagelists_length, flavor='raw',
                                 zero=True, immortal=True)
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
        self.prebuilt_root_objects = self.AddressStack()
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
        if self._teardown_now:
            return
        self.wait_for_the_end_of_collection()
        #
        # start the next collection, but with "stop" in _teardown_now,
        # which should shut down the collector thread
        self._teardown_now.append("stop")
        self.ready_to_start_lock.release()
        self.acquire(self.finished_lock)
        del self.ready_to_start_lock, self.finished_lock

    def get_type_id(self, obj):
        return self.header(obj).typeid16

    def init_gc_object_immortal(self, addr, typeid, flags=0):
        # 'flags' is ignored here
        hdr = llmemory.cast_adr_to_ptr(addr, lltype.Ptr(self.HDR))
        hdr.typeid16 = typeid
        hdr.mark = MARK_VALUE_STATIC
        hdr.flags = '\x00'

    def malloc_fixedsize_clear(self, typeid, size,
                               needs_finalizer=False, contains_weakptr=False):
        assert not needs_finalizer  # XXX
        assert not contains_weakptr # XXX
        size_gc_header = self.gcheaderbuilder.size_gc_header
        totalsize = size_gc_header + size
        rawtotalsize = raw_malloc_usage(totalsize)
        if rawtotalsize <= self.small_request_threshold:
            ll_assert(rawtotalsize & (WORD - 1) == 0,
                      "fixedsize not properly rounded")
            n = rawtotalsize >> WORD_POWER_2
            result = self.free_lists[n]
            if result != llmemory.NULL:
                self.free_lists[n] = result.address[0]
                #
                llarena.arena_reset(result, size_of_addr, 0)
                llarena.arena_reserve(result, totalsize)
                hdr = llmemory.cast_adr_to_ptr(result, lltype.Ptr(self.HDR))
                hdr.typeid16 = typeid
                hdr.mark = self.current_mark
                hdr.flags = '\x00'
                #
                obj = result + size_gc_header
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
            if result != llmemory.NULL:
                self.free_lists[n] = result.address[0]
                #
                llarena.arena_reset(result, size_of_addr, 0)
                llarena.arena_reserve(result, totalsize)
                hdr = llmemory.cast_adr_to_ptr(result, lltype.Ptr(self.HDR))
                hdr.typeid16 = typeid
                hdr.mark = self.current_mark
                hdr.flags = '\x00'
                #
                obj = result + size_gc_header
                (obj + offset_to_length).signed[0] = length
                return llmemory.cast_adr_to_ptr(obj, llmemory.GCREF)
        #
        # If the total size of the object would be larger than
        # 'small_request_threshold', or if the free_list is empty,
        # then allocate it externally.  We also go there if 'length'
        # is actually negative.
        return self._malloc_varsize_slowpath(typeid, length)

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
            #
            # Put the free page in the list 'nonfree_pages[n]'.  This is
            # a linked list chained through the first word of each page.
            n = (rawtotalsize + WORD - 1) >> WORD_POWER_2
            newpage.address[0] = self.nonfree_pages[n]
            self.nonfree_pages[n] = newpage
            #
            # Initialize the free page to contain objects of the given
            # size.  This requires setting up all object locations in the
            # page, linking them in the free list.
            head = self.free_lists[n]
            ll_assert(not head, "_malloc_slowpath: unexpected free_lists[n]")
            i = self.page_size - rawtotalsize
            limit = rawtotalsize + raw_malloc_usage(size_of_addr)
            while i >= limit:
                llarena.arena_reserve(newpage + i, size_of_addr)
                (newpage + i).address[0] = head
                head = newpage + i
                i -= rawtotalsize
            self.free_lists[n] = head
            result = head - rawtotalsize
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
            # with the system malloc().  XXX on 32-bit, we should prefer
            # 64-bit alignment of the object
            try:
                rawtotalsize = ovfcheck(raw_malloc_usage(size_of_addr) +
                                        rawtotalsize)
            except OverflowError:
                raise MemoryError
            block = llarena.arena_malloc(rawtotalsize, 2)
            if not block:
                raise MemoryError
            llarena.arena_reserve(block, size_of_addr)
            block.address[0] = self.nonfree_pages[0]
            self.nonfree_pages[0] = block
            result = block + size_of_addr
        #
        llarena.arena_reserve(result, totalsize)
        hdr = llmemory.cast_adr_to_ptr(result, lltype.Ptr(self.HDR))
        hdr.typeid16 = typeid
        hdr.mark = self.current_mark
        hdr.flags = '\x00'
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
        result = self._malloc_slowpath(typeid, totalsize)
        #
        offset_to_length = self.varsize_offset_to_length(typeid)
        obj = llmemory.cast_ptr_to_adr(result)
        (obj + offset_to_length).signed[0] = length
        return result
    _malloc_varsize_slowpath._dont_inline_ = True

    def allocate_next_arena(self):
        # xxx for now, allocate one page at a time with the system malloc()
        page = llarena.arena_malloc(self.page_size, 2)     # zero-filled
        if not page:
            raise MemoryError
        llarena.arena_reserve(page, size_of_addr)
        page.address[0] = NULL
        self.free_pages = page


    def write_barrier(self, newvalue, addr_struct):
        mark = self.header(addr_struct).mark
        if mark != self.current_mark:
            self.force_scan(addr_struct)

    def _init_writebarrier_logic(self):
        #
        def force_scan(obj):
            self.mutex_lock.acquire(True)
            mark = self.header(obj).mark
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
            self.mutex_lock.release()
        #
        force_scan._dont_inline_ = True
        self.force_scan = force_scan

    def _barrier_add_extra(self, root, ignored):
        self.extra_objects_to_mark.append(root.address[0])


    def wait_for_the_end_of_collection(self):
        """In the mutator thread: wait for the collection currently
        running (if any) to finish."""
        if self.collection_running != 0:
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
                if self.collect_tails[n] != NULL:
                    self.collect_tails[n].address[0] = self.free_lists[n]
                    self.free_lists[n] = self.collect_heads[n]
                n += 1
            #
            # Do the same with 'collect_heads[0]/collect_tails[0]'.
            if self.collect_tails[0] != NULL:
                self.collect_tails[0].address[0] = self.nonfree_pages[0]
                self.nonfree_pages[0] = self.collect_heads[0]


    def collect(self, gen=0):
        """Trigger a complete collection, and wait for it to finish."""
        self.trigger_next_collection()
        self.wait_for_the_end_of_collection()

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
        #
        # Start the collector thread
        self.collection_running = 1
        self.ready_to_start_lock.release()

    def _add_stack_root(self, root):
        obj = root.address[0]
        self.gray_objects.append(obj)

    def _add_prebuilt_root(self, obj, ignored):
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
                self.collection_running = 2
                #
                # Sweep
                self.collector_sweep()
                self.finished_lock.release()
                #
        except Exception, e:
            print 'Crash!', e.__class__.__name__, e
            self._exc_info = sys.exc_info()

    def other_mark(self, mark):
        ll_assert(mark == MARK_VALUE_1 or mark == MARK_VALUE_2,
                  "bad mark value")
        return chr(ord(mark) ^ (ord(MARK_VALUE_1) ^ ord(MARK_VALUE_2)))

    def is_marked(self, obj, current_mark):
        mark = self.header(obj).mark
        ll_assert(mark in (MARK_VALUE_1, MARK_VALUE_2, MARK_VALUE_STATIC),
                  "bad mark byte in object")
        return mark == current_mark

    def set_mark(self, obj, current_mark):
        self.header(obj).mark = current_mark

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
        self._collect_sweep_large_objects()
        n = 1
        while n < self.pagelists_length:
            self._collect_sweep_pages(n)
            n += 1

    def _collect_sweep_large_objects(self):
        block = self.collect_pages[0]
        nonmarked = self.other_mark(self.current_mark)
        linked_list = NULL
        first_block_in_linked_list = NULL
        while block != llmemory.NULL:
            hdr = block + size_of_addr
            if maybe_read_mark_byte(hdr) == nonmarked:
                # the object is still not marked.  Free it.
                llarena.arena_free(block)
                #
            else:
                # the object was marked: relink it
                block.address[0] = linked_list
                linked_list = block
                if first_block_in_linked_list == NULL:
                    first_block_in_linked_list = block
        #
        self.collect_heads[0] = linked_list
        self.collect_tails[0] = first_block_in_linked_list

    def _collect_sweep_pages(self, n):
        # sweep all pages from the linked list starting at 'page',
        # containing objects of fixed size 'object_size'.
        page = self.collect_pages[n]
        object_size = n << WORD_POWER_2
        linked_list = NULL
        first_loc_in_linked_list = NULL
        nonmarked = self.other_mark(self.current_mark)
        while page != llmemory.NULL:
            i = self.page_size - object_size
            limit = raw_malloc_usage(size_of_addr)
            while i >= limit:
                hdr = page + i
                #
                if maybe_read_mark_byte(hdr) == nonmarked:
                    # the location contains really an object (and is not just
                    # part of a linked list of free locations), and moreover
                    # the object is still not marked.  Free it by inserting
                    # it into the linked list.
                    llarena.arena_reset(hdr, object_size, 0)
                    llarena.arena_reserve(hdr, size_of_addr)
                    hdr.address[0] = linked_list
                    linked_list = hdr
                    if first_loc_in_linked_list == NULL:
                        first_loc_in_linked_list = hdr
                    # XXX detect when the whole page is freed again
                    #
                    # Clear the data, in prevision for the following
                    # malloc_fixedsize_clear().
                    llarena.arena_reset(hdr + size_of_addr,
                        object_size - raw_malloc_usage(size_of_addr), 2)
                #
                i -= object_size
            #
            page = page.address[0]
        #
        self.collect_heads[n] = linked_list
        self.collect_tails[n] = first_loc_in_linked_list


def maybe_read_mark_byte(addr):
    "NOT_RPYTHON"
    try:
        return addr.ptr.mark
    except AttributeError:
        return '\x00'
