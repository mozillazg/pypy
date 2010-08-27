
import time

from pypy.rpython.lltypesystem import lltype, llmemory, llarena, llgroup
from pypy.rpython.memory.gc.base import MovingGCBase, read_from_env
from pypy.rlib.debug import ll_assert, have_debug_prints
from pypy.rlib.debug import debug_print, debug_start, debug_stop
from pypy.rpython.memory.support import DEFAULT_CHUNK_SIZE
from pypy.rpython.memory.support import get_address_stack, get_address_deque
from pypy.rpython.memory.support import AddressDict
from pypy.rpython.lltypesystem.llmemory import NULL, raw_malloc_usage
from pypy.rlib.rarithmetic import ovfcheck, LONG_BIT, intmask
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rlib.objectmodel import we_are_translated
from pypy.rpython.lltypesystem import rffi
from pypy.rpython.memory.gcheader import GCHeaderBuilder

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
# This means we can reuse the same space, overwriting it as we collect.

# so the algorithm itself is performed in 3 stages (modulo weakrefs and
# finalizers):

# 1. We mark alive objects
# 2. We walk all objects and assign forward pointers in the same order,
#    also updating all references
# 3. We compact the space by moving.  We use 'arena_new_view' trick, which
#    looks like new space to tests, but compiles to the same pointer.
#    Also we use raw_memmove in case the object overlaps with its destination.

# After each collection, we bump 'next_collect_after' which is a marker
# where to start each collection.  It should be exponential (but less
# than 2) from the size occupied by objects so far.

# field optimization - we don't need forward pointer and flags at the same
# time. Instead we copy the TIDs in a list when we know how many objects are
# alive, and store the forward pointer in the old object header.

first_gcflag_bit = LONG_BIT//2
first_gcflag = 1 << first_gcflag_bit
GCFLAG_HASHTAKEN = first_gcflag << 0      # someone already asked for the hash
GCFLAG_HASHFIELD = first_gcflag << 1      # we have an extra hash field
# note that only the first 2 bits are preserved during a collection!
GCFLAG_MARKBIT   = intmask(first_gcflag << (LONG_BIT//2-1))
assert GCFLAG_MARKBIT < 0     # should be 0x80000000

GCFLAG_SAVED_HASHTAKEN = GCFLAG_HASHTAKEN >> first_gcflag_bit
GCFLAG_SAVED_HASHFIELD = GCFLAG_HASHFIELD >> first_gcflag_bit


TID_TYPE = llgroup.HALFWORD
BYTES_PER_TID = rffi.sizeof(TID_TYPE)
TID_BACKUP = rffi.CArray(TID_TYPE)


class MarkCompactGC(MovingGCBase):
    HDR = lltype.Struct('header', ('tid', lltype.Signed))
    typeid_is_in_field = 'tid'
    withhash_flag_is_in_field = 'tid', GCFLAG_HASHFIELD
    # ^^^ all prebuilt objects have GCFLAG_HASHTAKEN, but only some have
    #     GCFLAG_HASHFIELD (and then they are one word longer).
    WEAKREF_OFFSETS = rffi.CArray(lltype.Signed)

    # The default space size is 1.9375 GB, i.e. almost 2 GB, allocated as
    # a big mmap.  The process does not actually consume that space until
    # needed, of course.
    TRANSLATION_PARAMS = {'space_size': int((1 + 15.0/16)*1024*1024*1024),
                          'min_next_collect_after': 4*1024*1024}   # 4MB

    malloc_zero_filled = False
    inline_simple_malloc = True
    inline_simple_malloc_varsize = True
    total_collection_time = 0.0
    total_collection_count = 0

    def __init__(self, config, chunk_size=DEFAULT_CHUNK_SIZE, space_size=4096,
                 min_next_collect_after=128):
        MovingGCBase.__init__(self, config, chunk_size)
        self.space_size = space_size
        self.min_next_collect_after = min_next_collect_after

    def next_collection(self, used_space, num_objects_so_far, requested_size):
        used_space += BYTES_PER_TID * num_objects_so_far
        ll_assert(used_space <= self.space_size,
                  "used_space + num_objects_so_far overflow")
        try:
            next = ((used_space + requested_size) // 3) * 2
        except OverflowError:
            next = self.space_size
        if next < self.min_next_collect_after:
            next = self.min_next_collect_after
        if next > self.space_size - used_space:
            next = self.space_size - used_space
        # the value we return guarantees that used_space + next <= space_size,
        # with 'BYTES_PER_TID*num_objects_so_far' included in used_space
        return next

    def setup(self):
        envsize = max_size_from_env()
        if envsize >= 4096:
            self.space_size = envsize & ~4095

        self.next_collect_after = self.next_collection(0, 0, 0)

        self.program_start_time = time.time()
        self.space = llarena.arena_malloc(self.space_size, False)
        if not self.space:
            raise CannotAllocateGCArena
        self.free = self.space
        MovingGCBase.setup(self)
        self.objects_with_finalizers = self.AddressDeque()
        self.objects_with_weakrefs = self.AddressStack()
        self.tid_backup = lltype.nullptr(TID_BACKUP)

    def init_gc_object(self, addr, typeid16, flags=0):
        hdr = llmemory.cast_adr_to_ptr(addr, lltype.Ptr(self.HDR))
        hdr.tid = self.combine(typeid16, flags)

    def init_gc_object_immortal(self, addr, typeid16, flags=0):
        hdr = llmemory.cast_adr_to_ptr(addr, lltype.Ptr(self.HDR))
        flags |= GCFLAG_HASHTAKEN
        hdr.tid = self.combine(typeid16, flags)

    def _get_memory(self, totalsize):
        # also counts the space that will be needed during the following
        # collection to store the TID
        requested_size = raw_malloc_usage(totalsize) + BYTES_PER_TID
        self.next_collect_after -= requested_size
        if self.next_collect_after < 0:
            self.obtain_free_space(requested_size)
        result = self.free
        self.free += totalsize
        llarena.arena_reserve(result, totalsize)
        return result
    _get_memory._always_inline_ = True

    def _get_totalsize_var(self, nonvarsize, itemsize, length):
        try:
            varsize = ovfcheck(itemsize * length)
        except OverflowError:
            raise MemoryError
        totalsize = llarena.round_up_for_allocation(nonvarsize + varsize)
        if totalsize < 0:    # if wrapped around
            raise MemoryError
        return totalsize
    _get_totalsize_var._always_inline_ = True

    def _setup_object(self, result, typeid16, has_finalizer, contains_weakptr):
        size_gc_header = self.gcheaderbuilder.size_gc_header
        self.init_gc_object(result, typeid16)
        if has_finalizer:
            self.objects_with_finalizers.append(result + size_gc_header)
        if contains_weakptr:
            self.objects_with_weakrefs.append(result + size_gc_header)
        return llmemory.cast_adr_to_ptr(result+size_gc_header, llmemory.GCREF)
    _setup_object._always_inline_ = True

    def malloc_fixedsize(self, typeid16, size, can_collect,
                         has_finalizer=False, contains_weakptr=False):
        size_gc_header = self.gcheaderbuilder.size_gc_header
        totalsize = size_gc_header + size
        result = self._get_memory(totalsize)
        return self._setup_object(result, typeid16, has_finalizer,
                                  contains_weakptr)

    def malloc_fixedsize_clear(self, typeid16, size, can_collect,
                               has_finalizer=False, contains_weakptr=False):
        size_gc_header = self.gcheaderbuilder.size_gc_header
        totalsize = size_gc_header + size
        result = self._get_memory(totalsize)
        llmemory.raw_memclear(result, totalsize)
        return self._setup_object(result, typeid16, has_finalizer,
                                  contains_weakptr)

    def malloc_varsize_clear(self, typeid16, length, size, itemsize,
                             offset_to_length, can_collect):
        size_gc_header = self.gcheaderbuilder.size_gc_header
        nonvarsize = size_gc_header + size
        totalsize = self._get_totalsize_var(nonvarsize, itemsize, length)
        result = self._get_memory(totalsize)
        llmemory.raw_memclear(result, totalsize)
        (result + size_gc_header + offset_to_length).signed[0] = length
        return self._setup_object(result, typeid16, False, False)

    def obtain_free_space(self, requested_size):
        while True:
            executed_some_finalizers = self.markcompactcollect(requested_size)
            self.next_collect_after -= requested_size
            if self.next_collect_after >= 0:
                break    # ok
            else:
                if executed_some_finalizers:
                    pass   # try again to do a collection
                else:
                    raise MemoryError
    obtain_free_space._dont_inline_ = True

    def collect(self, gen=0):
        self.markcompactcollect()

    def markcompactcollect(self, requested_size=0):
        start_time = self.debug_collect_start(requested_size)
        self.debug_check_consistency()
        #
        # Mark alive objects
        #
        self.to_see = self.AddressDeque()
        self.trace_from_roots()
        self.to_see.delete()
        #
        # Prepare new views on the same memory
        #
        toaddr = llarena.arena_new_view(self.space)
        maxnum = self.space_size - (self.free - self.space)
        maxnum /= BYTES_PER_TID
        llarena.arena_reserve(self.free, llmemory.sizeof(TID_BACKUP, maxnum))
        self.tid_backup = llmemory.cast_adr_to_ptr(self.free,
                                                   lltype.Ptr(TID_BACKUP))
        #
        # Walk all objects and assign forward pointers in the same order,
        # also updating all references
        #
        #weakref_offsets = self.collect_weakref_offsets()
        finaladdr = self.update_forward_pointers(toaddr, maxnum)
        if (self.run_finalizers.non_empty() or
            self.objects_with_finalizers.non_empty()):
            self.update_run_finalizers()
        #if self.objects_with_weakrefs.non_empty():
        #    self.invalidate_weakrefs(weakref_offsets)

        self.update_objects_with_id()
        self.compact()
        #
        self.tid_backup = lltype.nullptr(TID_BACKUP)
        self.free = finaladdr
        remaining_size = (toaddr + self.space_size) - finaladdr
        llarena.arena_reset(finaladdr, remaining_size, False)
        self.next_collect_after = self.next_collection(finaladdr - toaddr,
                                                       self.num_alive_objs,
                                                       requested_size)
        #
        if not we_are_translated():
            llarena.arena_free(self.space)
            self.space = toaddr
        #
        self.debug_check_consistency()
        self.debug_collect_finish(start_time)
        if self.next_collect_after < 0:
            raise MemoryError
        #
        if self.run_finalizers.non_empty():
            self.execute_finalizers()
            return True      # executed some finalizers
        else:
            return False     # no finalizer executed

    def collect_weakref_offsets(self):
        xxx
        weakrefs = self.objects_with_weakrefs
        new_weakrefs = self.AddressStack()
        weakref_offsets = lltype.malloc(self.WEAKREF_OFFSETS,
                                        weakrefs.length(), flavor='raw')
        i = 0
        while weakrefs.non_empty():
            obj = weakrefs.pop()
            offset = self.weakpointer_offset(self.get_type_id(obj))
            weakref_offsets[i] = offset
            new_weakrefs.append(obj)
            i += 1
        self.objects_with_weakrefs = new_weakrefs
        weakrefs.delete()
        return weakref_offsets

    def debug_collect_start(self, requested_size):
        if have_debug_prints():
            debug_start("gc-collect")
            debug_print()
            debug_print(".----------- Full collection -------------------")
            debug_print("| requested size:",
                        requested_size)
            start_time = time.time()
            return start_time
        return -1

    def debug_collect_finish(self, start_time):
        if start_time != -1:
            end_time = time.time()
            elapsed_time = end_time - start_time
            self.total_collection_time += elapsed_time
            self.total_collection_count += 1
            total_program_time = end_time - self.program_start_time
            ct = self.total_collection_time
            cc = self.total_collection_count
            debug_print("| number of collections so far       ", 
                        cc)
            debug_print("| total space size                   ", 
                        self.space_size)
            debug_print("| number of objects alive            ", 
                        self.num_alive_objs)
            debug_print("| used space size                    ", 
                        self.free - self.space)
            debug_print("| next collection after              ", 
                        self.next_collect_after)
            debug_print("| total collections per second:      ",
                        cc / total_program_time)
            debug_print("| total time in markcompact-collect: ",
                        ct, "seconds")
            debug_print("| percentage collection<->total time:",
                        ct * 100.0 / total_program_time, "%")
            debug_print("`----------------------------------------------")
            debug_stop("gc-collect")


    def update_run_finalizers(self):
        if self.run_finalizers.non_empty():     # uncommon case
            run_finalizers = self.AddressDeque()
            while self.run_finalizers.non_empty():
                obj = self.run_finalizers.popleft()
                run_finalizers.append(self.get_forwarding_address(obj))
            self.run_finalizers.delete()
            self.run_finalizers = run_finalizers
        #
        objects_with_finalizers = self.AddressDeque()
        while self.objects_with_finalizers.non_empty():
            obj = self.objects_with_finalizers.popleft()
            objects_with_finalizers.append(self.get_forwarding_address(obj))
        self.objects_with_finalizers.delete()
        self.objects_with_finalizers = objects_with_finalizers

    def header(self, addr):
        # like header(), but asserts that we have a normal header
        hdr = MovingGCBase.header(self, addr)
        if not we_are_translated():
            assert isinstance(hdr.tid, llgroup.CombinedSymbolic)
        return hdr

    def header_forwarded(self, addr):
        # like header(), but asserts that we have a forwarding header
        hdr = MovingGCBase.header(self, addr)
        if not we_are_translated():
            assert isinstance(hdr.tid, int)
        return hdr

    def combine(self, typeid16, flags):
        return llop.combine_ushort(lltype.Signed, typeid16, flags)

    def get_type_id(self, addr):
        tid = self.header(addr).tid
        return llop.extract_ushort(llgroup.HALFWORD, tid)

    def trace_from_roots(self):
        self.root_walker.walk_roots(
            MarkCompactGC._mark_root,  # stack roots
            MarkCompactGC._mark_root,  # static in prebuilt non-gc structures
            MarkCompactGC._mark_root)  # static in prebuilt gc objects
        if (self.objects_with_finalizers.non_empty() or
            self.run_finalizers.non_empty()):
            self.trace_from_objects_with_finalizers()
        self._trace_and_mark()

    def _trace_and_mark(self):
        while self.to_see.non_empty():
            obj = self.to_see.popleft()
            self.trace(obj, self._mark_obj, None)

    def _mark_obj(self, pointer, ignored):
        self.mark(pointer.address[0])

    def _mark_root(self, root):
        self.mark(root.address[0])

    def mark(self, obj):
        if not self.marked(obj):
            self.header(obj).tid |= GCFLAG_MARKBIT
            self.to_see.append(obj)

    def marked(self, obj):
        # should work both if tid contains a CombinedSymbolic (for dying
        # objects, at this point), or a plain integer.
        return MovingGCBase.header(self, obj).tid & GCFLAG_MARKBIT

    def update_forward_pointers(self, toaddr, maxnum):
        self.base_forwarding_addr = base_forwarding_addr = toaddr
        fromaddr = self.space
        size_gc_header = self.gcheaderbuilder.size_gc_header
        num = 0
        while fromaddr < self.free:
            hdr = llmemory.cast_adr_to_ptr(fromaddr, lltype.Ptr(self.HDR))
            obj = fromaddr + size_gc_header
            # compute the original object size, including the
            # optional hash field
            totalsrcsize = size_gc_header + self.get_size(obj)
            if hdr.tid & GCFLAG_HASHFIELD:  # already a hash field, copy it too
                totalsrcsize += llmemory.sizeof(lltype.Signed)
            #
            if self.marked(obj):
                # the object is marked as suriving.  Compute the new object
                # size
                totaldstsize = totalsrcsize
                if (hdr.tid & (GCFLAG_HASHTAKEN|GCFLAG_HASHFIELD) ==
                               GCFLAG_HASHTAKEN):
                    # grow a new hash field -- with the exception: if
                    # the object actually doesn't move, don't
                    # (otherwise, we get a bogus toaddr > fromaddr)
                    if toaddr - base_forwarding_addr < fromaddr - self.space:
                        totaldstsize += llmemory.sizeof(lltype.Signed)
                llarena.arena_reserve(toaddr, totaldstsize)
                #
                # save the field hdr.tid in the array tid_backup
                ll_assert(num < maxnum, "overflow of the tid_backup table")
                self.tid_backup[num] = self.get_type_id(obj)
                num += 1
                # compute forward_offset, the offset to the future copy
                # of this object
                forward_offset = toaddr - base_forwarding_addr
                # copy the first two gc flags in forward_offset
                ll_assert(forward_offset & 3 == 0, "misalignment!")
                forward_offset |= (hdr.tid >> first_gcflag_bit) & 3
                hdr.tid = forward_offset | GCFLAG_MARKBIT
                ll_assert(self.marked(obj), "re-marking object failed!")
                # done
                toaddr += totaldstsize
            #
            fromaddr += totalsrcsize
            if not we_are_translated():
                assert toaddr - base_forwarding_addr <= fromaddr - self.space
        self.num_alive_objs = num

        # now update references
        self.root_walker.walk_roots(
            MarkCompactGC._update_ref,  # stack roots
            MarkCompactGC._update_ref,  # static in prebuilt non-gc structures
            MarkCompactGC._update_ref)  # static in prebuilt gc objects
        self.walk_marked_objects(MarkCompactGC.trace_and_update_ref)
        return toaddr

    def walk_marked_objects(self, callback):
        num = 0
        size_gc_header = self.gcheaderbuilder.size_gc_header
        fromaddr = self.space
        toaddr = self.base_forwarding_addr
        while fromaddr < self.free:
            hdr = llmemory.cast_adr_to_ptr(fromaddr, lltype.Ptr(self.HDR))
            obj = fromaddr + size_gc_header
            survives = self.marked(obj)
            if survives:
                typeid = self.get_typeid_from_backup(num)
                num += 1
            else:
                typeid = self.get_type_id(obj)
            baseobjsize = self._get_size_for_typeid(obj, typeid)
            totalsrcsize = size_gc_header + baseobjsize
            #
            if survives:
                grow_hash_field = False
                if hdr.tid & GCFLAG_SAVED_HASHFIELD:
                    totalsrcsize += llmemory.sizeof(lltype.Signed)
                totaldstsize = totalsrcsize
                if (hdr.tid & (GCFLAG_SAVED_HASHTAKEN|GCFLAG_SAVED_HASHFIELD)
                            == GCFLAG_SAVED_HASHTAKEN):
                    if toaddr - base_forwarding_addr < fromaddr - self.space:
                        grow_hash_field = True
                        totaldstsize += llmemory.sizeof(lltype.Signed)
                callback(self, obj, typeid, totalsrcsize,
                         toaddr, grow_hash_field)
                toaddr += totaldstsize
            else:
                if hdr.tid & GCFLAG_HASHFIELD:
                    totalsrcsize += llmemory.sizeof(lltype.Signed)
            #
            fromaddr += totalsrcsize
    walk_marked_objects._annspecialcase_ = 'specialize:arg(2)'

    def trace_and_update_ref(self, obj, typeid, _1, _2, _3):
        """Enumerate the locations inside the given obj that can contain
        GC pointers.  For each such location, callback(pointer, arg) is
        called, where 'pointer' is an address inside the object.
        Typically, 'callback' is a bound method and 'arg' can be None.
        """
        if self.is_gcarrayofgcptr(typeid):
            # a performance shortcut for GcArray(gcptr)
            length = (obj + llmemory.gcarrayofptr_lengthoffset).signed[0]
            item = obj + llmemory.gcarrayofptr_itemsoffset
            while length > 0:
                self._update_ref(item)
                item += llmemory.gcarrayofptr_singleitemoffset
                length -= 1
            return
        offsets = self.offsets_to_gc_pointers(typeid)
        i = 0
        while i < len(offsets):
            item = obj + offsets[i]
            self._update_ref(item)
            i += 1
        if self.has_gcptr_in_varsize(typeid):
            item = obj + self.varsize_offset_to_variable_part(typeid)
            length = (obj + self.varsize_offset_to_length(typeid)).signed[0]
            offsets = self.varsize_offsets_to_gcpointers_in_var_part(typeid)
            itemlength = self.varsize_item_sizes(typeid)
            while length > 0:
                j = 0
                while j < len(offsets):
                    itemobj = item + offsets[j]
                    self._update_ref(itemobj)
                    j += 1
                item += itemlength
                length -= 1

    def _update_ref(self, pointer):
        if self.points_to_valid_gc_object(pointer):
            pointer.address[0] = self.get_forwarding_address(
                pointer.address[0])

    def _is_external(self, obj):
        return not (self.space <= obj < self.free)

    def get_forwarding_address(self, obj):
        if self._is_external(obj):
            return obj
        return self.get_header_forwarded_addr(obj)

    def get_header_forwarded_addr(self, obj):
        GCFLAG_MASK = ~(GCFLAG_MARKBIT | 3)
        return (self.base_forwarding_addr +
                (self.header_forwarded(obj).tid & GCFLAG_MASK) +
                self.gcheaderbuilder.size_gc_header)

    def surviving(self, obj):
        return self._is_external(obj) or self.header_forwarded(obj).tid != -1

    def get_typeid_from_backup(self, num):
        return self.tid_backup[num]

    def compact(self):
        self.walk_marked_objects(MarkCompactGC.copy_and_compact)

    def copy_and_compact(self, obj, typeid, totalsrcsize,
                         toaddr, grow_hash_field):
        # restore the normal header
        hdr = self.header_forwarded(obj)
        gcflags = hdr.tid & 3
        if grow_hash_field:
            gcflags |= GCFLAG_SAVED_HASHFIELD
            save_hash_field_now
        hdr.tid = self.combine(typeid, gcflags << first_gcflag_bit)
        #
        fromaddr = obj - self.gcheaderbuilder.size_gc_header
        if we_are_translated():
            llmemory.raw_memmove(fromaddr, toaddr, totalsrcsize)
        else:
            llmemory.raw_memcopy(fromaddr, toaddr, totalsrcsize)

    def debug_check_object(self, obj):
        # not sure what to check here
        pass

    def trace_from_objects_with_finalizers(self):
        if self.run_finalizers.non_empty():   # uncommon case
            new_run_finalizers = self.AddressDeque()
            while self.run_finalizers.non_empty():
                x = self.run_finalizers.popleft()
                self.mark(x)
                new_run_finalizers.append(x)
            self.run_finalizers.delete()
            self.run_finalizers = new_run_finalizers
        #
        # xxx we get to run the finalizers in a random order
        self._trace_and_mark()
        new_with_finalizers = self.AddressDeque()
        while self.objects_with_finalizers.non_empty():
            x = self.objects_with_finalizers.popleft()
            if self.marked(x):
                new_with_finalizers.append(x)
            else:
                self.run_finalizers.append(x)
                self.mark(x)
                self._trace_and_mark()
        self.objects_with_finalizers.delete()
        self.objects_with_finalizers = new_with_finalizers

    def invalidate_weakrefs(self, weakref_offsets):
        # walk over list of objects that contain weakrefs
        # if the object it references survives then update the weakref
        # otherwise invalidate the weakref
        xxx
        new_with_weakref = self.AddressStack()
        i = 0
        while self.objects_with_weakrefs.non_empty():
            obj = self.objects_with_weakrefs.pop()
            if not self.surviving(obj):
                continue # weakref itself dies
            newobj = self.get_forwarding_address(obj)
            offset = weakref_offsets[i]
            pointing_to = (obj + offset).address[0]
            # XXX I think that pointing_to cannot be NULL here
            if pointing_to:
                if self.surviving(pointing_to):
                    (obj + offset).address[0] = self.get_forwarding_address(
                        pointing_to)
                    new_with_weakref.append(newobj)
                else:
                    (obj + offset).address[0] = NULL
            i += 1
        self.objects_with_weakrefs.delete()
        self.objects_with_weakrefs = new_with_weakref
        lltype.free(weakref_offsets, flavor='raw')

    def identityhash(self, gcobj):
        # Unlike SemiSpaceGC.identityhash(), this function does not have
        # to care about reducing top_of_space.  The reason is as
        # follows.  When we collect, each object either moves to the
        # left or stays where it is.  If it moves to the left (and if it
        # has GCFLAG_HASHTAKEN), we can give it a hash field, and the
        # end of the new object cannot move to the right of the end of
        # the old object.  If it stays where it is, then we don't need
        # to add the hash field.  So collecting can never actually grow
        # the consumed size.
        obj = llmemory.cast_ptr_to_adr(gcobj)
        hdr = self.header(obj)
        #
        if hdr.tid & GCFLAG_HASHFIELD:  # the hash is in a field at the end
            obj += self.get_size(obj)
            return obj.signed[0]
        #
        hdr.tid |= GCFLAG_HASHTAKEN
        if we_are_translated():
            return llmemory.cast_adr_to_int(obj)  # direct case
        else:
            try:
                adr = llarena.getfakearenaaddress(obj)   # -> arena address
            except RuntimeError:
                return llmemory.cast_adr_to_int(obj)  # not in an arena...
            return adr - self.space

# ____________________________________________________________

class CannotAllocateGCArena(Exception):
    pass

def max_size_from_env():
    return read_from_env('PYPY_MARKCOMPACTGC_MAX')
