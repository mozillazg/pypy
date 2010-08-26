
import time

from pypy.rpython.lltypesystem import lltype, llmemory, llarena, llgroup
from pypy.rpython.memory.gc.base import MovingGCBase, read_from_env
from pypy.rlib.debug import ll_assert, have_debug_prints
from pypy.rlib.debug import debug_print, debug_start, debug_stop
from pypy.rpython.memory.support import DEFAULT_CHUNK_SIZE
from pypy.rpython.memory.support import get_address_stack, get_address_deque
from pypy.rpython.memory.support import AddressDict
from pypy.rpython.lltypesystem.llmemory import NULL, raw_malloc_usage
from pypy.rlib.rarithmetic import ovfcheck, LONG_BIT
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
GCFLAG_MARKBIT   = first_gcflag << 2
# note that only the first 2 bits are preserved during a collection!


TID_TYPE = llgroup.HALFWORD
BYTES_PER_TID = rffi.sizeof(TID_TYPE)
TID_BACKUP = lltype.FixedSizeArray(TID_TYPE, 1)


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
    TRANSLATION_PARAMS = {'space_size': int((1 + 15.0/16)*1024*1024*1024)}

    malloc_zero_filled = False
    inline_simple_malloc = True
    inline_simple_malloc_varsize = True
    total_collection_time = 0.0
    total_collection_count = 0

    def __init__(self, config, chunk_size=DEFAULT_CHUNK_SIZE, space_size=4096):
        MovingGCBase.__init__(self, config, chunk_size)
        self.space_size = space_size

    def setup(self):
        envsize = max_size_from_env()
        if envsize >= 4096:
            self.space_size = envsize & ~4095

        self.next_collect_after = min(self.space_size,
                                      4*1024*1024)    # 4MB initially

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
        totalsize = self._get_totalsize_var(nonvarsize, itemize, length)
        result = self._get_memory(totalsize)
        llmemory.raw_memclear(result, totalsize)
        (result + size_gc_header + offset_to_length).signed[0] = length
        return self._setup_object(result, typeid16, False, False)

    def obtain_free_space(self, requested_size):
        self.markcompactcollect()
        self.next_collect_after -= requested_size
        if self.next_collect_after < 0:
            raise MemoryError
    obtain_free_space._dont_inline_ = True

    def collect(self, gen=0):
        self.markcompactcollect()

    def markcompactcollect(self):
        start_time = self.debug_collect_start()
        self.debug_check_consistency()
        #
        # Mark alive objects
        #
        self.to_see = self.AddressDeque()
        self.trace_from_roots()
        #if (self.objects_with_finalizers.non_empty() or
        #    self.run_finalizers.non_empty()):
        #    self.mark_objects_with_finalizers()
        #    self._trace_and_mark()
        self.to_see.delete()
        #
        # Prepare new views on the same memory
        #
        toaddr = llarena.arena_new_view(self.space)
        llarena.arena_reserve(self.free, self.space_size - self.free)
        self.tid_backup = llmemory.cast_adr_to_ptr(
            self.free,
            lltype.Ptr(self.TID_BACKUP))
        #
        # Walk all objects and assign forward pointers in the same order,
        # also updating all references
        #
        self.next_collect_after = self.space_size
        #weakref_offsets = self.collect_weakref_offsets()
        finaladdr = self.update_forward_pointers(toaddr)
        if (self.run_finalizers.non_empty() or
            self.objects_with_finalizers.non_empty()):
            self.update_run_finalizers()
        if self.objects_with_weakrefs.non_empty():
            self.invalidate_weakrefs(weakref_offsets)
        self.update_objects_with_id()
        self.compact(resizing)
        if not resizing:
            size = toaddr + self.space_size - finaladdr
            llarena.arena_reset(finaladdr, size, True)
        else:
            if 1:  # XXX? we_are_translated():
                # because we free stuff already in raw_memmove, we
                # would get double free here. Let's free it anyway
                llarena.arena_free(self.space)
            llarena.arena_reset(toaddr + size_of_alive_objs, tid_backup_size,
                                True)
        self.space        = toaddr
        self.free         = finaladdr
        self.top_of_space = toaddr + self.next_collect_after
        self.debug_check_consistency()
        self.tid_backup = lltype.nullptr(self.TID_BACKUP)
        if self.run_finalizers.non_empty():
            self.execute_finalizers()
        self.debug_collect_finish(start_time)
        
    def collect_weakref_offsets(self):
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

    def debug_collect_start(self):
        if have_debug_prints():
            debug_start("gc-collect")
            debug_print()
            debug_print(".----------- Full collection ------------------")
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
            debug_print("| total collections per second:      ",
                        cc / total_program_time)
            debug_print("| total time in markcompact-collect: ",
                        ct, "seconds")
            debug_print("| percentage collection<->total time:",
                        ct * 100.0 / total_program_time, "%")
            debug_print("`----------------------------------------------")
            debug_stop("gc-collect")


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
        self._trace_and_mark()

    def _trace_and_mark(self):
        while self.to_see.non_empty():
            obj = self.to_see.popleft()
            self.trace(obj, self._mark_obj, None)

    def _mark_obj(self, pointer, ignored):
        obj = pointer.address[0]
        if self.marked(obj):
            return
        self.mark(obj)
        self.to_see.append(obj)

    def _mark_root(self, root):
        self.mark(root.address[0])
        self.to_see.append(root.address[0])

    def mark(self, obj):
        self.header(obj).tid |= GCFLAG_MARKBIT

    def marked(self, obj):
        return self.header(obj).tid & GCFLAG_MARKBIT

    def update_forward_pointers(self, toaddr):
        base_forwarding_addr = toaddr
        fromaddr = self.space
        size_gc_header = self.gcheaderbuilder.size_gc_header
        p_tid_backup = self.tid_backup
        while fromaddr < self.free:
            hdr = llmemory.cast_adr_to_ptr(fromaddr, lltype.Ptr(self.HDR))
            obj = fromaddr + size_gc_header
            # compute the original and the new object size, including the
            # optional hash field
            baseobjsize = self.get_size(obj)
            totalsrcsize = size_gc_header + baseobjsize
            if hdr.tid & GCFLAG_HASHFIELD:  # already a hash field, copy it too
                totalsrcsize += llmemory.sizeof(lltype.Signed)
                totaldstsize = totalsrcsize
            elif hdr.tid & GCFLAG_HASHTAKEN:
                # grow a new hash field -- with the exception: if the object
                # actually doesn't move, don't (otherwise, toaddr > fromaddr)
                if toaddr < fromaddr:
                    totaldstsize += llmemory.sizeof(lltype.Signed)
            #
            if not self.marked(obj):
                hdr.tid = -1     # mark the object as dying
            else:
                llarena.arena_reserve(toaddr, totalsize)
                # save the field hdr.tid in the array tid_backup
                p_tid_backup[0] = self.get_type_id(obj)
                p_tid_backup = lltype.direct_ptradd(p_tid_backup, 1)
                # compute forward_offset, the offset to the future copy
                # of this object
                forward_offset = toaddr - base_forwarding_addr
                # copy the first two gc flags in forward_offset
                ll_assert(forward_offset & 3 == 0, "misalignment!")
                forward_offset |= (hdr.tid >> first_gcflag_bit) & 3
                hdr.tid = forward_offset
                # done
                toaddr += totaldstsize
            fromaddr += totalsrcsize
            if not we_are_translated():
                assert toaddr <= fromaddr

        # now update references
        self.root_walker.walk_roots(
            MarkCompactGC._update_root,  # stack roots
            MarkCompactGC._update_root,  # static in prebuilt non-gc structures
            MarkCompactGC._update_root)  # static in prebuilt gc objects
        fromaddr = self.space
        i = 0
        while fromaddr < self.free:
            hdr = llmemory.cast_adr_to_ptr(fromaddr, lltype.Ptr(self.HDR))
            obj = fromaddr + size_gc_header
            objsize = self.get_size_from_backup(obj, i)
            totalsize = size_gc_header + objsize
            if not self.surviving(obj):
                pass
            else:
                self.trace_with_backup(obj, self._update_ref, i)
            fromaddr += totalsize
            i += 1
        return toaddr

    def trace_with_backup(self, obj, callback, arg):
        """Enumerate the locations inside the given obj that can contain
        GC pointers.  For each such location, callback(pointer, arg) is
        called, where 'pointer' is an address inside the object.
        Typically, 'callback' is a bound method and 'arg' can be None.
        """
        typeid = self.get_typeid_from_backup(arg)
        if self.is_gcarrayofgcptr(typeid):
            # a performance shortcut for GcArray(gcptr)
            length = (obj + llmemory.gcarrayofptr_lengthoffset).signed[0]
            item = obj + llmemory.gcarrayofptr_itemsoffset
            while length > 0:
                if self.points_to_valid_gc_object(item):
                    callback(item, arg)
                item += llmemory.gcarrayofptr_singleitemoffset
                length -= 1
            return
        offsets = self.offsets_to_gc_pointers(typeid)
        i = 0
        while i < len(offsets):
            item = obj + offsets[i]
            if self.points_to_valid_gc_object(item):
                callback(item, arg)
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
                    if self.points_to_valid_gc_object(itemobj):
                        callback(itemobj, arg)
                    j += 1
                item += itemlength
                length -= 1
    trace_with_backup._annspecialcase_ = 'specialize:arg(2)'

    def _update_root(self, pointer):
        if pointer.address[0] != NULL:
            pointer.address[0] = self.get_forwarding_address(pointer.address[0])

    def _update_ref(self, pointer, ignore):
        if pointer.address[0] != NULL:
            pointer.address[0] = self.get_forwarding_address(pointer.address[0])

    def _is_external(self, obj):
        return not (self.space <= obj < self.top_of_space)

    def get_forwarding_address(self, obj):
        if self._is_external(obj):
            return obj
        return self.get_header_forwarded_addr(obj)

    def set_null_forwarding_address(self, obj, num):
        hdr = self.header(obj)
        hdr.tid = -1          # make the object forwarded to NULL

    def restore_normal_header(self, obj, num):
        # Reverse of set_forwarding_address().
        typeid16 = self.get_typeid_from_backup(num)
        hdr = self.header_forwarded(obj)
        hdr.tid = self.combine(typeid16, 0)      # restore the normal header

    def get_header_forwarded_addr(self, obj):
        return (self.base_forwarding_addr +
                self.header_forwarded(obj).tid +
                self.gcheaderbuilder.size_gc_header)

    def surviving(self, obj):
        return self._is_external(obj) or self.header_forwarded(obj).tid != -1

    def get_typeid_from_backup(self, num):
        return self.tid_backup[num]

    def get_size_from_backup(self, obj, num):
        # does not count the hash field, if any
        typeid = self.get_typeid_from_backup(num)
        size = self.fixed_size(typeid)
        if self.is_varsize(typeid):
            lenaddr = obj + self.varsize_offset_to_length(typeid)
            length = lenaddr.signed[0]
            size += length * self.varsize_item_sizes(typeid)
            size = llarena.round_up_for_allocation(size)
        return size

    def compact(self, resizing):
        fromaddr = self.space
        size_gc_header = self.gcheaderbuilder.size_gc_header
        start = fromaddr
        end = fromaddr
        num = 0
        while fromaddr < self.free:
            obj = fromaddr + size_gc_header
            objsize = self.get_size_from_backup(obj, num)
            totalsize = size_gc_header + objsize
            if not self.surviving(obj): 
                # this object dies. Following line is a noop in C,
                # we clear it to make debugging easier
                llarena.arena_reset(fromaddr, totalsize, False)
            else:
                if resizing:
                    end = fromaddr
                forward_obj = self.get_header_forwarded_addr(obj)
                self.restore_normal_header(obj, num)
                if obj != forward_obj:
                    #llop.debug_print(lltype.Void, "Copying from to",
                    #                 fromaddr, forward_ptr, totalsize)
                    llmemory.raw_memmove(fromaddr,
                                         forward_obj - size_gc_header,
                                         totalsize)
                if resizing and end - start > GC_CLEARANCE:
                    diff = end - start
                    #llop.debug_print(lltype.Void, "Cleaning", start, diff)
                    diff = (diff / GC_CLEARANCE) * GC_CLEARANCE
                    #llop.debug_print(lltype.Void, "Cleaning", start, diff)
                    end = start + diff
                    if we_are_translated():
                        # XXX wuaaaaa.... those objects are freed incorrectly
                        #                 here in case of test_gc
                        llarena.arena_reset(start, diff, True)
                    start += diff
            num += 1
            fromaddr += totalsize

    def debug_check_object(self, obj):
        # not sure what to check here
        pass

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

    def invalidate_weakrefs(self, weakref_offsets):
        # walk over list of objects that contain weakrefs
        # if the object it references survives then update the weakref
        # otherwise invalidate the weakref
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

    def get_size_incl_hash(self, obj):
        size = self.get_size(obj)
        hdr = self.header(obj)
        if hdr.tid & GCFLAG_HASHFIELD:
            size += llmemory.sizeof(lltype.Signed)
        return size

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
        return llmemory.cast_adr_to_int(obj)  # direct case

# ____________________________________________________________

class CannotAllocateGCArena(Exception):
    pass

def max_size_from_env():
    return read_from_env('PYPY_MARKCOMPACTGC_MAX')
