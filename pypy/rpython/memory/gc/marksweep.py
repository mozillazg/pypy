from pypy.rpython.lltypesystem.llmemory import raw_malloc, raw_free
from pypy.rpython.lltypesystem.llmemory import raw_memcopy, raw_memclear
from pypy.rpython.lltypesystem.llmemory import NULL, raw_malloc_usage
from pypy.rpython.memory.support import DEFAULT_CHUNK_SIZE, RTTIPTR
from pypy.rpython.memory.support import get_address_stack
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rlib.objectmodel import free_non_gc_object
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rlib.rarithmetic import ovfcheck
from pypy.rlib.debug import ll_assert
from pypy.rpython.memory.gc.base import GCBase


import sys, os

X_POOL = lltype.GcOpaqueType('gc.pool')
X_POOL_PTR = lltype.Ptr(X_POOL)
X_CLONE = lltype.GcStruct('CloneData', ('gcobjectptr', llmemory.GCREF),
                                       ('pool',        X_POOL_PTR))
X_CLONE_PTR = lltype.Ptr(X_CLONE)

def ll_getnext(hdr):
    "Return the 'next' header by reading the 'next_and_flags' fields"
    next = hdr.next_and_flags & ~1
    return llmemory.cast_adr_to_ptr(next, MarkSweepGC.HDRPTR)

def ll_setnext_clear(hdr, next):
    hdr.next_and_flags = llmemory.cast_ptr_to_adr(next)

def ll_ismarked(hdr):
    return (llmemory.cast_adr_to_int(hdr.next_and_flags) & 1) != 0

def ll_setmark(hdr):
    hdr.next_and_flags |= 1

def ll_clearmark(hdr):
    hdr.next_and_flags &= ~1


DEBUG_PRINT = False
memoryError = MemoryError()
class MarkSweepGC(GCBase):
    _alloc_flavor_ = "raw"

    HDR = lltype.ForwardReference()
    HDRPTR = lltype.Ptr(HDR)
    # need to maintain a linked list of malloced objects, since we used the
    # systems allocator and can't walk the heap
    HDR.become(lltype.Struct('header', ('typeptr', RTTIPTR),
                                       ('next_and_flags', llmemory.Address),
                             adtmeths={'getnext': ll_getnext,
                                       'setnext_clear': ll_setnext_clear,
                                       'ismarked': ll_ismarked,
                                       'setmark': ll_setmark,
                                       'clearmark': ll_clearmark}))

    POOL = lltype.GcStruct('gc_pool')
    POOLPTR = lltype.Ptr(POOL)

    POOLNODE = lltype.ForwardReference()
    POOLNODEPTR = lltype.Ptr(POOLNODE)
    POOLNODE.become(lltype.Struct('gc_pool_node', ('linkedlisthdr', HDR),
                                                  ('nextnode', POOLNODEPTR)))

    def __init__(self, chunk_size=DEFAULT_CHUNK_SIZE, start_heap_size=4096):
        GCBase.__init__(self)
        self.heap_usage = 0          # at the end of the latest collection
        self.bytes_malloced = 0      # since the latest collection
        self.bytes_malloced_threshold = start_heap_size
        self.total_collection_time = 0.0
        self.AddressStack = get_address_stack(chunk_size)
        self.malloced_objects = lltype.nullptr(self.HDR)
        self.malloced_objects_with_finalizer = lltype.nullptr(self.HDR)
        # these are usually only the small bits of memory that make a
        # weakref object
        self.objects_with_weak_pointers = lltype.nullptr(self.HDR)
        # pools, for x_swap_pool():
        #   'curpool' is the current pool, lazily allocated (i.e. NULL means
        #   the current POOL object is not yet malloc'ed).  POOL objects are
        #   usually at the start of a linked list of objects, via the HDRs.
        #   The exception is 'curpool' whose linked list of objects is in
        #   'self.malloced_objects' instead of in the header of 'curpool'.
        #   POOL objects are never in the middle of a linked list themselves.
        # XXX a likely cause for the current problems with pools is:
        # not all objects live in malloced_objects, some also live in
        # malloced_objects_with_finalizer and objects_with_weak_pointers
        self.curpool = lltype.nullptr(self.POOL)
        #   'poolnodes' is a linked list of all such linked lists.  Each
        #   linked list will usually start with a POOL object, but it can
        #   also contain only normal objects if the POOL object at the head
        #   was already freed.  The objects in 'malloced_objects' are not
        #   found via 'poolnodes'.
        self.poolnodes = lltype.nullptr(self.POOLNODE)
        self.collect_in_progress = False
        self.prev_collect_end_time = 0.0

    def maybe_collect(self):
        if self.bytes_malloced > self.bytes_malloced_threshold:
            self.collect()

    def write_malloc_statistics(self, typeid, size, result, varsize):
        pass

    def write_free_statistics(self, typeid, result):
        pass

    def malloc_fixedsize(self, typeid, size, can_collect, has_finalizer=False,
                         contains_weakptr=False):
        if can_collect:
            self.maybe_collect()
        size_gc_header = self.gcheaderbuilder.size_gc_header
        try:
            tot_size = size_gc_header + size
            usage = raw_malloc_usage(tot_size)
            bytes_malloced = ovfcheck(self.bytes_malloced+usage)
            ovfcheck(self.heap_usage + bytes_malloced)
        except OverflowError:
            raise memoryError
        result = raw_malloc(tot_size)
        if not result:
            raise memoryError
        hdr = llmemory.cast_adr_to_ptr(result, self.HDRPTR)
        hdr.typeptr = typeid
        if has_finalizer:
            hdr.setnext_clear(self.malloced_objects_with_finalizer)
            self.malloced_objects_with_finalizer = hdr
        elif contains_weakptr:
            hdr.setnext_clear(self.objects_with_weak_pointers)
            self.objects_with_weak_pointers = hdr
        else:
            hdr.setnext_clear(self.malloced_objects)
            self.malloced_objects = hdr
        self.bytes_malloced = bytes_malloced
        result += size_gc_header
        #llop.debug_print(lltype.Void, 'malloc typeid', typeid,
        #                 '->', llmemory.cast_adr_to_int(result))
        self.write_malloc_statistics(typeid, tot_size, result, False)
        return llmemory.cast_adr_to_ptr(result, llmemory.GCREF)
    malloc_fixedsize._dont_inline_ = True

    def malloc_fixedsize_clear(self, typeid, size, can_collect,
                               has_finalizer=False, contains_weakptr=False):
        if can_collect:
            self.maybe_collect()
        size_gc_header = self.gcheaderbuilder.size_gc_header
        try:
            tot_size = size_gc_header + size
            usage = raw_malloc_usage(tot_size)
            bytes_malloced = ovfcheck(self.bytes_malloced+usage)
            ovfcheck(self.heap_usage + bytes_malloced)
        except OverflowError:
            raise memoryError
        result = raw_malloc(tot_size)
        if not result:
            raise memoryError
        raw_memclear(result, tot_size)
        hdr = llmemory.cast_adr_to_ptr(result, self.HDRPTR)
        hdr.typeptr = typeid
        if has_finalizer:
            hdr.setnext_clear(self.malloced_objects_with_finalizer)
            self.malloced_objects_with_finalizer = hdr
        elif contains_weakptr:
            hdr.setnext_clear(self.objects_with_weak_pointers)
            self.objects_with_weak_pointers = hdr
        else:
            hdr.setnext_clear(self.malloced_objects)
            self.malloced_objects = hdr
        self.bytes_malloced = bytes_malloced
        result += size_gc_header
        #llop.debug_print(lltype.Void, 'malloc typeid', typeid,
        #                 '->', llmemory.cast_adr_to_int(result))
        self.write_malloc_statistics(typeid, tot_size, result, False)
        return llmemory.cast_adr_to_ptr(result, llmemory.GCREF)
    malloc_fixedsize_clear._dont_inline_ = True

    def malloc_varsize(self, typeid, length, size, itemsize, offset_to_length,
                       can_collect, has_finalizer=False):
        if can_collect:
            self.maybe_collect()
        size_gc_header = self.gcheaderbuilder.size_gc_header
        try:
            fixsize = size_gc_header + size
            varsize = ovfcheck(itemsize * length)
            tot_size = ovfcheck(fixsize + varsize)
            usage = raw_malloc_usage(tot_size)
            bytes_malloced = ovfcheck(self.bytes_malloced+usage)
            ovfcheck(self.heap_usage + bytes_malloced)
        except OverflowError:
            raise memoryError
        result = raw_malloc(tot_size)
        if not result:
            raise memoryError
        (result + size_gc_header + offset_to_length).signed[0] = length
        hdr = llmemory.cast_adr_to_ptr(result, self.HDRPTR)
        hdr.typeptr = typeid
        if has_finalizer:
            hdr.setnext_clear(self.malloced_objects_with_finalizer)
            self.malloced_objects_with_finalizer = hdr
        else:
            hdr.setnext_clear(self.malloced_objects)
            self.malloced_objects = hdr
        self.bytes_malloced = bytes_malloced
            
        result += size_gc_header
        #llop.debug_print(lltype.Void, 'malloc_varsize length', length,
        #                 'typeid', typeid,
        #                 '->', llmemory.cast_adr_to_int(result))
        self.write_malloc_statistics(typeid, tot_size, result, True)
        return llmemory.cast_adr_to_ptr(result, llmemory.GCREF)
    malloc_varsize._dont_inline_ = True

    def malloc_varsize_clear(self, typeid, length, size, itemsize,
                             offset_to_length, can_collect,
                             has_finalizer=False):
        if can_collect:
            self.maybe_collect()
        size_gc_header = self.gcheaderbuilder.size_gc_header
        try:
            fixsize = size_gc_header + size
            varsize = ovfcheck(itemsize * length)
            tot_size = ovfcheck(fixsize + varsize)
            usage = raw_malloc_usage(tot_size)
            bytes_malloced = ovfcheck(self.bytes_malloced+usage)
            ovfcheck(self.heap_usage + bytes_malloced)
        except OverflowError:
            raise memoryError
        result = raw_malloc(tot_size)
        if not result:
            raise memoryError
        raw_memclear(result, tot_size)        
        (result + size_gc_header + offset_to_length).signed[0] = length
        hdr = llmemory.cast_adr_to_ptr(result, self.HDRPTR)
        hdr.typeptr = typeid
        if has_finalizer:
            hdr.setnext_clear(self.malloced_objects_with_finalizer)
            self.malloced_objects_with_finalizer = hdr
        else:
            hdr.setnext_clear(self.malloced_objects)
            self.malloced_objects = hdr
        self.bytes_malloced = bytes_malloced
            
        result += size_gc_header
        #llop.debug_print(lltype.Void, 'malloc_varsize length', length,
        #                 'typeid', typeid,
        #                 '->', llmemory.cast_adr_to_int(result))
        self.write_malloc_statistics(typeid, tot_size, result, True)
        return llmemory.cast_adr_to_ptr(result, llmemory.GCREF)
    malloc_varsize_clear._dont_inline_ = True

    def collect(self):
        # 1. mark from the roots, and also the objects that objects-with-del
        #    point to (using the list of malloced_objects_with_finalizer)
        # 2. walk the list of objects-without-del and free the ones not marked
        # 3. walk the list of objects-with-del and for the ones not marked:
        #    call __del__, move the object to the list of object-without-del
        import time
        from pypy.rpython.lltypesystem.lloperation import llop
        if DEBUG_PRINT:
            llop.debug_print(lltype.Void, 'collecting...')
        start_time = time.time()
        self.collect_in_progress = True
        size_gc_header = self.gcheaderbuilder.size_gc_header
##        llop.debug_view(lltype.Void, self.malloced_objects, self.poolnodes,
##                        size_gc_header)

        # push the roots on the mark stack
        objects = self.AddressStack() # mark stack
        self._mark_stack = objects
        self.root_walker.walk_roots(
            MarkSweepGC._mark_root,  # stack roots
            MarkSweepGC._mark_root,  # static in prebuilt non-gc structures
            MarkSweepGC._mark_root)  # static in prebuilt gc objects

        # from this point onwards, no more mallocs should be possible
        old_malloced = self.bytes_malloced
        self.bytes_malloced = 0
        curr_heap_size = 0
        freed_size = 0

        # mark objects reachable by objects with a finalizer, but not those
        # themselves. add their size to curr_heap_size, since they always
        # survive the collection
        hdr = self.malloced_objects_with_finalizer
        while hdr:
            gc_info = llmemory.cast_ptr_to_adr(hdr)
            obj = gc_info + size_gc_header
            if not hdr.ismarked():
                self.add_reachable_to_stack(obj, objects)
            addr = llmemory.cast_ptr_to_adr(hdr)
            typeid = hdr.typeptr
            size = self.fixed_size(typeid)
            if self.is_varsize(typeid):
                length = (obj + self.varsize_offset_to_length(typeid)).signed[0]
                size += self.varsize_item_sizes(typeid) * length
            estimate = raw_malloc_usage(size_gc_header + size)
            curr_heap_size += estimate
            hdr = hdr.getnext()

        # mark thinks on the mark stack and put their descendants onto the
        # stack until the stack is empty
        while objects.non_empty():  #mark
            curr = objects.pop()
            gc_info = curr - size_gc_header
            hdr = llmemory.cast_adr_to_ptr(gc_info, self.HDRPTR)
            if hdr.ismarked():
                continue
            self.add_reachable_to_stack(curr, objects)
            hdr.setmark()
        objects.delete()
        # also mark self.curpool
        if self.curpool:
            gc_info = llmemory.cast_ptr_to_adr(self.curpool) - size_gc_header
            hdr = llmemory.cast_adr_to_ptr(gc_info, self.HDRPTR)
            hdr.setmark()
        # go through the list of objects containing weak pointers
        # and kill the links if they go to dead objects
        # if the object itself is not marked, free it
        hdr = self.objects_with_weak_pointers
        surviving = lltype.nullptr(self.HDR)
        while hdr:
            typeid = hdr.typeptr
            next = hdr.getnext()
            addr = llmemory.cast_ptr_to_adr(hdr)
            size = self.fixed_size(typeid)
            estimate = raw_malloc_usage(size_gc_header + size)
            if hdr.ismarked():
                offset = self.weakpointer_offset(typeid)
                gc_info = llmemory.cast_ptr_to_adr(hdr)
                weakref_obj = gc_info + size_gc_header
                pointing_to = (weakref_obj + offset).address[0]
                if pointing_to:
                    gc_info_pointing_to = pointing_to - size_gc_header
                    hdr_pointing_to = llmemory.cast_adr_to_ptr(
                        gc_info_pointing_to, self.HDRPTR)
                    # pointed to object will die
                    # XXX what to do if the object has a finalizer which resurrects
                    # the object?
                    if not hdr_pointing_to.ismarked():
                        (weakref_obj + offset).address[0] = NULL
                hdr.setnext_clear(surviving)     # this also clears the mark
                surviving = hdr
                curr_heap_size += estimate
            else:
                gc_info = llmemory.cast_ptr_to_adr(hdr)
                weakref_obj = gc_info + size_gc_header
                self.write_free_statistics(typeid, weakref_obj)
                freed_size += estimate
                raw_free(addr)
            hdr = next
        self.objects_with_weak_pointers = surviving
        # sweep: delete objects without del if they are not marked
        # unmark objects without del that are marked
        firstpoolnode = lltype.malloc(self.POOLNODE, flavor='raw')
        firstpoolnode.linkedlisthdr.setnext_clear(self.malloced_objects)
        firstpoolnode.nextnode = self.poolnodes
        prevpoolnode = lltype.nullptr(self.POOLNODE)
        poolnode = firstpoolnode
        while poolnode:   #sweep
            previous = poolnode.linkedlisthdr
            hdr = previous.getnext()
            while hdr:  #sweep
                typeid = hdr.typeptr
                next = hdr.getnext()
                addr = llmemory.cast_ptr_to_adr(hdr)
                size = self.fixed_size(typeid)
                if self.is_varsize(typeid):
                    length = (addr + size_gc_header + self.varsize_offset_to_length(typeid)).signed[0]
                    size += self.varsize_item_sizes(typeid) * length
                estimate = raw_malloc_usage(size_gc_header + size)
                if hdr.ismarked():
                    # hdr.clearmark() -- done automatically by the
                    # call to setnext_clear() that will follow
                    previous.setnext_clear(hdr)
                    previous = hdr
                    curr_heap_size += estimate
                else:
                    gc_info = llmemory.cast_ptr_to_adr(hdr)
                    obj = gc_info + size_gc_header
                    self.write_free_statistics(typeid, obj)
                    freed_size += estimate
                    raw_free(addr)
                hdr = next
            previous.setnext_clear(lltype.nullptr(self.HDR))
            next = poolnode.nextnode
            if not poolnode.linkedlisthdr.getnext() and prevpoolnode:
                # completely empty node
                prevpoolnode.nextnode = next
                lltype.free(poolnode, flavor='raw')
            else:
                prevpoolnode = poolnode
            poolnode = next
        self.malloced_objects = firstpoolnode.linkedlisthdr.getnext()
        self.poolnodes = firstpoolnode.nextnode
        lltype.free(firstpoolnode, flavor='raw')
        #llop.debug_view(lltype.Void, self.malloced_objects, self.malloced_objects_with_finalizer, size_gc_header)

        end_time = time.time()
        compute_time = start_time - self.prev_collect_end_time
        collect_time = end_time - start_time

        garbage_collected = old_malloced - (curr_heap_size - self.heap_usage)

        if (collect_time * curr_heap_size >
            0.02 * garbage_collected * compute_time): 
            self.bytes_malloced_threshold += self.bytes_malloced_threshold / 2
        if (collect_time * curr_heap_size <
            0.005 * garbage_collected * compute_time):
            self.bytes_malloced_threshold /= 2

        # Use atleast as much memory as current live objects.
        if curr_heap_size > self.bytes_malloced_threshold:
            self.bytes_malloced_threshold = curr_heap_size

        # Cap at 1/4 GB
        self.bytes_malloced_threshold = min(self.bytes_malloced_threshold,
                                            256 * 1024 * 1024)
        self.total_collection_time += collect_time
        self.prev_collect_end_time = end_time
        if DEBUG_PRINT:
            llop.debug_print(lltype.Void,
                             "  malloced since previous collection:",
                             old_malloced, "bytes")
            llop.debug_print(lltype.Void,
                             "  heap usage at start of collection: ",
                             self.heap_usage + old_malloced, "bytes")
            llop.debug_print(lltype.Void,
                             "  freed:                             ",
                             freed_size, "bytes")
            llop.debug_print(lltype.Void,
                             "  new heap usage:                    ",
                             curr_heap_size, "bytes")
            llop.debug_print(lltype.Void,
                             "  total time spent collecting:       ",
                             self.total_collection_time, "seconds")
            llop.debug_print(lltype.Void,
                             "  collecting time:                   ",
                             collect_time)
            llop.debug_print(lltype.Void,
                             "  computing time:                    ",
                             collect_time)
            llop.debug_print(lltype.Void,
                             "  new threshold:                     ",
                             self.bytes_malloced_threshold)
##        llop.debug_view(lltype.Void, self.malloced_objects, self.poolnodes,
##                        size_gc_header)
        assert self.heap_usage + old_malloced == curr_heap_size + freed_size

        self.heap_usage = curr_heap_size
        hdr = self.malloced_objects_with_finalizer
        self.malloced_objects_with_finalizer = lltype.nullptr(self.HDR)
        last = lltype.nullptr(self.HDR)
        while hdr:
            next = hdr.getnext()
            if hdr.ismarked():
                hdr.setnext_clear(lltype.nullptr(self.HDR))  # also clears mark
                if not self.malloced_objects_with_finalizer:
                    self.malloced_objects_with_finalizer = hdr
                else:
                    last.setnext_clear(hdr)
                last = hdr
            else:
                obj = llmemory.cast_ptr_to_adr(hdr) + size_gc_header
                finalizer = self.getfinalizer(hdr.typeptr)
                # make malloced_objects_with_finalizer consistent
                # for the sake of a possible collection caused by finalizer
                if not self.malloced_objects_with_finalizer:
                    self.malloced_objects_with_finalizer = next
                else:
                    last.setnext_clear(next)
                hdr.setnext_clear(self.malloced_objects)
                self.malloced_objects = hdr
                #llop.debug_view(lltype.Void, self.malloced_objects, self.malloced_objects_with_finalizer, size_gc_header)
                finalizer(obj)
                if not self.collect_in_progress: # another collection was caused?
                    llop.debug_print(lltype.Void, "outer collect interrupted "
                                                  "by recursive collect")
                    return
                if not last:
                    if self.malloced_objects_with_finalizer == next:
                        self.malloced_objects_with_finalizer = lltype.nullptr(self.HDR)
                    else:
                        # now it gets annoying: finalizer caused a malloc of something
                        # with a finalizer
                        last = self.malloced_objects_with_finalizer
                        while last.getnext() != next:
                            last = last.getnext()
                            last.setnext_clear(lltype.nullptr(self.HDR))
                else:
                    last.setnext_clear(lltype.nullptr(self.HDR))
            hdr = next
        self.collect_in_progress = False

    def _mark_root(self, root):   # 'root' is the address of the GCPTR
        gcobjectaddr = root.address[0]
        self._mark_stack.append(gcobjectaddr)

    def _mark_root_and_clear_bit(self, root):
        gcobjectaddr = root.address[0]
        self._mark_stack.append(gcobjectaddr)
        size_gc_header = self.gcheaderbuilder.size_gc_header
        gc_info = gcobjectaddr - size_gc_header
        hdr = llmemory.cast_adr_to_ptr(gc_info, self.HDRPTR)
        hdr.clearmark()

    STAT_HEAP_USAGE     = 0
    STAT_BYTES_MALLOCED = 1
    STATISTICS_NUMBERS  = 2

    def get_type_id(self, obj):
        size_gc_header = self.gcheaderbuilder.size_gc_header
        gc_info = obj - size_gc_header
        hdr = llmemory.cast_adr_to_ptr(gc_info, self.HDRPTR)
        return hdr.typeptr

    def add_reachable_to_stack(self, obj, objects):
        self.trace(obj, self._add_reachable, objects)

    def _add_reachable(pointer, objects):
        obj = pointer.address[0]
        if obj:
            objects.append(obj)
    _add_reachable = staticmethod(_add_reachable)

    def statistics(self, index):
        # no memory allocation here!
        if index == self.STAT_HEAP_USAGE:
            return self.heap_usage
        if index == self.STAT_BYTES_MALLOCED:
            return self.bytes_malloced
        return -1

    def init_gc_object_immortal(self, hdr, typeid):
        # prebuilt gc structures always have the mark bit set
        hdr.typeptr = typeid
        hdr.setmark()

    # experimental support for thread cloning
    def x_swap_pool(self, newpool):
        # Set newpool as the current pool (create one if newpool == NULL).
        # All malloc'ed objects are put into the current pool;this is a
        # way to separate objects depending on when they were allocated.
        size_gc_header = self.gcheaderbuilder.size_gc_header
        # invariant: each POOL GcStruct is at the _front_ of a linked list
        # of malloced objects.
        oldpool = self.curpool
        #llop.debug_print(lltype.Void, 'x_swap_pool',
        #                 lltype.cast_ptr_to_int(oldpool),
        #                 lltype.cast_ptr_to_int(newpool))
        if not oldpool:
            # make a fresh pool object, which is automatically inserted at the
            # front of the current list
            oldpool = lltype.malloc(self.POOL)
            addr = llmemory.cast_ptr_to_adr(oldpool)
            addr -= size_gc_header
            hdr = llmemory.cast_adr_to_ptr(addr, self.HDRPTR)
            # put this new POOL object in the poolnodes list
            node = lltype.malloc(self.POOLNODE, flavor="raw")
            node.linkedlisthdr.setnext_clear(hdr)
            node.nextnode = self.poolnodes
            self.poolnodes = node
        else:
            # manually insert oldpool at the front of the current list
            addr = llmemory.cast_ptr_to_adr(oldpool)
            addr -= size_gc_header
            hdr = llmemory.cast_adr_to_ptr(addr, self.HDRPTR)
            hdr.setnext_clear(self.malloced_objects)

        newpool = lltype.cast_opaque_ptr(self.POOLPTR, newpool)
        if newpool:
            # newpool is at the front of the new linked list to install
            addr = llmemory.cast_ptr_to_adr(newpool)
            addr -= size_gc_header
            hdr = llmemory.cast_adr_to_ptr(addr, self.HDRPTR)
            self.malloced_objects = hdr.getnext()
            # invariant: now that objects in the hdr.next list are accessible
            # through self.malloced_objects, make sure they are not accessible
            # via poolnodes (which has a node pointing to newpool):
            hdr.setnext_clear(lltype.nullptr(self.HDR))
        else:
            # start a fresh new linked list
            self.malloced_objects = lltype.nullptr(self.HDR)
        self.curpool = newpool
        return lltype.cast_opaque_ptr(X_POOL_PTR, oldpool)

    def x_clone(self, clonedata):
        # Recursively clone the gcobject and everything it points to,
        # directly or indirectly -- but stops at objects that are not
        # in the specified pool.  A new pool is built to contain the
        # copies, and the 'gcobjectptr' and 'pool' fields of clonedata
        # are adjusted to refer to the result.

        # install a new pool into which all the mallocs go
        curpool = self.x_swap_pool(lltype.nullptr(X_POOL))

        size_gc_header = self.gcheaderbuilder.size_gc_header
        oldobjects = self.AddressStack()
        # if no pool specified, use the current pool as the 'source' pool
        oldpool = clonedata.pool or curpool
        oldpool = lltype.cast_opaque_ptr(self.POOLPTR, oldpool)
        addr = llmemory.cast_ptr_to_adr(oldpool)
        addr -= size_gc_header

        hdr = llmemory.cast_adr_to_ptr(addr, self.HDRPTR)
        hdr = hdr.getnext()   # skip the POOL object itself
        while hdr:
            next = hdr.getnext()
            # 'hdr.next' is abused to point to the copy
            ll_assert(not hdr.ismarked(), "x_clone: object already marked")
            hdr.setnext_clear(lltype.nullptr(self.HDR))
            hdr.setmark()      # mark all objects from malloced_list
            oldobjects.append(llmemory.cast_ptr_to_adr(hdr))
            hdr = next

        # a stack of addresses of places that still points to old objects
        # and that must possibly be fixed to point to a new copy
        stack = self.AddressStack()
        stack.append(llmemory.cast_ptr_to_adr(clonedata)
                     + llmemory.offsetof(X_CLONE, 'gcobjectptr'))
        while stack.non_empty():
            gcptr_addr = stack.pop()
            oldobj_addr = gcptr_addr.address[0]
            if not oldobj_addr:
                continue   # pointer is NULL
            oldhdr = llmemory.cast_adr_to_ptr(oldobj_addr - size_gc_header,
                                              self.HDRPTR)
            if not oldhdr.ismarked():
                continue   # ignore objects that were not in the malloced_list
            newhdr = oldhdr.getnext()      # abused to point to the copy
            if not newhdr:
                typeid = hdr.typeptr
                size = self.fixed_size(typeid)
                # XXX! collect() at the beginning if the free heap is low
                if self.is_varsize(typeid):
                    itemsize = self.varsize_item_sizes(typeid)
                    offset_to_length = self.varsize_offset_to_length(typeid)
                    length = (oldobj_addr + offset_to_length).signed[0]
                    newobj = self.malloc_varsize(typeid, length, size,
                                                 itemsize, offset_to_length,
                                                 False)
                    size += length*itemsize
                else:
                    newobj = self.malloc_fixedsize(typeid, size, False)
                    length = -1

                newobj_addr = llmemory.cast_ptr_to_adr(newobj)

                #llop.debug_print(lltype.Void, 'clone',
                #                 llmemory.cast_adr_to_int(oldobj_addr),
                #                 '->', llmemory.cast_adr_to_int(newobj_addr),
                #                 'typeid', typeid,
                #                 'length', length)

                newhdr_addr = newobj_addr - size_gc_header
                newhdr = llmemory.cast_adr_to_ptr(newhdr_addr, self.HDRPTR)

                saved_tid  = newhdr.typeptr        # XXX hack needed for genc
                saved_next = newhdr.next_and_flags # where size_gc_header == 0
                raw_memcopy(oldobj_addr, newobj_addr, size)
                newhdr.typeptr = saved_tid
                newhdr.next_and_flags = saved_next

                offsets = self.offsets_to_gc_pointers(typeid)
                i = 0
                while i < len(offsets):
                    pointer_addr = newobj_addr + offsets[i]
                    stack.append(pointer_addr)
                    i += 1

                if length > 0:
                    offsets = self.varsize_offsets_to_gcpointers_in_var_part(
                        typeid)
                    itemlength = self.varsize_item_sizes(typeid)
                    offset = self.varsize_offset_to_variable_part(typeid)
                    itembaseaddr = newobj_addr + offset
                    i = 0
                    while i < length:
                        item = itembaseaddr + itemlength * i
                        j = 0
                        while j < len(offsets):
                            pointer_addr = item + offsets[j]
                            stack.append(pointer_addr)
                            j += 1
                        i += 1

                oldhdr.setnext_clear(newhdr)
                oldhdr.setmark()
            newobj_addr = llmemory.cast_ptr_to_adr(newhdr) + size_gc_header
            gcptr_addr.address[0] = newobj_addr
        stack.delete()

        # re-create the original linked list
        next = lltype.nullptr(self.HDR)
        while oldobjects.non_empty():
            hdr = llmemory.cast_adr_to_ptr(oldobjects.pop(), self.HDRPTR)
            hdr.setnext_clear(next)       # this also resets the mark
            next = hdr
        oldobjects.delete()

        # consistency check
        addr = llmemory.cast_ptr_to_adr(oldpool)
        addr -= size_gc_header
        hdr = llmemory.cast_adr_to_ptr(addr, self.HDRPTR)
        ll_assert(hdr.getnext() == next, "bad .next at the end of x_clone")

        # build the new pool object collecting the new objects, and
        # reinstall the pool that was current at the beginning of x_clone()
        clonedata.pool = self.x_swap_pool(curpool)


class PrintingMarkSweepGC(MarkSweepGC):
    _alloc_flavor_ = "raw"
    COLLECT_EVERY = 2000

    def __init__(self, chunk_size=DEFAULT_CHUNK_SIZE, start_heap_size=4096):
        MarkSweepGC.__init__(self, chunk_size, start_heap_size)
        self.count_mallocs = 0

    def maybe_collect(self):
        self.count_mallocs += 1
        if self.count_mallocs > self.COLLECT_EVERY:
            self.collect()

    def write_malloc_statistics(self, typeid, size, result, varsize):
        if varsize:
            what = "malloc_varsize"
        else:
            what = "malloc"
        llop.debug_print(lltype.Void, what, typeid, " ", size, " ", result)

    def write_free_statistics(self, typeid, result):
        llop.debug_print(lltype.Void, "free", typeid, " ", result)

    def collect(self):
        self.count_mallocs = 0
        MarkSweepGC.collect(self)
