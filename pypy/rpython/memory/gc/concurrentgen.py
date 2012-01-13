import time, sys
from pypy.rpython.lltypesystem import lltype, llmemory, llarena, llgroup, rffi
from pypy.rpython.lltypesystem.llmemory import raw_malloc_usage
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.annlowlevel import llhelper
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.rlib.objectmodel import we_are_translated, running_on_llinterp
from pypy.rlib.debug import ll_assert, debug_print, debug_start, debug_stop
from pypy.rlib.rarithmetic import ovfcheck, LONG_BIT, r_uint, intmask
from pypy.rpython.memory.gc.base import GCBase
from pypy.rpython.memory.gc import env
from pypy.rpython.memory import gctypelayout
from pypy.rpython.memory.support import get_address_stack
from pypy.module.thread import ll_thread

#
# A concurrent generational mark&sweep GC.
#
# This uses a separate thread to run the collections in parallel.
# This is an entirely non-moving collector, with a generational write
# barrier adapted to the concurrent marking done by the collector thread.
# See concurrentgen.txt for some details.
#

WORD = LONG_BIT // 8


# Objects start with an integer 'tid', which is decomposed as follows.
# Lowest byte: one of the following values (which are all odd, so
# let us know if the 'tid' is valid or is just a word-aligned address):
MARK_BYTE_1       = 0x6D    # 'm', 109
MARK_BYTE_2       = 0x4B    # 'K', 75
MARK_BYTE_3       = 0x25    # '%', 37
MARK_BYTE_STATIC  = 0x53    # 'S', 83
# Next lower byte: a combination of flags.
FL_WITHHASH       = 0x0100
FL_EXTRA          = 0x0200
# And the high half of the word contains the numeric typeid.


class ConcurrentGenGC(GCBase):
    _alloc_flavor_ = "raw"
    inline_simple_malloc = True
    #inline_simple_malloc_varsize = True
    needs_deletion_barrier = True
    needs_weakref_read_barrier = True
    prebuilt_gc_objects_are_static_roots = False
    malloc_zero_filled = True
    gcflag_extra = FL_EXTRA

    HDRPTR = lltype.Ptr(lltype.ForwardReference())
    HDR = lltype.Struct('header', ('tid', lltype.Signed),
                                  ('next', HDRPTR))   # <-- kill me later XXX
    HDRPTR.TO.become(HDR)
    HDRSIZE = llmemory.sizeof(HDR)
    NULL = lltype.nullptr(HDR)
    typeid_is_in_field = 'tid', llgroup.HALFSHIFT
    withhash_flag_is_in_field = 'tid', FL_WITHHASH
    # ^^^ prebuilt objects may have the flag FL_WITHHASH;
    #     then they are one word longer, the extra word storing the hash.

    TRANSLATION_PARAMS = {
        # Automatically adjust the remaining parameters from the environment.
        "read_from_env": True,

        # The minimal RAM usage: use 24 MB by default.
        # Environment variable: PYPY_GC_MIN
        "min_heap_size": 24*1024*1024,
        }


    def __init__(self, config,
                 read_from_env=False,
                 min_heap_size=128*WORD,
                 **kwds):
        GCBase.__init__(self, config, **kwds)
        self.read_from_env = read_from_env
        self.min_heap_size = r_uint(min_heap_size)
        #
        self.main_thread_ident = ll_thread.get_ident() # non-transl. debug only
        #
        self.extra_objects_to_mark = self.AddressStack()
        self.flagged_objects = self.AddressStack()
        self.prebuilt_root_objects = self.AddressStack()
        #
        # Create the CollectorThread object
        self.collector = CollectorThread(self)
        #
        self._initialize()
        #
        # Write barrier: actually a deletion barrier, triggered when there
        # is a collection running and the mutator tries to change an object
        # that was not scanned yet.
        self._init_writebarrier_logic()

    def _initialize(self):
        # Initialize the GC.  In normal translated program, this function
        # is not translated but just called from __init__ ahead of time.
        # During test_transformed_gc, it is translated, so that we can
        # quickly reset the GC between tests.
        #
        self.extra_objects_to_mark.clear()
        self.flagged_objects.clear()
        self.prebuilt_root_objects.clear()
        #
        # The linked list of new young objects, and the linked list of
        # all old objects.  Note that the aging objects are not here
        # but on 'collector.aging_objects'.  Note also that 'old_objects'
        # contains the objects that the write barrier re-marked as young
        # (so they are "old young objects").
        self.new_young_objects = self.NULL
        self.new_young_objects_wr = self.NULL      # weakrefs
        self.new_young_objects_size = r_uint(0)
        self.old_objects = self.NULL
        self.old_objects_wr = self.NULL
        self.old_objects_size = r_uint(0)    # total size of self.old_objects
        #
        # See concurrentgen.txt for more information about these fields.
        self.current_young_marker = MARK_BYTE_1
        self.current_aging_marker = MARK_BYTE_2
        self.current_old_marker   = MARK_BYTE_3
        #
        self.num_major_collects = 0
        #self.ready_to_start_lock = ...built in setup()
        #self.finished_lock = ...built in setup()
        #self.mutex_lock = ...built in setup()
        #
        self.collector._initialize()

    def setup(self):
        "Start the concurrent collector thread."
        # don't call GCBase.setup(self), because we don't need
        # 'run_finalizers' as a deque
        debug_start("gc-startup")
        self.finalizer_lock_count = 0
        #
        self.ready_to_start_lock = ll_thread.allocate_ll_lock()
        self.finished_lock = ll_thread.allocate_ll_lock()
        self.mutex_lock = ll_thread.allocate_ll_lock()
        #
        self.acquire(self.finished_lock)
        self.acquire(self.ready_to_start_lock)
        #
        self.collector.setup()
        #
        self.set_min_heap_size(self.min_heap_size)
        if self.read_from_env:
            #
            newsize = env.read_from_env('PYPY_GC_MIN')
            if newsize > 0:
                self.set_min_heap_size(r_uint(newsize))
        #
        debug_print("minimal heap size:", self.min_heap_size)
        debug_stop("gc-startup")

    def set_min_heap_size(self, newsize):
        # See concurrentgen.txt.
        self.min_heap_size = newsize
        self.total_memory_size = newsize     # total heap size
        self.nursery_limit = newsize >> 2    # total size of the '->new...' box
        #
        # The in-use portion of the '->new...' box contains the objs
        # that are in the 'new_young_objects' list.  The total of their
        # size is 'new_young_objects_size'.
        #
        # The 'old objects' box contains the objs that are in the
        # 'old_objects' list.  The total of their size is 'old_objects_size'.
        #
        # The write barrier occasionally resets the mark byte of objects
        # to 'young'.  This is done without adding or removing objects
        # to the above lists, and consequently without correcting the
        # '*_size' variables.  Because of that, the 'old_objects' lists
        # may contain a few objects that are not marked 'old' any more,
        # and conversely, prebuilt objects may end up marked 'old' but
        # are never added to the 'old_objects' list.

    def update_total_memory_size(self):
        # compute the new value for 'total_memory_size': it should be
        # twice old_objects_size, but never less than 2/3rd of the old value,
        # and at least 'min_heap_size'
        absolute_maximum = r_uint(-1)
        if self.old_objects_size < absolute_maximum // 2:
            tms = self.old_objects_size * 2
        else:
            tms = absolute_maximum
        tms = max(tms, self.total_memory_size // 3 * 2)
        tms = max(tms, self.min_heap_size)
        self.total_memory_size = tms
        debug_print("total memory size:", tms)


    def _teardown(self):
        "Stop the collector thread after tests have run."
        self.wait_for_the_end_of_collection()
        #
        # start the next collection, but with collector.running set to 42,
        # which should shut down the collector thread
        self.collector.running = 42
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
                               needs_finalizer=False,
                               finalizer_is_light=False,
                               contains_weakptr=False):
        # Generic function to allocate any fixed-size object.
        #
        # Case of finalizers (test constant-folded)
        if needs_finalizer:
            raise NotImplementedError
            ll_assert(not contains_weakptr,
                     "'needs_finalizer' and 'contains_weakptr' both specified")
            return self._malloc_with_finalizer(typeid, size)
        #
        # Case of weakreferences (test constant-folded)
        if contains_weakptr:
            return self._malloc_weakref(typeid, size)
        #
        # Regular case
        return self._malloc_regular(typeid, size)

    def malloc_varsize_clear(self, typeid, length, size, itemsize,
                             offset_to_length):
        # Generic function to allocate any variable-size object.
        #
        nonvarsize = self.gcheaderbuilder.size_gc_header + size
        #
        if length < 0:
            raise MemoryError
        try:
            totalsize = ovfcheck(nonvarsize + ovfcheck(itemsize * length))
        except OverflowError:
            raise MemoryError
        #
        return self._do_malloc(typeid, totalsize, offset_to_length, length, 0)


    def _malloc_regular(self, typeid, size):
        totalsize = self.gcheaderbuilder.size_gc_header + size
        return self._do_malloc(typeid, totalsize, -1, -1, 0)
    _malloc_regular._dont_inline_ = True

    def _malloc_weakref(self, typeid, size):
        totalsize = self.gcheaderbuilder.size_gc_header + size
        return self._do_malloc(typeid, totalsize, -1, -1, 1)
    _malloc_weakref._dont_inline_ = True


    def _do_malloc(self, typeid, totalsize, offset_to_length, length,
                   linked_list_number):
        # Generic function to perform allocation.  Inlined in its few callers,
        # so that some checks like 'offset_to_length >= 0' are removed.
        rawtotalsize = raw_malloc_usage(totalsize)
        adr = llarena.arena_malloc(rawtotalsize, 2)
        if adr == llmemory.NULL:
            raise MemoryError
        llarena.arena_reserve(adr, totalsize)
        obj = adr + self.gcheaderbuilder.size_gc_header
        if offset_to_length >= 0:
            (obj + offset_to_length).signed[0] = length
            totalsize = llarena.round_up_for_allocation(totalsize)
            rawtotalsize = raw_malloc_usage(totalsize)
        hdr = self.header(obj)
        hdr.tid = self.combine(typeid, self.current_young_marker, 0)
        if linked_list_number == 0:
            hdr.next = self.new_young_objects
            self.new_young_objects = hdr
        elif linked_list_number == 1:
            hdr.next = self.new_young_objects_wr
            self.new_young_objects_wr = hdr
        else:
            raise AssertionError(linked_list_number)
        self.new_young_objects_size += r_uint(rawtotalsize)
        if self.new_young_objects_size > self.nursery_limit:
            self.nursery_overflowed(obj)
        return llmemory.cast_adr_to_ptr(obj, llmemory.GCREF)
    _do_malloc._always_inline_ = True

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

    def deletion_barrier(self, addr_struct):
        # XXX check the assembler
        mark = self.header(addr_struct).tid & 0xFF
        if mark != self.current_young_marker:
            self.force_scan(addr_struct)

    def assume_young_pointers(self, addr_struct):
        raise NotImplementedError

    def writebarrier_before_copy(self, source_addr, dest_addr,
                                 source_start, dest_start, length):
        return False  # XXX implement

    def _init_writebarrier_logic(self):
        #
        def force_scan(obj):
            cym = self.current_young_marker
            com = self.current_old_marker
            mark = self.get_mark(obj)
            #debug_print("deletion_barrier:", mark, obj)
            #
            if mark == com:     # most common case, make it fast
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
                    ll_assert(self.collector.running == 1,
                              "write barrier: wrong call?")
                    #
                    # It's fine to set the mark before tracing, because
                    # we are anyway in a 'mutex_lock' critical section.
                    # The collector thread will not exit from the phase
                    # 'collector.running == 1' here.
                    self.trace(obj, self._barrier_add_extra, None)
                    #
                    # Still at 1:
                    ll_assert(self.collector.running == 1,
                              "write barrier: oups!?")
                    #
                else:
                    # a 'com' mark is possible here: the collector thread
                    # sets it in parallel to objects.  In that case it has
                    # been handled already.
                    ll_assert(mark == self.current_old_marker,
                              "write barrier: bogus object mark")
                #
                self.release(self.mutex_lock)
            #
            # In all cases, the object is now flagged
            self.flagged_objects.append(obj)
        #
        force_scan._dont_inline_ = True
        force_scan._should_never_raise_ = True
        self.force_scan = force_scan

    def _barrier_add_extra(self, root, ignored):
        obj = root.address[0]
        self.get_mark(obj)
        self.extra_objects_to_mark.append(obj)

    # ----------

    def nursery_overflowed(self, newest_obj):
        # See concurrentgen.txt.  Called after the nursery overflowed.
        #
        debug_start("gc-nursery-full")
        #
        if self.previous_collection_finished():
            # The previous collection finished; no collection is running now.
            #
            # Expand the nursery if we can, up to 25% of total_memory_size.
            # In some cases, the limiting factor is that the nursery size
            # plus the old objects size must not be larger than
            # total_memory_size.
            expand_to = self.total_memory_size >> 2
            expand_to = min(expand_to, self.total_memory_size -
                                       self.old_objects_size)
            if expand_to > self.nursery_limit:
                debug_print("expanding nursery limit to:", expand_to)
                self.nursery_limit = expand_to
                #
                # If 'new_young_objects_size' is not greater than this
                # expanded 'nursery_size', then we are done: we can just
                # continue filling the nursery.
                if self.new_young_objects_size <= self.nursery_limit:
                    debug_stop("gc-nursery-full")
                    return
            #
            # Else, we trigger the next minor collection now.
            self.flagged_objects.append(newest_obj)
            self._start_minor_collection()
            #
            # Now there is no new object left.
            ll_assert(self.new_young_objects_size == r_uint(0),
                      "new object left behind?")
            #
            # Reset the nursery size to be at most 25% of
            # total_memory_size, and initially no more than
            # 3/4*total_memory_size - old_objects_size.  If that value
            # is not positive, then we immediately go into major
            # collection mode.
            three_quarters = (self.total_memory_size >> 2) * 3
            if self.old_objects_size < three_quarters:
                newsize = three_quarters - self.old_objects_size
                newsize = min(newsize, self.total_memory_size >> 2)
                self.nursery_limit = newsize
                debug_print("total memory size:", self.total_memory_size)
                debug_print("initial nursery limit:", self.nursery_limit)
                debug_stop("gc-nursery-full")
                return

        # The previous collection is likely not finished yet.
        # At this point we want a full collection to occur.
        debug_print("starting a major collection")
        #
        # We have to first wait for the previous minor collection to finish:
        self.wait_for_the_end_of_collection()
        #
        # Start the major collection.
        self._start_major_collection(newest_obj)
        #
        debug_stop("gc-nursery-full")


    def wait_for_the_end_of_collection(self):
        if self.collector.running != 0:
            self.stop_collection(wait=True)


    def previous_collection_finished(self):
        return self.collector.running == 0 or self.stop_collection(wait=False)


    def stop_collection(self, wait):
        ll_assert(self.collector.running != 0, "stop_collection: running == 0")
        #
        debug_start("gc-stop")
        major_collection = (self.collector.major_collection_phase == 2)
        if major_collection or wait:
            debug_print("waiting for the end of collection, major =",
                        int(major_collection))
            self.acquire(self.finished_lock)
        else:
            if not self.try_acquire(self.finished_lock):
                debug_print("minor collection not finished!")
                debug_stop("gc-stop")
                return False
        #
        debug_print("old objects size:", self.old_objects_size)
        debug_stop("gc-stop")
        self.collector.running = 0
        #debug_print("collector.running = 0")
        #
        # Check invariants
        ll_assert(not self.extra_objects_to_mark.non_empty(),
                  "objs left behind in extra_objects_to_mark")
        ll_assert(not self.collector.gray_objects.non_empty(),
                  "objs left behind in gray_objects")
        #
        if self.DEBUG:
            self.debug_check_lists()
        #
        if major_collection:
            self.collector.major_collection_phase = 0
            # Update the total memory usage to 2 times the old objects' size
            self.update_total_memory_size()
        #
        return True


    def execute_finalizers_ll(self):
        return # XXX
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


    def collect(self, gen=4):
        debug_start("gc-forced-collect")
        self.wait_for_the_end_of_collection()
        self._start_major_collection(llmemory.NULL)
        self.wait_for_the_end_of_collection()
        self.execute_finalizers_ll()
        debug_stop("gc-forced-collect")
        return
        # XXX reimplement this:
        """
        gen=0: Trigger a minor collection if none is running.  Never blocks,
        except if it happens to start a major collection.
        
        gen=1: The same, but if a minor collection is running, wait for
        it to finish before triggering the next one.  Guarantees that
        young objects not reachable when collect() is called will soon
        be freed.

        gen=2: The same, but wait for the triggered collection to
        finish.  Guarantees that young objects not reachable when
        collect() is called will be freed by the time collect() returns.

        gen=3: Trigger a major collection, waiting for it to start.
        Guarantees that any object not reachable when collect() is called
        will soon be freed.

        gen>=4: Do a full synchronous major collection.
        """

    def _start_minor_collection(self, major_collection_phase=0):
        #
        debug_start("gc-minor-start")
        #
        # Scan the stack roots and the refs in non-GC objects
        self.root_walker.walk_roots(
            ConcurrentGenGC._add_stack_root,  # stack roots
            ConcurrentGenGC._add_stack_root,  # in prebuilt non-gc
            None)                             # static in prebuilt gc
        #
        # Add the objects still waiting in 'objects_with_finalizers_to_run'
        #p = self.objects_with_finalizers_to_run
        #while p != self.NULL:
        #    x = llmemory.cast_ptr_to_adr(p)
        #    x = llarena.getfakearenaaddress(x) + 8
        #    obj = x + self.gcheaderbuilder.size_gc_header
        #    #debug_print("_objects_with_finalizers_to_run", obj)
        #    self.get_mark(obj)
        #    self.gray_objects.append(obj)
        #    p = list_next(p)
        #
        # Add all old objects that have been written to since the last
        # time trigger_next_collection was called
        self.flagged_objects.foreach(self._add_flagged_root, None)
        #
        # Clear this list
        self.flagged_objects.clear()
        #
        # Exchange the meanings of 'cym' and 'cam'
        other = self.current_young_marker
        self.current_young_marker = self.current_aging_marker
        self.current_aging_marker = other
        #
        # Copy a few 'mutator' fields to 'collector' fields
        self.collector.aging_objects    = self.new_young_objects
        self.collector.aging_objects_wr = self.new_young_objects_wr
        self.new_young_objects = self.NULL
        self.new_young_objects_wr = self.NULL
        self.new_young_objects_size = r_uint(0)
        #self.collect_weakref_pages = self.weakref_pages
        #self.collect_finalizer_pages = self.finalizer_pages
        #
        # Start the collector thread
        self._start_collection_common(major_collection_phase)
        #
        debug_stop("gc-minor-start")

    def _start_major_collection(self, newest_obj):
        #
        debug_start("gc-major-collection")
        #
        # Force a minor collection's marking step to occur now
        if newest_obj:
            self.flagged_objects.append(newest_obj)
        self._start_minor_collection(major_collection_phase=1)
        #
        # Wait for it to finish
        self.stop_collection(wait=True)
        #
        # Assert that this list is still empty (cleared by the call to
        # _start_minor_collection)
        ll_assert(not self.flagged_objects.non_empty(),
                  "flagged_objects should be empty here")
        ll_assert(self.new_young_objects == self.NULL,
                  "new_young_obejcts should be empty here")
        ll_assert(self.new_young_objects_wr == self.NULL,
                  "new_young_obejcts_wr should be empty here")
        #
        # Keep this newest_obj alive
        if newest_obj:
            self.collector.gray_objects.append(newest_obj)
        #
        # Scan again the stack roots and the refs in non-GC objects
        self.root_walker.walk_roots(
            ConcurrentGenGC._add_stack_root,  # stack roots
            ConcurrentGenGC._add_stack_root,  # in prebuilt non-gc
            None)                             # static in prebuilt gc
        #
        # Add the objects still waiting in 'objects_with_finalizers_to_run'
        #xxx
        #
        # Add all prebuilt objects that have ever been mutated
        self.prebuilt_root_objects.foreach(self._add_prebuilt_root, None)
        #
        # Exchange the meanings of 'com' and 'cam'
        other = self.current_old_marker
        self.current_old_marker = self.current_aging_marker
        self.current_aging_marker = other
        #
        # Copy a few 'mutator' fields to 'collector' fields
        self.collector.delayed_aging_objects = self.collector.aging_objects
        self.collector.delayed_aging_objects_wr=self.collector.aging_objects_wr
        self.collector.aging_objects = self.old_objects
        self.collector.aging_objects_wr = self.old_objects_wr
        self.old_objects = self.NULL
        self.old_objects_wr = self.NULL
        self.old_objects_size = r_uint(0)
        #self.collect_weakref_pages = self.weakref_pages
        #self.collect_finalizer_pages = self.finalizer_pages
        #
        # Start again the collector thread
        self._start_collection_common(major_collection_phase=2)
        #
        self.num_major_collects += 1
        debug_print("major collection", self.num_major_collects, "started")
        debug_stop("gc-major-collection")

    def _start_collection_common(self, major_collection_phase):
        self.collector.current_young_marker = self.current_young_marker
        self.collector.current_aging_marker = self.current_aging_marker
        self.collector.current_old_marker   = self.current_old_marker
        self.collector.major_collection_phase = major_collection_phase
        self.collector.running = 1
        #debug_print("collector.running = 1")
        self.release(self.ready_to_start_lock)

    def _add_stack_root(self, root):
        # NB. it's ok to edit 'gray_objects' from the mutator thread here,
        # because the collector thread is not running yet
        obj = root.address[0]
        #debug_print("_add_stack_root", obj)
        #assert 'DEAD' not in repr(obj)
        self.get_mark(obj)
        self.collector.gray_objects.append(obj)

    def _add_flagged_root(self, obj, ignored):
        #debug_print("_add_flagged_root", obj)
        #
        # Important: the mark on 'obj' must be 'cym', otherwise it will not
        # be scanned at all.  It should generally be, except in rare cases
        # where it was reset to 'com' by the collector thread.
        mark = self.get_mark(obj)
        if mark == self.current_old_marker:
            self.set_mark(obj, self.current_young_marker)
        else:
            ll_assert(mark == self.current_young_marker,
                      "add_flagged: bad mark")
        #
        self.collector.gray_objects.append(obj)

    def _add_prebuilt_root(self, obj, ignored):
        self.get_mark(obj)
        self.collector.gray_objects.append(obj)

    def debug_check_lists(self):
        # check that they are correct, non-infinite linked lists,
        # and check that the total size of objects in the lists corresponds
        # precisely to the value recorded
        size = self.debug_check_list(self.new_young_objects)
        size += self.debug_check_list(self.new_young_objects_wr)
        ll_assert(size == self.new_young_objects_size,
                  "bogus total size in new_young_objects")
        #
        size = self.debug_check_list(self.old_objects)
        size += self.debug_check_list(self.old_objects_wr)
        ll_assert(size == self.old_objects_size,
                  "bogus total size in old_objects")

    def debug_check_list(self, list):
        previous = self.NULL
        count = 0
        size = r_uint(0)
        size_gc_header = self.gcheaderbuilder.size_gc_header
        while list != self.NULL:
            obj = llmemory.cast_ptr_to_adr(list) + size_gc_header
            size1 = size_gc_header + self.get_size(obj)
            #print "debug:", llmemory.raw_malloc_usage(size1)
            size += llmemory.raw_malloc_usage(size1)
            # detect loops
            ll_assert(list != previous, "loop!")
            count += 1
            if count & (count-1) == 0:    # only on powers of two, to
                previous = list           # detect loops of any size
            list = list.next
        #print "\tTOTAL:", size
        return size

    def acquire(self, lock):
        if we_are_translated():
            ll_thread.c_thread_acquirelock_NOAUTO(lock, 1)
        else:
            assert ll_thread.get_ident() == self.main_thread_ident
            while not self.try_acquire(lock):
                time.sleep(0.05)
                # ---------- EXCEPTION FROM THE COLLECTOR THREAD ----------
                if hasattr(self.collector, '_exc_info'):
                    self._reraise_from_collector_thread()

    def try_acquire(self, lock):
        res = ll_thread.c_thread_acquirelock_NOAUTO(lock, 0)
        return rffi.cast(lltype.Signed, res) != 0

    def release(self, lock):
        ll_thread.c_thread_releaselock_NOAUTO(lock)

    def _reraise_from_collector_thread(self):
        exc, val, tb = self.collector._exc_info
        raise exc, val, tb

    def set_mark(self, obj, newmark):
        _set_mark(self.header(obj), newmark)

    def get_mark(self, obj):
        mark = self.header(obj).tid & 0xFF
        ll_assert(mark == MARK_BYTE_1 or
                  mark == MARK_BYTE_2 or
                  mark == MARK_BYTE_3 or
                  mark == MARK_BYTE_STATIC, "bad mark byte in object")
        return mark

    # ----------
    # Weakrefs

    def weakref_deref(self, wrobj):
        # Weakrefs need some care.  This code acts as a read barrier.
        # The only way I found is to acquire the mutex_lock to prevent
        # the collection thread from going from collector.running==1
        # to collector.running==2, or from collector.running==2 to
        # collector.running==3.
        #
        self.acquire(self.mutex_lock)
        #
        targetobj = gctypelayout.ll_weakref_deref(wrobj)
        if targetobj != llmemory.NULL:
            #
            if self.collector.running == 1:
                # If we are in the phase collector.running==1, we don't
                # know if the object will be scanned a bit later or
                # not; so we have to assume that it survives, and
                # force it to be scanned.
                self.get_mark(targetobj)
                self.extra_objects_to_mark.append(targetobj)
                #
            elif self.collector.running == 2:
                # In the phase collector.running==2, if the object is
                # not marked it's too late; we have to detect that case
                # and return NULL instead here, as if the corresponding
                # collector phase was already finished (deal_with_weakrefs).
                # Otherwise we would be returning an object that is about to
                # be swept away.
                if not self.collector.is_marked_or_static(targetobj):
                    targetobj = llmemory.NULL
                #
            else:
                # In other phases we are fine.
                pass
        #
        self.release(self.mutex_lock)
        #
        return targetobj


# ____________________________________________________________
#
# The collector thread is put on another class, in order to separate
# it more cleanly (both from a code organization point of view and
# from the point of view of cache locality).


class CollectorThread(object):
    _alloc_flavor_ = "raw"

    NULL = ConcurrentGenGC.NULL

    def __init__(self, gc):
        self.gc = gc
        #
        # a different AddressStack class, which uses a different pool
        # of free pages than the regular one, so can run concurrently
        self.CollectorAddressStack = get_address_stack(lock="collector")
        self.gray_objects = self.CollectorAddressStack()
        #
        # The start function for the thread, as a function and not a method
        def collector_start():
            if we_are_translated():
                self.collector_run()
            else:
                self.collector_run_nontranslated()
        collector_start._should_never_raise_ = True
        self.collector_start = collector_start

    def _initialize(self):
        self.gray_objects.clear()
        #
        # When the mutator thread wants to trigger the next collection,
        # it scans its own stack roots and prepares everything, then
        # sets 'collector.running' to 1, and releases
        # 'ready_to_start_lock'.  This triggers the collector thread,
        # which re-acquires 'ready_to_start_lock' and does its job.
        # When done it releases 'finished_lock'.  The mutator thread is
        # responsible for resetting 'collector.running' to 0.
        #
        # The collector thread's state can be found (with careful locking)
        # by inspecting the same variable from the mutator thread:
        #   * collector.running == 1: Marking.  [Deletion barrier active.]
        #   * collector.running == 2: Clearing weakrefs.
        #   * collector.running == 3: Marking from unreachable finalizers.
        #   * collector.running == 4: Sweeping.
        #   * collector.running == -1: Done.
        # The mutex_lock is acquired to go from 1 to 2, and from 2 to 3.
        self.running = 0
        self.major_collection_phase = 0
        #
        # when the collection starts, we make all young objects aging and
        # move 'new_young_objects' into 'aging_objects'
        self.aging_objects = self.NULL
        self.aging_objects_wr = self.NULL
        self.delayed_aging_objects = self.NULL
        self.delayed_aging_objects_wr = self.NULL

    def setup(self):
        self.ready_to_start_lock = self.gc.ready_to_start_lock
        self.finished_lock = self.gc.finished_lock
        self.mutex_lock = self.gc.mutex_lock
        #
        # start the thread
        self.collector_ident = ll_thread.c_thread_start_nowrapper(
            llhelper(ll_thread.CALLBACK, self.collector_start))
        assert self.collector_ident != -1

    def acquire(self, lock):
        ll_thread.c_thread_acquirelock_NOAUTO(lock, 1)

    def release(self, lock):
        ll_thread.c_thread_releaselock_NOAUTO(lock)

    def get_mark(self, obj):
        return self.gc.get_mark(obj)

    def set_mark(self, obj, newmark):
        self.gc.set_mark(obj, newmark)

    def collector_run_nontranslated(self):
        try:
            if not hasattr(self.gc, 'currently_running_in_rtyper'):
                self.collector_run()     # normal tests
            else:
                # this case is for test_transformed_gc: we need to spawn
                # another LLInterpreter for this new thread.
                from pypy.rpython.llinterp import LLInterpreter
                llinterp = LLInterpreter(self.gc.currently_running_in_rtyper)
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
            if self.running == 42:
                self.release(self.finished_lock)
                break
            #
            self.collector_presweep()
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
            extra_objects_to_mark = self.gc.extra_objects_to_mark
            while extra_objects_to_mark.non_empty():
                obj = extra_objects_to_mark.pop()
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
        self.running = 2
        #debug_print("collection_running = 2")
        self.release(self.mutex_lock)

    def _collect_mark(self):
        extra_objects_to_mark = self.gc.extra_objects_to_mark
        cam = self.current_aging_marker
        com = self.current_old_marker
        while self.gray_objects.non_empty():
            obj = self.gray_objects.pop()
            if self.get_mark(obj) != cam:
                continue
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
            #debug_print("mark:", obj)
            self.gc.trace(obj, self._collect_add_pending, None)
            self.set_mark(obj, com)
            #
            # Interrupt early if the mutator's write barrier adds stuff
            # to that list.  Note that the check is imprecise because
            # it is not lock-protected, but that's good enough.  The
            # idea is that we trace in priority objects flagged with
            # the write barrier, because they are more likely to
            # reference further objects that will soon be accessed too.
            if extra_objects_to_mark.non_empty():
                break

    def _collect_add_pending(self, root, ignored):
        obj = root.address[0]
        # these 'get_mark(obj)' are here for debugging invalid marks.
        # XXX check that the C compiler removes them if lldebug is off
        self.get_mark(obj)
        self.gray_objects.append(obj)


    def collector_sweep(self):
        if self.major_collection_phase != 1:  # no sweeping during phase 1
            self.update_size = self.gc.old_objects_size
            #
            lst = self._collect_do_sweep(self.aging_objects,
                                         self.current_aging_marker,
                                         self.gc.old_objects)
            self.gc.old_objects = lst
            #
            lst = self._collect_do_sweep(self.aging_objects_wr,
                                         self.current_aging_marker,
                                         self.gc.old_objects_wr)
            self.gc.old_objects_wr = lst
            #
            self.gc.old_objects_size = self.update_size
        #
        self.running = -1
        #debug_print("collection_running = -1")

    def collector_presweep(self):
        if self.major_collection_phase == 2:  # only in this phase
            # Finish the delayed sweep from the previous minor collection.
            # The objects left unmarked were left with 'cam', which is
            # now 'com' because we switched their values.
            self.update_size = r_uint(0)
            lst = self._collect_do_sweep(self.delayed_aging_objects,
                                         self.current_old_marker,
                                         self.aging_objects)
            self.aging_objects = lst
            self.delayed_aging_objects = self.NULL
            #
            lst = self._collect_do_sweep(self.delayed_aging_objects_wr,
                                         self.current_old_marker,
                                         self.aging_objects_wr)
            self.aging_objects_wr = lst
            self.delayed_aging_objects_wr = self.NULL

    def _collect_do_sweep(self, hdr, still_not_marked, linked_list):
        size_gc_header = self.gc.gcheaderbuilder.size_gc_header
        #
        while hdr != self.NULL:
            nexthdr = hdr.next
            mark = hdr.tid & 0xFF
            if mark == still_not_marked:
                # the object is still not marked.  Free it.
                blockadr = llmemory.cast_ptr_to_adr(hdr)
                #debug_print("free:", blockadr + size_gc_header)
                blockadr = llarena.getfakearenaaddress(blockadr)
                llarena.arena_free(blockadr)
                #
            else:
                # the object was marked: relink it
                ll_assert(mark == self.current_old_marker or
                          mark == self.current_aging_marker or
                          mark == self.current_young_marker,
                          "sweep: bad mark")
                hdr.next = linked_list
                linked_list = hdr
                #
                # count its size
                obj = llmemory.cast_ptr_to_adr(hdr) + size_gc_header
                size1 = size_gc_header + self.gc.get_size(obj)
                self.update_size += llmemory.raw_malloc_usage(size1)
                #
            hdr = nexthdr
        #
        return linked_list


    # -------------------------
    # CollectorThread: Weakrefs

    def is_marked_or_static(self, obj):
        return self.get_mark(obj) != self.current_aging_marker

    def deal_with_weakrefs(self):
        # For simplicity, we do the minimal amount of work here: if a weakref
        # dies or points to a dying object, we clear it and move it from
        # 'aging_objects_wr' to 'aging_objects'.  Otherwise, we keep it in
        # 'aging_objects_wr'.
        size_gc_header = self.gc.gcheaderbuilder.size_gc_header
        linked_list    = self.aging_objects
        linked_list_wr = self.NULL
        #
        hdr = self.aging_objects_wr
        while hdr != self.NULL:
            nexthdr = hdr.next
            #
            mark = hdr.tid & 0xFF
            if mark == self.current_aging_marker:
                # the weakref object itself is not referenced any more
                valid = False
                #
            else:
                #
                type_id = llop.extract_high_ushort(llgroup.HALFWORD, hdr.tid)
                offset = self.gc.weakpointer_offset(type_id)
                ll_assert(offset >= 0, "bad weakref")
                obj = llmemory.cast_ptr_to_adr(hdr) + size_gc_header
                pointing_to = (obj + offset).address[0]
                if pointing_to == llmemory.NULL:
                    # special case only for fresh new weakrefs not yet filled
                    valid = True
                    #
                elif not self.is_marked_or_static(pointing_to):
                    # 'pointing_to' dies
                    (obj + offset).address[0] = llmemory.NULL
                    valid = False
                else:
                    valid = True
            #
            if valid:
                hdr.next = linked_list_wr
                linked_list = linked_list_wr
            else:
                hdr.next = linked_list
                linked_list = hdr.next
            #
            hdr = nexthdr
        #
        self.aging_objects = linked_list
        self.aging_objects_wr = linked_list_wr
        #
        self.acquire(self.mutex_lock)
        self.running = 3
        #debug_print("collector.running = 3")
        self.release(self.mutex_lock)

    # ---------------------------
    # CollectorThread: Finalizers

    def deal_with_objects_with_finalizers(self):
        self.running = 4; return
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
        self.collector.running = 4
        #debug_print("collection_running = 4")


# ____________________________________________________________
#
# Hack to write the 'mark' or the 'flags' bytes of an object header
# without overwriting the whole word.  Essential in the rare case where
# the other thread might be concurrently writing the other byte.

concurrent_setter_lock = ll_thread.allocate_lock()

def emulate_set_mark(p, v):
    "NOT_RPYTHON"
    assert v in (MARK_BYTE_1, MARK_BYTE_2, MARK_BYTE_3, MARK_BYTE_STATIC)
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
