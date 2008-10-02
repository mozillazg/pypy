
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
from pypy.rlib.objectmodel import we_are_translated

GCFLAG_MARKBIT = MovingGCBase.first_unused_gcflag

memoryError = MemoryError()

# Mark'n'compact garbage collector
#
# main point of this GC is to save as much memory as possible
# (not to be worse than semispace), but avoid having peaks of
# memory during collection. Inspired, at least partly by squeak's
# garbage collector

# so, the idea as now is:

# this gc works more or less like semispace, but has some essential
# differencies. The main difference is that we have separate phases of
# marking and assigning pointers, hence order of objects is preserved.
# This means we can reuse the same space if it did not grow enough.
# More importantly, in case we need to resize space we can copy it bit by
# bit, hence avoiding double memory consumption at peak times

# so the algorithm itself is performed in 3 stages (module weakrefs and
# finalizers)

# 1. We mark alive objects
# 2. We walk all objects and assign forward pointers in the same order,
#    also updating all references
# 3. We compact the space by moving. In case we move to the same space,
#    we use arena_new_view trick, which looks like new space to tests,
#    but compiles to the same pointer. Also we use raw_memmove in case
#    objects overlap.

# in case we need to grow space, we use
# current_space_size * FREE_SPACE_MULTIPLIER / FREE_SPACE_DIVIDER + needed
FREE_SPACE_MULTIPLIER = 3
FREE_SPACE_DIVIDER = 2
FREE_SPACE_ADD = 256

class MarkCompactGC(MovingGCBase):
    HDR = lltype.Struct('header', ('tid', lltype.Signed),
                        ('forward_ptr', llmemory.Address))

    TRANSLATION_PARAMS = {'space_size': 2*1024*1024} # XXX adjust

    malloc_zero_filled = True
    inline_simple_malloc = True
    inline_simple_malloc_varsize = True

    def __init__(self, chunk_size=DEFAULT_CHUNK_SIZE, space_size=4096):
        self.space_size = space_size
        MovingGCBase.__init__(self, chunk_size)

    def setup(self):
        self.space = llarena.arena_malloc(self.space_size, True)
        ll_assert(bool(self.space), "couldn't allocate arena")
        self.free = self.space
        self.top_of_space = self.space + self.space_size
        MovingGCBase.setup(self)
        self.run_finalizers = self.AddressDeque()

    def init_gc_object(self, addr, typeid, flags=0):
        hdr = llmemory.cast_adr_to_ptr(addr, lltype.Ptr(self.HDR))
        hdr.tid = typeid | flags
        hdr.forward_ptr = NULL

    def malloc_fixedsize_clear(self, typeid, size, can_collect,
                               has_finalizer=False, contains_weakptr=False):
        assert can_collect
        size_gc_header = self.gcheaderbuilder.size_gc_header
        totalsize = size_gc_header + size
        result = self.free
        if raw_malloc_usage(totalsize) > self.top_of_space - result:
            if not can_collect:
                raise memoryError
            result = self.obtain_free_space(totalsize)
        llarena.arena_reserve(result, totalsize)
        self.init_gc_object(result, typeid)
        self.free += totalsize
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
        result = self.free
        if raw_malloc_usage(totalsize) > self.top_of_space - result:
            if not can_collect:
                raise memoryError
            result = self.obtain_free_space(totalsize)
        llarena.arena_reserve(result, totalsize)
        self.init_gc_object(result, typeid)
        (result + size_gc_header + offset_to_length).signed[0] = length
        self.free = result + llarena.round_up_for_allocation(totalsize)
        if has_finalizer:
            self.objects_with_finalizers.append(result + size_gc_header)
        return llmemory.cast_adr_to_ptr(result+size_gc_header, llmemory.GCREF)

    def obtain_free_space(self, totalsize):
        # a bit of tweaking to maximize the performance and minimize the
        # amount of code in an inlined version of malloc_fixedsize_clear()
        if not self.try_obtain_free_space(totalsize):
            raise memoryError
        return self.free
    obtain_free_space._dont_inline_ = True

    def try_obtain_free_space(self, needed):
        needed = raw_malloc_usage(needed)
        missing = needed - (self.top_of_space - self.free)
        if (self.red_zone >= 2 and self.increase_space_size(needed)):
            return True
        else:
            self.markcompactcollect()
        missing = needed - (self.top_of_space - self.free)
        if missing <= 0:
            return True      # success
        else:
            # first check if the object could possibly fit
            if not self.increase_space_size(needed):
                return False
        return True

    def new_space_size(self, incr):
        return (self.space_size * FREE_SPACE_MULTIPLIER /
                FREE_SPACE_DIVIDER + incr + FREE_SPACE_ADD)

    def increase_space_size(self, needed):
        self.red_zone = 0
        new_size = self.new_space_size(needed)
        newspace = llarena.arena_malloc(new_size, True)
        if not newspace:
            return False
        self.tospace = newspace
        self.space_size = new_size
        self.markcompactcollect(resizing=True)
        return True

    def collect(self):
        self.markcompactcollect()

    def markcompactcollect(self, resizing=False):
        self.debug_check_consistency()
        if resizing:
            toaddr = self.tospace
        else:
            toaddr = llarena.arena_new_view(self.space)
        self.to_see = self.AddressStack()
        self.mark_roots_recursively()
        if (self.objects_with_finalizers.non_empty() or
            self.run_finalizers.non_empty()):
            self.mark_objects_with_finalizers()
            self._trace_and_mark()
        self.to_see.delete()
        finaladdr = self.update_forward_pointers(toaddr)
        if (self.run_finalizers.non_empty() or
            self.objects_with_finalizers.non_empty()):
            self.update_run_finalizers()
        if self.objects_with_weakrefs.non_empty():
            self.invalidate_weakrefs()
        self.update_objects_with_id()
        self.compact(resizing)
        if not resizing:
            size = toaddr + self.space_size - finaladdr
            llarena.arena_reset(finaladdr, size, True)
        else:
            if we_are_translated():
                # because we free stuff already in raw_memmove, we
                # would get double free here. Let's free it anyway
                llarena.arena_free(self.space)
        self.space        = toaddr
        self.free         = finaladdr
        self.top_of_space = toaddr + self.space_size
        self.debug_check_consistency()
        if not resizing:
            self.record_red_zone()
        if self.run_finalizers.non_empty():
            self.execute_finalizers()

    def update_run_finalizers(self):
        run_finalizers = self.AddressDeque()
        while self.run_finalizers.non_empty():
            obj = self.run_finalizers.popleft()
            run_finalizers.append(self.get_forwarding_address(obj))
        self.run_finalizers.delete()
        self.run_finalizers = run_finalizers
        objects_with_finalizers = self.AddressDeque()
        while self.objects_with_finalizers.non_empty():
            obj = self.objects_with_finalizers.popleft()
            objects_with_finalizers.append(self.get_forwarding_address(obj))
        self.objects_with_finalizers.delete()
        self.objects_with_finalizers = objects_with_finalizers

    def get_type_id(self, addr):
        return self.header(addr).tid & TYPEID_MASK

    def mark_roots_recursively(self):
        self.root_walker.walk_roots(
            MarkCompactGC._mark_root_recursively,  # stack roots
            MarkCompactGC._mark_root_recursively,  # static in prebuilt non-gc structures
            MarkCompactGC._mark_root_recursively)  # static in prebuilt gc objects
        self._trace_and_mark()

    def _trace_and_mark(self):
        while self.to_see.non_empty():
            obj = self.to_see.pop()
            self.trace(obj, self._mark_obj, None)

    def _mark_obj(self, pointer, ignored):
        obj = pointer.address[0]
        if obj != NULL:
            if self.marked(obj):
                return
            self.mark(obj)
            self.to_see.append(obj)

    def _mark_root_recursively(self, root):
        self.mark(root.address[0])
        self.to_see.append(root.address[0])

    def mark(self, obj):
        self.header(obj).tid |= GCFLAG_MARKBIT

    def marked(self, obj):
        return self.header(obj).tid & GCFLAG_MARKBIT

    def update_forward_pointers(self, toaddr):
        fromaddr = self.space
        size_gc_header = self.gcheaderbuilder.size_gc_header
        while fromaddr < self.free:
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
        while fromaddr < self.free:
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

    def compact(self, resizing):
        fromaddr = self.space
        size_gc_header = self.gcheaderbuilder.size_gc_header
        while fromaddr < self.free:
            hdr = llmemory.cast_adr_to_ptr(fromaddr, lltype.Ptr(self.HDR))
            obj = fromaddr + size_gc_header
            objsize = self.get_size(obj)
            totalsize = size_gc_header + objsize
            if not self.surviving(obj): 
                # this object dies
                pass
            else:
                ll_assert(self.is_forwarded(obj), "not forwarded, surviving obj")
                forward_ptr = hdr.forward_ptr
                hdr.forward_ptr = NULL
                hdr.tid &= ~(GCFLAG_MARKBIT|GCFLAG_FINALIZATION_ORDERING)
                #if fromaddr != forward_ptr:
                llmemory.raw_memmove(fromaddr, forward_ptr, totalsize)
            fromaddr += totalsize

    def debug_check_object(self, obj):
        # not sure what to check here
        if not self._is_external(obj):
            ll_assert(not self.marked(obj), "Marked")
            ll_assert(not self.surviving(obj), "forward_ptr set")
        
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

    def mark_objects_with_finalizers(self):
        new_with_finalizers = self.AddressDeque()
        run_finalizers = self.run_finalizers
        new_run_finalizers = self.AddressDeque()
        while run_finalizers.non_empty():
            x = run_finalizers.popleft()
            self.mark(x)
            self.to_see.append(x)
            new_run_finalizers.append(x)
        run_finalizers.delete()
        self.run_finalizers = new_run_finalizers
        while self.objects_with_finalizers.non_empty():
            x = self.objects_with_finalizers.popleft()
            if self.marked(x):
                new_with_finalizers.append(x)
            else:
                new_run_finalizers.append(x)
                self.mark(x)
                self.to_see.append(x)
        self.objects_with_finalizers.delete()
        self.objects_with_finalizers = new_with_finalizers

    def execute_finalizers(self):
        self.finalizer_lock_count += 1
        try:
            while self.run_finalizers.non_empty():
                if self.finalizer_lock_count > 1:
                    # the outer invocation of execute_finalizers() will do it
                    break
                obj = self.run_finalizers.popleft()
                finalizer = self.getfinalizer(self.get_type_id(obj))
                finalizer(obj)
        finally:
            self.finalizer_lock_count -= 1

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
