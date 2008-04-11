import sys
from pypy.rpython.memory.gc.semispace import SemiSpaceGC
from pypy.rpython.memory.gc.generation import GenerationGC
from pypy.rpython.lltypesystem import llmemory, llarena
from pypy.rpython.lltypesystem.llmemory import raw_malloc_usage
from pypy.rlib.debug import ll_assert
from pypy.rlib.rarithmetic import ovfcheck

GCFLAG_MARK = GenerationGC.first_unused_gcflag << 0


class HybridGC(GenerationGC):
    """A two-generations semi-space GC like the GenerationGC,
    except that objects above a certain size are handled separately:
    they are allocated via raw_malloc/raw_free in a mark-n-sweep fashion.
    """
    first_unused_gcflag = GenerationGC.first_unused_gcflag << 1

    def __init__(self, *args, **kwds):
        large_object = kwds.pop('large_object', 32)
        GenerationGC.__init__(self, *args, **kwds)

        # Objects whose total size is at least 'large_object' bytes are
        # allocated separately in a mark-n-sweep fashion.  In this
        # class, we assume that the 'large_object' limit is not very high,
        # so that all objects that wouldn't easily fit in the nursery
        # are considered large by this limit.  This is the meaning of
        # the 'assert' below.
        self.nonlarge_max = large_object - 1
        assert self.nonlarge_max <= self.lb_young_var_basesize
        self.large_objects_collect_trigger = self.space_size

    def setup(self):
        self.large_objects_list = self.AddressDeque()
        GenerationGC.setup(self)

    # NB. to simplify the code, only varsized objects can be considered
    # 'large'.

    def malloc_varsize_clear(self, typeid, length, size, itemsize,
                             offset_to_length, can_collect,
                             has_finalizer=False):
        if has_finalizer or not can_collect:
            return SemiSpaceGC.malloc_varsize_clear(self, typeid, length, size,
                                                    itemsize, offset_to_length,
                                                    can_collect, has_finalizer)
        size_gc_header = self.gcheaderbuilder.size_gc_header
        nonvarsize = size_gc_header + size

        # Compute the maximal length that makes the object still
        # below 'nonlarge_max'.  All the following logic is usually
        # constant-folded because self.nonlarge_max, size and itemsize
        # are all constants (the arguments are constant due to
        # inlining).
        if not raw_malloc_usage(itemsize):
            too_many_items = raw_malloc_usage(nonvarsize) > self.nonlarge_max
        else:
            maxlength = self.nonlarge_max - raw_malloc_usage(nonvarsize)
            maxlength = maxlength // raw_malloc_usage(itemsize)
            too_many_items = length > maxlength

        if not too_many_items:
            # With the above checks we know now that totalsize cannot be more
            # than 'nonlarge_max'; in particular, the + and * cannot overflow.
            # Let's try to fit the object in the nursery.
            totalsize = nonvarsize + itemsize * length
            result = self.nursery_free
            if raw_malloc_usage(totalsize) <= self.nursery_top - result:
                llarena.arena_reserve(result, totalsize)
                # GCFLAG_NO_YOUNG_PTRS is never set on young objs
                self.init_gc_object(result, typeid, flags=0)
                (result + size_gc_header + offset_to_length).signed[0] = length
                self.nursery_free = result + llarena.round_up_for_allocation(
                    totalsize)
                return llmemory.cast_adr_to_ptr(result+size_gc_header,
                                                llmemory.GCREF)
        return self.malloc_varsize_slowpath(typeid, length)

    def malloc_varsize_slowpath(self, typeid, length):
        # For objects that are too large, or when the nursery is exhausted.
        # In order to keep malloc_varsize_clear() as compact as possible,
        # we recompute what we need in this slow path instead of passing
        # it all as function arguments.
        size_gc_header = self.gcheaderbuilder.size_gc_header
        nonvarsize = size_gc_header + self.fixed_size(typeid)
        itemsize = self.varsize_item_sizes(typeid)
        offset_to_length = self.varsize_offset_to_length(typeid)
        try:
            varsize = ovfcheck(itemsize * length)
            totalsize = ovfcheck(nonvarsize + varsize)
        except OverflowError:
            raise MemoryError()
        if raw_malloc_usage(totalsize) > self.nonlarge_max:
            result = self.malloc_varsize_marknsweep(totalsize)
            flags = self.GCFLAGS_FOR_NEW_EXTERNAL_OBJECTS
        else:
            result = self.malloc_varsize_collecting_nursery(totalsize)
            flags = self.GCFLAGS_FOR_NEW_YOUNG_OBJECTS
        self.init_gc_object(result, typeid, flags)
        (result + size_gc_header + offset_to_length).signed[0] = length
        return llmemory.cast_adr_to_ptr(result+size_gc_header, llmemory.GCREF)

    malloc_varsize_slowpath._dont_inline_ = True

    def malloc_varsize_collecting_nursery(self, totalsize):
        result = self.collect_nursery()
        ll_assert(raw_malloc_usage(totalsize) <= self.nursery_top - result,
                  "not enough room in malloc_varsize_collecting_nursery()")
        llarena.arena_reserve(result, totalsize)
        self.nursery_free = result + llarena.round_up_for_allocation(
            totalsize)
        return result

    def malloc_varsize_marknsweep(self, totalsize):
        # In order to free the large objects from time to time, we
        # arbitrarily force a full collect() if none occurs when we have
        # allocated 'self.space_size' bytes of large objects.
        self.large_objects_collect_trigger -= raw_malloc_usage(totalsize)
        if self.large_objects_collect_trigger < 0:
            self.semispace_collect()
        # XXX maybe we should use llarena.arena_malloc above a certain size?
        result = llmemory.raw_malloc(totalsize)
        if not result:
            raise MemoryError()
        # The parent classes guarantee zero-filled allocations, so we
        # need to follow suit.
        llmemory.raw_memclear(result, totalsize)
        size_gc_header = self.gcheaderbuilder.size_gc_header
        self.large_objects_list.append(result + size_gc_header)
        return result

    # the following methods are hook into SemiSpaceGC.semispace_collect()

    def starting_full_collect(self):
        # This hook is not really necessary but it's a nice place
        # to put the following comment:
        # No object should have a GCFLAG_MARK at this point
        # (except some prebuilt objects but they are ignored).
        pass

    def visit_external_object(self, obj):
        # leave a GCFLAG_MARK on all external objects visited (some
        # prebuilt objects will also get the flag, but it doesn't matter)
        self.header(obj).tid |= GCFLAG_MARK

    def finished_full_collect(self):
        # free all mark-n-sweep-managed objects that have not been marked
        large_objects = self.large_objects_list
        remaining_large_objects = self.AddressDeque()
        while large_objects.non_empty():
            obj = large_objects.popleft()
            if self.header(obj).tid & GCFLAG_MARK:
                self.header(obj).tid -= GCFLAG_MARK
                remaining_large_objects.append(obj)
            else:
                addr = obj - self.gcheaderbuilder.size_gc_header
                llmemory.raw_free(addr)
        large_objects.delete()
        self.large_objects_list = remaining_large_objects
        # As we just collected, it's fine to raw_malloc'ate up to space_size
        # bytes again before we should force another collect.
        self.large_objects_collect_trigger = self.space_size
