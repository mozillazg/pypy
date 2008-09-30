
from pypy.rpython.lltypesystem import lltype, llmemory, llarena
from pypy.rpython.memory.gc.base import MovingGCBase, \
     TYPEID_MASK, GCFLAG_FINALIZATION_ORDERING, GCFLAG_EXTERNAL
from pypy.rlib.debug import ll_assert
from pypy.rpython.memory.support import DEFAULT_CHUNK_SIZE
from pypy.rpython.memory.support import get_address_stack, get_address_deque
from pypy.rpython.memory.support import AddressDict
from pypy.rpython.lltypesystem.llmemory import NULL, raw_malloc_usage
from pypy.rlib.rarithmetic import ovfcheck
from pypy.rpython.lltypesystem.lloperation import llop

GCFLAG_MARKBIT = MovingGCBase.first_unused_gcflag

memoryError = MemoryError()

# Mark'n'compact garbage collector
#
# main point of this GC is to save as much memory as possible
# (not to be worse than semispace), but avoid having peaks of
# memory during collection. Inspired, at least partly by squeak's
# garbage collector

# so, the idea as now is:

# we allocate space (full of zeroes) which is big enough to handle
# all possible cases. Because it's full of zeroes, we never allocate
# it really, unless we start using it

# for each collection we mark objects which are alive, also marking all
# for which we want to run finalizers. we mark them by storing forward
# pointer, which will be a place to copy them. After that, we copy all
# using memmove to another view of the same space, hence compacting
# everything

# before compacting, we update forward references to pointers

class MarkCompactGC(MovingGCBase):
    HDR = lltype.Struct('header', ('tid', lltype.Signed),
                        ('forward_ptr', llmemory.Address))

    # XXX probably we need infinite (ie 4G) amount of memory here
    # and we'll keep all pages shared. The question is what we do
    # with tests which create all llarenas

    TRANSLATION_PARAMS = {'space_size': 16*1024*1024} # XXX adjust

    def __init__(self, chunk_size=DEFAULT_CHUNK_SIZE, space_size=16*(1024**2)):
        # space_size should be maximal available virtual memory.
        # this way we'll never need to copy anything nor implement
        # paging on our own
        self.space_size = space_size
        MovingGCBase.__init__(self, chunk_size)
        self.counter = 0

    def setup(self):
        self.space = llarena.arena_malloc(self.space_size, True)
        ll_assert(bool(self.space), "couldn't allocate arena")
        self.spaceptr = self.space
        self.toaddr = self.space
        MovingGCBase.setup(self)
        self.finalizers_to_run = self.AddressDeque()

    def init_gc_object(self, addr, typeid, flags=0):
        hdr = llmemory.cast_adr_to_ptr(addr, lltype.Ptr(self.HDR))
        hdr.tid = typeid | flags
        hdr.forward_ptr = NULL

    def malloc_fixedsize_clear(self, typeid, size, can_collect,
                               has_finalizer=False, contains_weakptr=False):
        assert can_collect
        size_gc_header = self.gcheaderbuilder.size_gc_header
        totalsize = size_gc_header + size
        self.eventually_collect()
        result = self.spaceptr
        llarena.arena_reserve(result, totalsize)
        self.init_gc_object(result, typeid)
        self.spaceptr += totalsize
        if has_finalizer:
            self.objects_with_finalizers.append(result + size_gc_header)
        if contains_weakptr:
            self.objects_with_weakrefs.append(result + size_gc_header)
        return llmemory.cast_adr_to_ptr(result+size_gc_header, llmemory.GCREF)
    
    def malloc_varsize_clear(self, typeid, length, size, itemsize,
                             offset_to_length, can_collect,
                             has_finalizer=False):
        assert can_collect
        size_gc_header = self.gcheaderbuilder.size_gc_header
        nonvarsize = size_gc_header + size
        try:
            varsize = ovfcheck(itemsize * length)
            totalsize = ovfcheck(nonvarsize + varsize)
        except OverflowError:
            raise memoryError
        self.eventually_collect()
        result = self.spaceptr
        llarena.arena_reserve(result, totalsize)
        self.init_gc_object(result, typeid)
        (result + size_gc_header + offset_to_length).signed[0] = length
        self.spaceptr = result + llarena.round_up_for_allocation(totalsize)
        if has_finalizer:
            self.objects_with_finalizers.append(result + size_gc_header)
        return llmemory.cast_adr_to_ptr(result+size_gc_header, llmemory.GCREF)

    def eventually_collect(self):
        # XXX this is a very bad idea, come up with better heuristics
        # XXX it also does not check can_collect flag
        self.counter += 1
        if self.counter == 1000:
            self.collect()
            self.counter = 0

    def collect(self):
        self.debug_check_consistency()
        toaddr = llarena.arena_new_view(self.space)
        self.mark_roots_recursively()
        self.debug_check_consistency()
        #if self.run_finalizers.non_empty():
        #    self.update_run_finalizers()
        if self.objects_with_finalizers.non_empty():
            self.mark_objects_with_finalizers()
        if self.finalizers_to_run.non_empty():
            self.execute_finalizers()
        self.debug_check_consistency()
        finaladdr = self.update_forward_pointers(toaddr)
        if self.objects_with_weakrefs.non_empty():
            self.invalidate_weakrefs()
        self.update_objects_with_id()
        self.compact()
        self.space = toaddr
        self.spaceptr = finaladdr
        self.debug_check_consistency()

    def get_type_id(self, addr):
        return self.header(addr).tid & TYPEID_MASK

    def mark_roots_recursively(self):
        self.root_walker.walk_roots(
            MarkCompactGC._mark_root_recursively,  # stack roots
            MarkCompactGC._mark_root_recursively,  # static in prebuilt non-gc structures
            MarkCompactGC._mark_root_recursively)  # static in prebuilt gc objects

    def _mark_root_recursively(self, root):
        self.trace_and_mark(root.address[0])

    def mark(self, obj):
        self.header(obj).tid |= GCFLAG_MARKBIT

    def marked(self, obj):
        return self.header(obj).tid & GCFLAG_MARKBIT

    def trace_and_mark(self, obj):
        if self.marked(obj):
            return
        self.mark(obj)
        to_see = self.AddressStack()
        to_see.append(obj)
        while to_see.non_empty():
            obj = to_see.pop()
            self.trace(obj, self._mark_obj, to_see)
        to_see.delete()

    def _mark_obj(self, pointer, to_see):
        obj = pointer.address[0]
        if obj != NULL:
            if self.marked(obj):
                return
            self.mark(obj)
            to_see.append(obj)

    def update_forward_pointers(self, toaddr):
        fromaddr = self.space
        size_gc_header = self.gcheaderbuilder.size_gc_header
        while fromaddr < self.spaceptr:
            hdr = llmemory.cast_adr_to_ptr(fromaddr, lltype.Ptr(self.HDR))
            obj = fromaddr + size_gc_header
            objsize = self.get_size(obj)
            totalsize = size_gc_header + objsize
            if not self.marked(obj):
                pass
            else:
                llarena.arena_reserve(toaddr, totalsize)
                self.set_forwarding_address(obj, toaddr)
                toaddr += totalsize
            fromaddr += totalsize

        # now update references
        self.root_walker.walk_roots(
            MarkCompactGC._update_root,  # stack roots
            MarkCompactGC._update_root,  # static in prebuilt non-gc structures
            MarkCompactGC._update_root)  # static in prebuilt gc objects
        fromaddr = self.space
        while fromaddr < self.spaceptr:
            hdr = llmemory.cast_adr_to_ptr(fromaddr, lltype.Ptr(self.HDR))
            obj = fromaddr + size_gc_header
            objsize = self.get_size(obj)
            totalsize = size_gc_header + objsize
            if not self.marked(obj):
                pass
            else:
                self.trace(obj, self._update_ref, None)
            fromaddr += totalsize
        return toaddr

    def _update_root(self, pointer):
        if pointer.address[0] != NULL:
            pointer.address[0] = self.get_forwarding_address(pointer.address[0])

    def _update_ref(self, pointer, ignore):
        if pointer.address[0] != NULL:
            pointer.address[0] = self.get_forwarding_address(pointer.address[0])

    def is_forwarded(self, addr):
        return self.header(addr).forward_ptr != NULL

    def _is_external(self, obj):
        # XXX might change
        return self.header(obj).tid & GCFLAG_EXTERNAL

    def get_forwarding_address(self, obj):
        if self._is_external(obj):
            return obj
        else:
            return self.header(obj).forward_ptr + self.size_gc_header()

    def set_forwarding_address(self, obj, newaddr):
        self.header(obj).forward_ptr = newaddr

    def surviving(self, obj):
        return self.header(obj).forward_ptr != NULL

    def compact(self):
        fromaddr = self.space
        size_gc_header = self.gcheaderbuilder.size_gc_header
        while fromaddr < self.spaceptr:
            hdr = llmemory.cast_adr_to_ptr(fromaddr, lltype.Ptr(self.HDR))
            obj = fromaddr + size_gc_header
            objsize = self.get_size(obj)
            totalsize = size_gc_header + objsize
            if not self.surviving(obj): 
                # this object dies, clear arena                
                llarena.arena_reset(fromaddr, totalsize, True)
            else:
                ll_assert(self.is_forwarded(obj), "not forwarded, surviving obj")
                forward_ptr = hdr.forward_ptr
                hdr.forward_ptr = NULL
                hdr.tid &= ~(GCFLAG_MARKBIT&GCFLAG_FINALIZATION_ORDERING)
                #llop.debug_print(lltype.Void, fromaddr, "copied to", forward_ptr,
                #                 "\ntid", self.header(obj).tid,
                #                 "\nsize", totalsize)
                llmemory.raw_memmove(fromaddr, forward_ptr, totalsize)
                llarena.arena_reset(fromaddr, totalsize, False)
                assert llmemory.cast_adr_to_ptr(forward_ptr, lltype.Ptr(self.HDR)).tid
            fromaddr += totalsize

    def debug_check_object(self, obj):
        # not sure what to check here
        pass


    def id(self, ptr):
        obj = llmemory.cast_ptr_to_adr(ptr)
        if self.header(obj).tid & GCFLAG_EXTERNAL:
            result = self._compute_id_for_external(obj)
        else:
            result = self._compute_id(obj)
        return llmemory.cast_adr_to_int(result)

    def _next_id(self):
        # return an id not currently in use (as an address instead of an int)
        if self.id_free_list.non_empty():
            result = self.id_free_list.pop()    # reuse a dead id
        else:
            # make up a fresh id number
            result = llmemory.cast_int_to_adr(self.next_free_id)
            self.next_free_id += 2    # only odd numbers, to make lltype
                                      # and llmemory happy and to avoid
                                      # clashes with real addresses
        return result

    def _compute_id(self, obj):
        # look if the object is listed in objects_with_id
        result = self.objects_with_id.get(obj)
        if not result:
            result = self._next_id()
            self.objects_with_id.setitem(obj, result)
        return result

    def _compute_id_for_external(self, obj):
        # For prebuilt objects, we can simply return their address.
        # This method is overriden by the HybridGC.
        return obj

    def update_objects_with_id(self):
        old = self.objects_with_id
        new_objects_with_id = self.AddressDict(old.length())
        old.foreach(self._update_object_id_FAST, new_objects_with_id)
        old.delete()
        self.objects_with_id = new_objects_with_id

    def _update_object_id(self, obj, id, new_objects_with_id):
        # safe version (used by subclasses)
        if self.surviving(obj):
            newobj = self.get_forwarding_address(obj)
            new_objects_with_id.setitem(newobj, id)
        else:
            self.id_free_list.append(id)

    def _update_object_id_FAST(self, obj, id, new_objects_with_id):
        # unsafe version, assumes that the new_objects_with_id is large enough
        if self.surviving(obj):
            newobj = self.get_forwarding_address(obj)
            new_objects_with_id.insertclean(newobj, id)
        else:
            self.id_free_list.append(id)

    def _finalization_state(self, obj):
        if self.surviving(obj):
            hdr = self.header(obj)
            if hdr.tid & GCFLAG_FINALIZATION_ORDERING:
                return 2
            else:
                return 3
        else:
            hdr = self.header(obj)
            if hdr.tid & GCFLAG_FINALIZATION_ORDERING:
                return 1
            else:
                return 0

    def mark_objects_with_finalizers(self):
        new_with_finalizers = self.AddressDeque()
        finalizers_to_run = self.finalizers_to_run
        while self.objects_with_finalizers.non_empty():
            x = self.objects_with_finalizers.popleft()
            if self.marked(x):
                new_with_finalizers.append(x)
            else:
                finalizers_to_run.append(x)
                self.trace_and_mark(x)
        self.objects_with_finalizers.delete()
        self.objects_with_finalizers = new_with_finalizers

    def execute_finalizers(self):
        while self.finalizers_to_run.non_empty():
            obj = self.finalizers_to_run.popleft()
            finalizer = self.getfinalizer(self.get_type_id(obj))
            finalizer(obj)
        self.finalizers_to_run.delete()
        self.finalizers_to_run = self.AddressDeque()

    def invalidate_weakrefs(self):
        # walk over list of objects that contain weakrefs
        # if the object it references survives then update the weakref
        # otherwise invalidate the weakref
        new_with_weakref = self.AddressStack()
        while self.objects_with_weakrefs.non_empty():
            obj = self.objects_with_weakrefs.pop()
            if not self.surviving(obj):
                continue # weakref itself dies
            newobj = self.get_forwarding_address(obj)
            offset = self.weakpointer_offset(self.get_type_id(obj))
            pointing_to = (obj + offset).address[0]
            # XXX I think that pointing_to cannot be NULL here
            if pointing_to:
                if self.surviving(pointing_to):
                    (obj + offset).address[0] = self.get_forwarding_address(
                        pointing_to)
                    new_with_weakref.append(newobj)
                else:
                    (obj + offset).address[0] = NULL
        self.objects_with_weakrefs.delete()
        self.objects_with_weakrefs = new_with_weakref
