from pypy.rpython.lltypesystem import lltype, llmemory, llarena, llgroup
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.memory.gc.base import MovingGCBase
from pypy.rpython.memory.gc import minimarkpage
from pypy.rpython.memory.support import DEFAULT_CHUNK_SIZE
from pypy.rlib.rarithmetic import ovfcheck, LONG_BIT, intmask
from pypy.rlib.debug import ll_assert, debug_print

WORD = LONG_BIT // 8

first_gcflag = 1 << (LONG_BIT//2)

# The following flag is never set on young objects, i.e. the ones living
# in the nursery.  It is initially set on all prebuilt and old objects,
# and gets cleared by the write_barrier() when we write in them a
# pointer to a young object.
GCFLAG_NO_YOUNG_PTRS = first_gcflag << 0

# The following flag is set on some prebuilt objects.  The flag is set
# unless the object is already listed in 'prebuilt_root_objects'.
# When a pointer is written inside an object with GCFLAG_NO_HEAP_PTRS
# set, the write_barrier clears the flag and adds the object to
# 'prebuilt_root_objects'.
GCFLAG_NO_HEAP_PTRS = first_gcflag << 1

# The following flag is set on surviving objects during a major collection.
GCFLAG_VISITED      = first_gcflag << 2

# The following flag is set on objects that have an extra hash field,
# except on nursery objects, where it means that it *will* grow a hash
# field when moving.
GCFLAG_HASHFIELD    = first_gcflag << 3

# Marker set to 'tid' during a minor collection when an object from
# the nursery was forwarded.
FORWARDED_MARKER = -1

# ____________________________________________________________

class MiniMarkGC(MovingGCBase):
    _alloc_flavor_ = "raw"
    inline_simple_malloc = True
    inline_simple_malloc_varsize = True
    needs_write_barrier = True
    prebuilt_gc_objects_are_static_roots = False
    malloc_zero_filled = True    # XXX experiment with False

    # All objects start with a HDR, i.e. with a field 'tid' which contains
    # a word.  This word is divided in two halves: the lower half contains
    # the typeid, and the upper half contains various flags, as defined
    # by GCFLAG_xxx above.
    HDR = lltype.Struct('header', ('tid', lltype.Signed))
    typeid_is_in_field = 'tid'
    #withhash_flag_is_in_field = 'tid', _GCFLAG_HASH_BASE * 0x2

    # During a minor collection, the objects in the nursery that are
    # moved outside are changed in-place: their header is replaced with
    # FORWARDED_MARKER, and the following word is set to the address of
    # where the object was moved.  This means that all objects in the
    # nursery need to be at least 2 words long, but objects outside the
    # nursery don't need to.
    minimal_size_in_nursery = llmemory.raw_malloc_usage(
        llmemory.sizeof(HDR) + llmemory.sizeof(llmemory.Address))


    TRANSLATION_PARAMS = {
        # The size of the nursery.  -1 means "auto", which means that it
        # will look it up in the env var PYPY_GENERATIONGC_NURSERY and
        # fall back to half the size of the L2 cache.
        "nursery_size": -1,

        # The system page size.  Like obmalloc.c, we assume that it is 4K,
        # which is OK for most systems.
        "page_size": 4096,

        # The size of an arena.  Arenas are groups of pages allocated
        # together.
        "arena_size": 65536*WORD,

        # The maximum size of an object allocated compactly.  All objects
        # that are larger or equal are just allocated with raw_malloc().
        "small_request_threshold": 32*WORD,
        }

    def __init__(self, config, chunk_size=DEFAULT_CHUNK_SIZE,
                 nursery_size=32*WORD,
                 page_size=16*WORD,
                 arena_size=64*WORD,
                 small_request_threshold=6*WORD,
                 ArenaCollectionClass=None):
        MovingGCBase.__init__(self, config, chunk_size)
        self.nursery_size = nursery_size
        self.small_request_threshold = small_request_threshold
        self.nursery_hash_base = -1
        #
        # The ArenaCollection() handles the nonmovable objects allocation.
        if ArenaCollectionClass is None:
            ArenaCollectionClass = minimarkpage.ArenaCollection
        self.ac = ArenaCollectionClass(arena_size, page_size,
                                       small_request_threshold)
        #
        # Used by minor collection: a list of non-young objects that
        # (may) contain a pointer to a young object.  Populated by
        # the write barrier.
        self.old_objects_pointing_to_young = self.AddressStack()
        #
        # A list of all prebuilt GC objects that contain pointers to the heap
        self.prebuilt_root_objects = self.AddressStack()
        #
        self._init_writebarrier_logic()


    def setup(self):
        """Called at run-time to initialize the GC."""
        MovingGCBase.setup(self)
        #
        assert self.nursery_size > 0, "XXX"
        #
        # A list of all raw_malloced objects (the objects too large)
        self.rawmalloced_objects = self.AddressStack()
        #
        # Support for id()
        self.young_objects_with_id = self.AddressDict()
        #
        # the start of the nursery: we actually allocate a tiny bit more for
        # the nursery than really needed, to simplify pointer arithmetic
        # in malloc_fixedsize_clear().
        extra = self.small_request_threshold - WORD
        self.nursery = llarena.arena_malloc(self.nursery_size + extra, True)
        if not self.nursery:
            raise MemoryError("cannot allocate nursery")
        # the current position in the nursery:
        self.nursery_next = self.nursery
        # the end of the nursery:
        self.nursery_top = self.nursery + self.nursery_size


    def malloc_fixedsize_clear(self, typeid, size, can_collect=True,
                               needs_finalizer=False, contains_weakptr=False):
        ll_assert(can_collect, "!can_collect")
        assert not needs_finalizer   # XXX
        assert not contains_weakptr  # XXX
        size_gc_header = self.gcheaderbuilder.size_gc_header
        totalsize = size_gc_header + size
        #
        # If totalsize is greater or equal than small_request_threshold,
        # ask for a rawmalloc.  The following check should be constant-folded.
        if llmemory.raw_malloc_usage(totalsize)>=self.small_request_threshold:
            result = self.external_malloc(typeid, totalsize)
            #
        else:
            # If totalsize is smaller than minimal_size_in_nursery, round it
            # up.  The following check should also be constant-folded.
            if (llmemory.raw_malloc_usage(totalsize) <
                llmemory.raw_malloc_usage(self.minimal_size_in_nursery)):
                totalsize = self.minimal_size_in_nursery
            #
            # Get the memory from the nursery.  If there is not enough space
            # there, do a collect first.
            result = self.nursery_next
            self.nursery_next = result + totalsize
            if self.nursery_next > self.nursery_top:
                result = self.collect_and_reserve(totalsize)
            #
            # Build the object.
            llarena.arena_reserve(result, totalsize)
            self.init_gc_object(result, typeid, flags=0)
        #
        return llmemory.cast_adr_to_ptr(result+size_gc_header, llmemory.GCREF)


    def malloc_varsize_clear(self, typeid, length, size, itemsize,
                             offset_to_length, can_collect):
        ll_assert(can_collect, "!can_collect")
        size_gc_header = self.gcheaderbuilder.size_gc_header
        nonvarsize = size_gc_header + size
        try:
            varsize = ovfcheck(itemsize * length)
            totalsize = ovfcheck(nonvarsize + varsize)
        except OverflowError:
            raise MemoryError
        #
        # If totalsize is greater than small_request_threshold, ask for
        # a rawmalloc.
        if llmemory.raw_malloc_usage(totalsize)>=self.small_request_threshold:
            result = self.external_malloc(typeid, totalsize)
            #
        else:
            # 'totalsize' should contain at least the GC header and
            # the length word, so it should never be smaller than
            # 'minimal_size_in_nursery' so far
            ll_assert(llmemory.raw_malloc_usage(totalsize) >=
                      self.minimal_size_in_nursery,
                      "malloc_varsize_clear(): totalsize < minimalsize")
            #
            # Get the memory from the nursery.  If there is not enough space
            # there, do a collect first.
            result = self.nursery_next
            self.nursery_next = result + totalsize
            if self.nursery_next > self.nursery_top:
                result = self.collect_and_reserve(totalsize)
            #
            # Build the object.
            llarena.arena_reserve(result, totalsize)
            self.init_gc_object(result, typeid, flags=0)
        #
        # Set the length and return the object.
        (result + size_gc_header + offset_to_length).signed[0] = length
        return llmemory.cast_adr_to_ptr(result+size_gc_header, llmemory.GCREF)


    def collect(self, gen=1):
        """Do a minor (gen=0) or major (gen>0) collection."""
        self.minor_collection()
        if gen > 0:
            self.major_collection()

    def collect_and_reserve(self, totalsize):
        """To call when nursery_next overflows nursery_top.
        Do a minor collection, and possibly also a major collection,
        and finally reserve 'totalsize' bytes at the start of the
        now-empty nursery.
        """
        self.collect(0)   # XXX
        self.nursery_next = self.nursery + totalsize
        return self.nursery
    collect_and_reserve._dont_inline_ = True


    def external_malloc(self, typeid, totalsize):
        """Allocate a large object using raw_malloc()."""
        #
        result = llmemory.raw_malloc(totalsize)
        if not result:
            raise MemoryError("cannot allocate large object")
        llmemory.raw_memclear(result, totalsize)
        self.init_gc_object(result, typeid, GCFLAG_NO_YOUNG_PTRS)
        #
        size_gc_header = self.gcheaderbuilder.size_gc_header
        self.rawmalloced_objects.append(result + size_gc_header)
        return result
    external_malloc._dont_inline_ = True


    # ----------
    # Simple helpers

    def get_type_id(self, obj):
        tid = self.header(obj).tid
        return llop.extract_ushort(llgroup.HALFWORD, tid)

    def combine(self, typeid16, flags):
        return llop.combine_ushort(lltype.Signed, typeid16, flags)

    def init_gc_object(self, addr, typeid16, flags=0):
        #print "init_gc_object(%r, 0x%x)" % (addr, flags)
        # The default 'flags' is zero.  The flags GCFLAG_NO_xxx_PTRS
        # have been chosen to allow 'flags' to be zero in the common
        # case (hence the 'NO' in their name).
        hdr = llmemory.cast_adr_to_ptr(addr, lltype.Ptr(self.HDR))
        hdr.tid = self.combine(typeid16, flags)

    def init_gc_object_immortal(self, addr, typeid16, flags=0):
        # For prebuilt GC objects, the flags must contain
        # GCFLAG_NO_xxx_PTRS, at least initially.
        flags |= GCFLAG_NO_HEAP_PTRS | GCFLAG_NO_YOUNG_PTRS
        self.init_gc_object(addr, typeid16, flags)

    def _can_never_move(self, obj):
        return False      # approximate good enough answer for id()

    def is_in_nursery(self, addr):
        ll_assert(llmemory.cast_adr_to_int(addr) & 1 == 0,
                  "odd-valued (i.e. tagged) pointer unexpected here")
        return self.nursery <= addr < self.nursery_top

    def is_forwarded_marker(self, tid):
        return isinstance(tid, int) and tid == FORWARDED_MARKER

    def get_forwarding_address(self, obj):
        obj = llarena.getfakearenaaddress(obj)
        return obj.address[0]

    def debug_check_object(self, obj):
        # after a minor or major collection, no object should be in the nursery
        ll_assert(not self.is_in_nursery(obj),
                  "object in nursery after collection")
        # similarily, all objects should have this flag:
        ll_assert(self.header(obj).tid & GCFLAG_NO_YOUNG_PTRS,
                  "missing GCFLAG_NO_YOUNG_PTRS")
        # the GCFLAG_VISITED should not be set between collections
        ll_assert(self.header(obj).tid & GCFLAG_VISITED == 0,
                  "unexpected GCFLAG_VISITED")

    # ----------
    # Write barrier

    # for the JIT: a minimal description of the write_barrier() method
    # (the JIT assumes it is of the shape
    #  "if addr_struct.int0 & JIT_WB_IF_FLAG: remember_young_pointer()")
    JIT_WB_IF_FLAG = GCFLAG_NO_YOUNG_PTRS

    def write_barrier(self, newvalue, addr_struct):
        if self.header(addr_struct).tid & GCFLAG_NO_YOUNG_PTRS:
            self.remember_young_pointer(addr_struct, newvalue)

    def _init_writebarrier_logic(self):
        # The purpose of attaching remember_young_pointer to the instance
        # instead of keeping it as a regular method is to help the JIT call it.
        # Additionally, it makes the code in write_barrier() marginally smaller
        # (which is important because it is inlined *everywhere*).
        # For x86, there is also an extra requirement: when the JIT calls
        # remember_young_pointer(), it assumes that it will not touch the SSE
        # registers, so it does not save and restore them (that's a *hack*!).
        def remember_young_pointer(addr_struct, addr):
            # 'addr_struct' is the address of the object in which we write;
            # 'addr' is the address that we write in 'addr_struct'.
            ll_assert(not self.is_in_nursery(addr_struct),
                      "nursery object with GCFLAG_NO_YOUNG_PTRS")
            # if we have tagged pointers around, we first need to check whether
            # we have valid pointer here, otherwise we can do it after the
            # is_in_nursery check
            if (self.config.taggedpointers and
                not self.is_valid_gc_object(addr)):
                return
            #
            # Core logic: if the 'addr' is in the nursery, then we need
            # to remove the flag GCFLAG_NO_YOUNG_PTRS and add the old object
            # to the list 'old_objects_pointing_to_young'.  We know that
            # 'addr_struct' cannot be in the nursery, because nursery objects
            # never have the flag GCFLAG_NO_YOUNG_PTRS to start with.
            objhdr = self.header(addr_struct)
            if self.is_in_nursery(addr):
                self.old_objects_pointing_to_young.append(addr_struct)
                objhdr.tid &= ~GCFLAG_NO_YOUNG_PTRS
            elif (not self.config.taggedpointers and
                  not self.is_valid_gc_object(addr)):
                return
            #
            # Second part: if 'addr_struct' is actually a prebuilt GC
            # object and it's the first time we see a write to it, we
            # add it to the list 'prebuilt_root_objects'.  Note that we
            # do it even in the (rare?) case of 'addr' being another
            # prebuilt object, to simplify code.
            if objhdr.tid & GCFLAG_NO_HEAP_PTRS:
                objhdr.tid &= ~GCFLAG_NO_HEAP_PTRS
                self.prebuilt_root_objects.append(addr_struct)

        remember_young_pointer._dont_inline_ = True
        self.remember_young_pointer = remember_young_pointer


    # ----------
    # Nursery collection

    def minor_collection(self):
        """Perform a minor collection: find the objects from the nursery
        that remain alive and move them out."""
        #
        # First, find the roots that point to nursery objects.  These
        # nursery objects are copied out of the nursery.  Note that
        # references to further nursery objects are not modified by
        # this step; only objects directly referenced by roots are
        # copied out.  They are also added to the list
        # 'old_objects_pointing_to_young'.
        self.collect_roots_in_nursery()
        #
        # Now trace objects from 'old_objects_pointing_to_young'.
        # All nursery objects they reference are copied out of the
        # nursery, and again added to 'old_objects_pointing_to_young'.
        # We proceed until 'old_objects_pointing_to_young' is empty.
        self.collect_oldrefs_to_nursery()
        #
        # Update the id tracking of any object that was moved out of
        # the nursery.
        if self.young_objects_with_id.length() > 0:
            self.update_young_objects_with_id()
        #
        # Now all live nursery objects should be out, and the rest dies.
        # Fill the whole nursery with zero and reset the current nursery
        # pointer.
        llarena.arena_reset(self.nursery, self.nursery_size, 2)
        self.nursery_next = self.nursery
        #
        self.change_nursery_hash_base()
        self.debug_check_consistency()     # XXX expensive!


    def collect_roots_in_nursery(self):
        # we don't need to trace prebuilt GcStructs during a minor collect:
        # if a prebuilt GcStruct contains a pointer to a young object,
        # then the write_barrier must have ensured that the prebuilt
        # GcStruct is in the list self.old_objects_pointing_to_young.
        self.root_walker.walk_roots(
            MiniMarkGC._trace_drag_out,  # stack roots
            MiniMarkGC._trace_drag_out,  # static in prebuilt non-gc
            None)                        # static in prebuilt gc

    def collect_oldrefs_to_nursery(self):
        # Follow the old_objects_pointing_to_young list and move the
        # young objects they point to out of the nursery.
        oldlist = self.old_objects_pointing_to_young
        while oldlist.non_empty():
            obj = oldlist.pop()
            #
            # Add the flag GCFLAG_NO_YOUNG_PTRS.  All live objects should have
            # this flag after a nursery collection.
            self.header(obj).tid |= GCFLAG_NO_YOUNG_PTRS
            #
            # Trace the 'obj' to replace pointers to nursery with pointers
            # outside the nursery, possibly forcing nursery objects out
            # and adding them to 'old_objects_pointing_to_young' as well.
            self.trace_and_drag_out_of_nursery(obj)

    def trace_and_drag_out_of_nursery(self, obj):
        """obj must not be in the nursery.  This copies all the
        young objects it references out of the nursery.
        """
        self.trace(obj, self._trace_drag_out, None)


    def _trace_drag_out(self, root, ignored=None):
        obj = root.address[0]
        #
        # If 'obj' is not in the nursery, nothing to change.
        if not self.is_in_nursery(obj):
            return
        #size_gc_header = self.gcheaderbuilder.size_gc_header
        #print '\ttrace_drag_out', llarena.getfakearenaaddress(obj - size_gc_header),
        #
        # If 'obj' was already forwarded, change it to its forwarding address.
        if self.is_forwarded_marker(self.header(obj).tid):
            root.address[0] = self.get_forwarding_address(obj)
            #print '(already forwarded)'
            return
        #
        # First visit to 'obj': we must move it out of the nursery.
        size_gc_header = self.gcheaderbuilder.size_gc_header
        size = self.get_size(obj)
        totalsize = size_gc_header + size
        totalsize_incl_hash = totalsize
        if self.header(obj).tid & GCFLAG_HASHFIELD:
            totalsize_incl_hash += llmemory.sizeof(lltype.Signed)
        # 
        # Allocate a new nonmovable location for it.
        # Note that 'totalsize' must be < small_request_threshold, so
        # 'totalsize_incl_hash <= small_request_threshold'.
        newhdr = self.ac.malloc(totalsize_incl_hash)
        newobj = newhdr + size_gc_header
        #
        # Copy it.  Note that references to other objects in the
        # nursery are kept unchanged in this step.
        llmemory.raw_memcopy(obj - size_gc_header, newhdr, totalsize)
        #
        # Write the hash field too, if necessary.
        if self.header(obj).tid & GCFLAG_HASHFIELD:
            hash = self._compute_current_nursery_hash(obj)
            (newhdr + (size_gc_header + size)).signed[0] = hash
        #
        # Set the old object's tid to FORWARDED_MARKER and replace
        # the old object's content with the target address.
        # A bit of no-ops to convince llarena that we are changing
        # the layout, in non-translated versions.
        llarena.arena_reset(obj - size_gc_header, totalsize, 0)
        llarena.arena_reserve(obj - size_gc_header, llmemory.sizeof(self.HDR))
        llarena.arena_reserve(obj, llmemory.sizeof(llmemory.Address))
        self.header(obj).tid = FORWARDED_MARKER
        obj = llarena.getfakearenaaddress(obj)
        obj.address[0] = newobj
        #
        # Change the original pointer to this object.
        #print
        #print '\t\t\t->', llarena.getfakearenaaddress(newobj - size_gc_header)
        root.address[0] = newobj
        #
        # Add the newobj to the list 'old_objects_pointing_to_young',
        # because it can contain further pointers to other young objects.
        # We will fix such references to point to the copy of the young
        # objects when we walk 'old_objects_pointing_to_young'.
        self.old_objects_pointing_to_young.append(newobj)


    # ----------
    # Full collection

    def major_collection(self):
        """Do a major collection.  Only for when the nursery is empty."""
        #
        # Debugging checks
        ll_assert(self.nursery_next == self.nursery,
                  "nursery not empty in major_collection()")
        self.debug_check_consistency()
        #
        # Note that a major collection is non-moving.  The goal is only to
        # find and free some of the objects allocated by the ArenaCollection.
        # We first visit all objects and toggle the flag GCFLAG_VISITED on
        # them, starting from the roots.
        self.collect_roots()
        self.visit_all_objects()
        #
        # Walk the 'objects_with_id' list and remove the ones that die,
        # i.e. that don't have the GCFLAG_VISITED flag.
        self.update_objects_with_id()
        #
        # Walk all rawmalloced objects and free the ones that don't
        # have the GCFLAG_VISITED flag.
        self.free_unvisited_rawmalloc_objects()
        #
        # Ask the ArenaCollection to visit all objects.  Free the ones
        # that have not been visited above, and reset GCFLAG_VISITED on
        # the others.
        self.ac.mass_free(self._free_if_unvisited)
        #
        # We also need to reset the GCFLAG_VISITED on prebuilt GC objects.
        self.prebuilt_root_objects.foreach(self._reset_gcflag_visited, None)
        #
        self.debug_check_consistency()


    def _free_if_unvisited(self, hdr):
        size_gc_header = self.gcheaderbuilder.size_gc_header
        obj = hdr + size_gc_header
        if self.header(obj).tid & GCFLAG_VISITED:
            self.header(obj).tid &= ~GCFLAG_VISITED
            return False     # survives
        else:
            return True      # dies

    def _reset_gcflag_visited(self, obj, ignored=None):
        self.header(obj).tid &= ~GCFLAG_VISITED

    def free_unvisited_rawmalloc_objects(self):
        size_gc_header = self.gcheaderbuilder.size_gc_header
        list = self.rawmalloced_objects
        self.rawmalloced_objects = self.AddressStack()
        #
        while list.non_empty():
            obj = list.pop()
            if self.header(obj).tid & GCFLAG_VISITED:
                self.header(obj).tid &= ~GCFLAG_VISITED   # survives
                self.rawmalloced_objects.append(obj)
            else:
                llmemory.raw_free(obj - size_gc_header)
        #
        list.delete()


    def collect_roots(self):
        # Collect all roots.  Starts from all the objects
        # from 'prebuilt_root_objects'.
        self.objects_to_trace = self.AddressStack()
        self.prebuilt_root_objects.foreach(self._collect_obj, None)
        #
        # Add the roots from the other sources.
        self.root_walker.walk_roots(
            MiniMarkGC._collect_ref,  # stack roots
            MiniMarkGC._collect_ref,  # static in prebuilt non-gc structures
            None)   # we don't need the static in all prebuilt gc objects

    def _collect_obj(self, obj, ignored=None):
        self.objects_to_trace.append(obj)

    def _collect_ref(self, root, ignored=None):
        self.objects_to_trace.append(root.address[0])

    def visit_all_objects(self):
        pending = self.objects_to_trace
        while pending.non_empty():
            obj = pending.pop()
            self.visit(obj)
        pending.delete()

    def visit(self, obj):
        #
        # 'obj' is a live object.  Check GCFLAG_VISITED to know if we
        # have already seen it before.
        #
        # Moreover, we can ignore prebuilt objects with GCFLAG_NO_HEAP_PTRS.
        # If they have this flag set, then they cannot point to heap
        # objects, so ignoring them is fine.  If they don't have this
        # flag set, then the object should be in 'prebuilt_root_objects',
        # and the GCFLAG_VISITED will be reset at the end of the
        # collection.
        hdr = self.header(obj)
        if hdr.tid & (GCFLAG_VISITED | GCFLAG_NO_HEAP_PTRS):
            return
        #
        # It's the first time.  We set the flag.
        hdr.tid |= GCFLAG_VISITED
        #
        # Trace the content of the object and put all objects it references
        # into the 'objects_to_trace' list.
        self.trace(obj, self._collect_ref, None)


    # ----------
    # id() support

    def id(self, gcobj):
        """Implement id() of an object, given as a GCREF."""
        obj = llmemory.cast_ptr_to_adr(gcobj)
        #
        # Is it a tagged pointer?  For them, the result is odd-valued.
        if not self.is_valid_gc_object(obj):
            return llmemory.cast_adr_to_int(obj)
        #
        # Is the object still in the nursery?
        if self.is_in_nursery(obj):
            result = self.young_objects_with_id.get(obj)
            if not result:
                result = self._next_id()
                self.young_objects_with_id.setitem(obj, result)
        else:
            result = self.objects_with_id.get(obj)
            if not result:
                # An 'obj' not in the nursery and not in 'objects_with_id'
                # did not have its id() asked for and will not move any more,
                # so we can just return its address as the result.
                return llmemory.cast_adr_to_int(obj)
        #
        # If we reach here, 'result' is an odd number.  If we double it,
        # we have a number of the form 4n+2, which cannot collide with
        # tagged pointers nor with any real address.
        return llmemory.cast_adr_to_int(result) * 2


    def update_young_objects_with_id(self):
        # Called during a minor collection.
        self.young_objects_with_id.foreach(self._update_object_id,
                                           self.objects_with_id)
        self.young_objects_with_id.clear()
        # NB. the clear() also makes the dictionary shrink back to its
        # minimal size, which is actually a good idea: a large, mostly-empty
        # table is bad for the next call to 'foreach'.

    def _update_object_id(self, obj, id, new_objects_with_id):
        if self.is_forwarded_marker(self.header(obj).tid):
            newobj = self.get_forwarding_address(obj)
            new_objects_with_id.setitem(newobj, id)
        else:
            self.id_free_list.append(id)

    def _update_object_id_FAST(self, obj, id, new_objects_with_id):
        # overrides the parent's version (a bit hackish)
        if self.header(obj).tid & GCFLAG_VISITED:
            new_objects_with_id.insertclean(obj, id)
        else:
            self.id_free_list.append(id)


    # ----------
    # identityhash() support

    def identityhash(self, gcobj):
        obj = llmemory.cast_ptr_to_adr(gcobj)
        if self.is_in_nursery(obj):
            #
            # A nursery object's identityhash is never stored with the
            # object, but returned by _compute_current_nursery_hash().
            # But we must set the GCFLAG_HASHFIELD to remember that
            # we will have to store it into the object when it moves.
            self.header(obj).tid |= GCFLAG_HASHFIELD
            return self._compute_current_nursery_hash(obj)
        #
        if self.header(obj).tid & GCFLAG_HASHFIELD:
            #
            # An non-moving object with a hash field.
            objsize = self.get_size(obj)
            obj = llarena.getfakearenaaddress(obj)
            return (obj + objsize).signed[0]
        #
        # No hash field needed.
        return llmemory.cast_adr_to_int(obj)


    def change_nursery_hash_base(self):
        # The following should be enough to ensure that young objects
        # tend to always get a different hash.  It also makes sure that
        # nursery_hash_base is not a multiple of WORD, to avoid collisions
        # with the hash of non-young objects.
        hash_base = self.nursery_hash_base
        hash_base += self.nursery_size - 1
        if (hash_base & (WORD-1)) == 0:
            hash_base -= 1
        self.nursery_hash_base = intmask(hash_base)

    def _compute_current_nursery_hash(self, obj):
        return intmask(llmemory.cast_adr_to_int(obj) + self.nursery_hash_base)


# ____________________________________________________________

# For testing, a simple implementation of ArenaCollection.
# This version could be used together with obmalloc.c, but
# it requires an extra word per object in the 'all_objects'
# list.

class SimpleArenaCollection(object):

    def __init__(self, arena_size, page_size, small_request_threshold):
        self.arena_size = arena_size   # ignored
        self.page_size = page_size
        self.small_request_threshold = small_request_threshold
        self.all_objects = []

    def malloc(self, size):
        nsize = llmemory.raw_malloc_usage(size)
        ll_assert(nsize > 0, "malloc: size is null or negative")
        ll_assert(nsize <= self.small_request_threshold,"malloc: size too big")
        ll_assert((nsize & (WORD-1)) == 0, "malloc: size is not aligned")
        #
        result = llarena.arena_malloc(nsize, False)
        #
        minimarkpage.reserve_with_hash(result, size)
        self.all_objects.append(result)
        return result

    def mass_free(self, ok_to_free_func):
        objs = self.all_objects
        self.all_objects = []
        for rawobj in objs:
            if ok_to_free_func(rawobj):
                llarena.arena_free(rawobj)
            else:
                self.all_objects.append(rawobj)
