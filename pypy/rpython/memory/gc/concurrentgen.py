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
from pypy.rpython.memory.support import get_address_stack
from pypy.module.thread import ll_thread

#
# A "3/4th concurrent" generational mark&sweep GC.
#
# This uses a separate thread to run the minor collections in parallel.
# See concurrentgen.txt for some details.
#
# Major collections are serialized for the mark phase, but the sweep
# phase can be parallelized again.  XXX not done so far, YYY investigate
# also completely parallelizing them too
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

    HDRPTR = lltype.Ptr(lltype.ForwardReference())
    HDR = lltype.Struct('header', ('tid', lltype.Signed),
                                  ('next', HDRPTR))   # <-- kill me later
    HDRPTR.TO.become(HDR)
    HDRSIZE = llmemory.sizeof(HDR)
    NULL = lltype.nullptr(HDR)
    typeid_is_in_field = 'tid', llgroup.HALFSHIFT
    withhash_flag_is_in_field = 'tid', FL_WITHHASH
    # ^^^ prebuilt objects may have the flag FL_WITHHASH;
    #     then they are one word longer, the extra word storing the hash.

    TRANSLATION_PARAMS = {}

    def __init__(self, config, **kwds):
        GCBase.__init__(self, config, **kwds)
        self.main_thread_ident = ll_thread.get_ident()
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
        self.old_objects = self.NULL
        #
        # See concurrentgen.txt for more information about these fields.
        self.current_young_marker = MARK_BYTE_1
        self.collector.current_aging_marker = MARK_BYTE_2
        #
        #self.ready_to_start_lock = ...built in setup()
        #self.finished_lock = ...built in setup()
        #self.mutex_lock = ...built in setup()
        #
        self.collector._initialize()

    def setup(self):
        "Start the concurrent collector thread."
        # don't call GCBase.setup(self), because we don't need
        # 'run_finalizers' as a deque
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
                               needs_finalizer=False, contains_weakptr=False):
        #
        # For now, we always start the next collection as soon as the
        # previous one is finished
        if self.collector.running <= 0:
            self.trigger_next_collection()
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
            raise NotImplementedError
            return self._malloc_weakref(typeid, size)
        #
        # Regular case
        size_gc_header = self.gcheaderbuilder.size_gc_header
        totalsize = size_gc_header + size
        adr = llarena.arena_malloc(llmemory.raw_malloc_usage(totalsize), 2)
        if adr == llmemory.NULL:
            raise MemoryError
        llarena.arena_reserve(adr, totalsize)
        obj = adr + size_gc_header
        hdr = self.header(obj)
        hdr.tid = self.combine(typeid, self.current_young_marker, 0)
        hdr.next = self.new_young_objects
        self.new_young_objects = hdr
        return llmemory.cast_adr_to_ptr(obj, llmemory.GCREF)

    def malloc_varsize_clear(self, typeid, length, size, itemsize,
                             offset_to_length):
        #
        # For now, we always start the next collection as soon as the
        # previous one is finished
        if self.collector.running <= 0:
            self.trigger_next_collection()
        #
        size_gc_header = self.gcheaderbuilder.size_gc_header
        nonvarsize = size_gc_header + size
        #
        if length < 0:
            raise MemoryError
        try:
            totalsize = ovfcheck(nonvarsize + ovfcheck(itemsize * length))
        except OverflowError:
            raise MemoryError
        #
        adr = llarena.arena_malloc(llmemory.raw_malloc_usage(totalsize), 2)
        if adr == llmemory.NULL:
            raise MemoryError
        llarena.arena_reserve(adr, totalsize)
        obj = adr + size_gc_header
        (obj + offset_to_length).signed[0] = length
        hdr = self.header(obj)
        hdr.tid = self.combine(typeid, self.current_young_marker, 0)
        hdr.next = self.new_young_objects
        self.new_young_objects = hdr
        return llmemory.cast_adr_to_ptr(obj, llmemory.GCREF)

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
            mark = self.get_mark(obj)
            #debug_print("deletion_barrier:", mark, obj)
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
                if mark == self.collector.current_aging_marker:
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
        force_scan._should_never_raise_ = True
        self.force_scan = force_scan

    def _barrier_add_extra(self, root, ignored):
        obj = root.address[0]
        self.get_mark(obj)
        self.extra_objects_to_mark.append(obj)


    def wait_for_the_end_of_collection(self):
        """In the mutator thread: wait for the minor collection currently
        running (if any) to finish."""
        if self.collector.running != 0:
            debug_start("gc-stop")
            #
            self.acquire(self.finished_lock)
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
            debug_stop("gc-stop")
            #
            # We must *not* run execute_finalizers_ll() here, because it
            # can start the next collection, and then this function returns
            # with a collection in progress, which it should not.  Be careful
            # to call execute_finalizers_ll() in the caller somewhere.
            ll_assert(self.collector.running == 0,
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

        gen>=3: Major collection.

        XXX later:
           gen=3: Do a major collection, but don't wait for sweeping to finish.
           The most useful default.
           gen>=4: Do a full synchronous major collection.
        """
        debug_start("gc-forced-collect")
        debug_print("collect, gen =", gen)
        if gen >= 1 or self.collector.running <= 0:
            self.trigger_next_collection(gen >= 3)
            if gen >= 2:
                self.wait_for_the_end_of_collection()
        self.execute_finalizers_ll()
        debug_stop("gc-forced-collect")

    def trigger_next_collection(self, force_major_collection=False):
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
        self.current_young_marker = self.collector.current_aging_marker
        self.collector.current_aging_marker = other
        #
        # Copy a few 'mutator' fields to 'collector' fields
        collector = self.collector
        collector.aging_objects = self.new_young_objects
        self.new_young_objects = self.NULL
        #self.collect_weakref_pages = self.weakref_pages
        #self.collect_finalizer_pages = self.finalizer_pages
        #
        # Start the collector thread
        self.collector.running = 1
        #debug_print("collector.running = 1")
        self.release(self.ready_to_start_lock)
        #
        debug_stop("gc-start")
        #
        self.execute_finalizers_ll()

    def _add_stack_root(self, root):
        # NB. it's ok to edit 'gray_objects' from the mutator thread here,
        # because the collector thread is not running yet
        obj = root.address[0]
        #debug_print("_add_stack_root", obj)
        self.get_mark(obj)
        self.collector.gray_objects.append(obj)

    def _add_flagged_root(self, obj, ignored):
        #debug_print("_add_flagged_root", obj)
        #
        # Important: the mark on 'obj' must be 'cym', otherwise it will not
        # be scanned at all.  It should generally be, except in rare cases
        # where it was reset to '#' by the collector thread.
        mark = self.get_mark(obj)
        if mark == MARK_BYTE_OLD:
            self.set_mark(obj, self.current_young_marker)
        else:
            ll_assert(mark == self.current_young_marker,
                      "add_flagged: bad mark")
        #
        self.collector.gray_objects.append(obj)

    def debug_check_lists(self):
        # just check that they are correct, non-infinite linked lists
        self.debug_check_list(self.new_young_objects)
        self.debug_check_list(self.old_objects)

    def debug_check_list(self, list):
        try:
            previous = self.NULL
            count = 0
            while list != self.NULL:
                # prevent constant-folding, and detects loops of length 1
                ll_assert(list != previous, "loop!")
                previous = list
                list = list.next
                count += 1
            return count
        except KeyboardInterrupt:
            ll_assert(False, "interrupted")
            raise

    def acquire(self, lock):
        if we_are_translated():
            ll_thread.c_thread_acquirelock(lock, 1)
        else:
            assert ll_thread.get_ident() == self.main_thread_ident
            while rffi.cast(lltype.Signed,
                            ll_thread.c_thread_acquirelock(lock, 0)) == 0:
                time.sleep(0.05)
                # ---------- EXCEPTION FROM THE COLLECTOR THREAD ----------
                if hasattr(self.collector, '_exc_info'):
                    self._reraise_from_collector_thread()

    def release(self, lock):
        ll_thread.c_thread_releaselock(lock)

    def _reraise_from_collector_thread(self):
        exc, val, tb = self.collector._exc_info
        raise exc, val, tb

    def set_mark(self, obj, newmark):
        _set_mark(self.header(obj), newmark)

    def get_mark(self, obj):
        mark = self.header(obj).tid & 0xFF
        ll_assert(mark == MARK_BYTE_1 or
                  mark == MARK_BYTE_2 or
                  mark == MARK_BYTE_OLD or
                  mark == MARK_BYTE_STATIC, "bad mark byte in object")
        return mark

    # ----------
    # Weakrefs

    def weakref_deref(self, wrobj):
        raise NotImplementedError
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
        #
        # when the collection starts, we make all young objects aging and
        # move 'new_young_objects' into 'aging_objects'
        self.aging_objects = self.NULL

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
        ll_thread.c_thread_acquirelock(lock, 1)

    def release(self, lock):
        ll_thread.c_thread_releaselock(lock)

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
            self.gc.trace(obj, self._collect_add_pending, None)
            self.set_mark(obj, MARK_BYTE_OLD)
            #
            # Interrupt early if the mutator's write barrier adds stuff
            # to that list.  Note that the check is imprecise because
            # it is not lock-protected, but that's good enough.  The
            # idea is that we trace in priority objects flagged with
            # the write barrier, because they are more likely to
            # reference further objects that will soon be accessed too.
            if extra_objects_to_mark.non_empty():
                return

    def _collect_add_pending(self, root, ignored):
        obj = root.address[0]
        # these 'get_mark(obj) are here for debugging invalid marks.
        # XXX check that the C compiler removes them if lldebug is off
        self.get_mark(obj)
        self.gray_objects.append(obj)

    def collector_sweep(self):
        cam = self.current_aging_marker
        hdr = self.aging_objects
        linked_list = self.gc.old_objects
        while hdr != self.NULL:
            nexthdr = hdr.next
            mark = hdr.tid & 0xFF
            if mark == cam:
                # the object is still not marked.  Free it.
                blockadr = llmemory.cast_ptr_to_adr(hdr)
                blockadr = llarena.getfakearenaaddress(blockadr)
                llarena.arena_free(blockadr)
                #
            else:
                # the object was marked: relink it
                ll_assert(mark == self.gc.current_young_marker or
                          mark == MARK_BYTE_OLD, "sweep: bad mark")
                hdr.next = linked_list
                linked_list = hdr
                #
            hdr = nexthdr
        #
        self.gc.old_objects = linked_list
        #
        self.running = -1
        #debug_print("collection_running = -1")

    # -------------------------
    # CollectorThread: Weakrefs

    def deal_with_weakrefs(self):
        self.running = 3; return
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
        self.collector.running = 3
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
