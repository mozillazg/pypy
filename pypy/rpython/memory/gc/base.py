from pypy.rpython.lltypesystem import lltype, llmemory, llarena
from pypy.rlib.debug import ll_assert
from pypy.rpython.memory.gcheader import GCHeaderBuilder
from pypy.rpython.memory.support import DEFAULT_CHUNK_SIZE
from pypy.rpython.memory.support import get_address_stack, get_address_deque
from pypy.rpython.memory.support import AddressDict
from pypy.rpython.lltypesystem.llmemory import NULL, raw_malloc_usage

class GCBase(object):
    _alloc_flavor_ = "raw"
    moving_gc = False
    needs_write_barrier = False
    malloc_zero_filled = False
    prebuilt_gc_objects_are_static_roots = True
    can_realloc = False

    def can_malloc_nonmovable(self):
        return not self.moving_gc

    # The following flag enables costly consistency checks after each
    # collection.  It is automatically set to True by test_gc.py.  The
    # checking logic is translatable, so the flag can be set to True
    # here before translation.
    DEBUG = False

    def set_query_functions(self, is_varsize, has_gcptr_in_varsize,
                            is_gcarrayofgcptr,
                            getfinalizer,
                            offsets_to_gc_pointers,
                            fixed_size, varsize_item_sizes,
                            varsize_offset_to_variable_part,
                            varsize_offset_to_length,
                            varsize_offsets_to_gcpointers_in_var_part,
                            weakpointer_offset):
        self.getfinalizer = getfinalizer
        self.is_varsize = is_varsize
        self.has_gcptr_in_varsize = has_gcptr_in_varsize
        self.is_gcarrayofgcptr = is_gcarrayofgcptr
        self.offsets_to_gc_pointers = offsets_to_gc_pointers
        self.fixed_size = fixed_size
        self.varsize_item_sizes = varsize_item_sizes
        self.varsize_offset_to_variable_part = varsize_offset_to_variable_part
        self.varsize_offset_to_length = varsize_offset_to_length
        self.varsize_offsets_to_gcpointers_in_var_part = varsize_offsets_to_gcpointers_in_var_part
        self.weakpointer_offset = weakpointer_offset

    def set_root_walker(self, root_walker):
        self.root_walker = root_walker

    def write_barrier(self, newvalue, addr_struct):
        pass

    def setup(self):
        pass

    def statistics(self, index):
        return -1

    def size_gc_header(self, typeid=0):
        return self.gcheaderbuilder.size_gc_header

    def malloc(self, typeid, length=0, zero=False):
        """For testing.  The interface used by the gctransformer is
        the four malloc_[fixed,var]size[_clear]() functions.
        """
        # Rules about fallbacks in case of missing malloc methods:
        #  * malloc_fixedsize_clear() and malloc_varsize_clear() are mandatory
        #  * malloc_fixedsize() and malloc_varsize() fallback to the above
        # XXX: as of r49360, gctransformer.framework never inserts calls
        # to malloc_varsize(), but always uses malloc_varsize_clear()

        size = self.fixed_size(typeid)
        needs_finalizer = bool(self.getfinalizer(typeid))
        contains_weakptr = self.weakpointer_offset(typeid) >= 0
        assert not (needs_finalizer and contains_weakptr)
        if self.is_varsize(typeid):
            assert not contains_weakptr
            itemsize = self.varsize_item_sizes(typeid)
            offset_to_length = self.varsize_offset_to_length(typeid)
            if zero or not hasattr(self, 'malloc_varsize'):
                malloc_varsize = self.malloc_varsize_clear
            else:
                malloc_varsize = self.malloc_varsize
            ref = malloc_varsize(typeid, length, size, itemsize,
                                 offset_to_length, True, needs_finalizer)
        else:
            if zero or not hasattr(self, 'malloc_fixedsize'):
                malloc_fixedsize = self.malloc_fixedsize_clear
            else:
                malloc_fixedsize = self.malloc_fixedsize
            ref = malloc_fixedsize(typeid, size, True, needs_finalizer,
                                   contains_weakptr)
        # lots of cast and reverse-cast around...
        return llmemory.cast_ptr_to_adr(ref)

    def malloc_nonmovable(self, typeid, length=0, zero=False):
        return self.malloc(typeid, length, zero)

    def id(self, ptr):
        return lltype.cast_ptr_to_int(ptr)

    def can_move(self, addr):
        return False

    def set_max_heap_size(self, size):
        pass

    def x_swap_pool(self, newpool):
        return newpool

    def x_clone(self, clonedata):
        raise RuntimeError("no support for x_clone in the GC")

    def trace(self, obj, callback, arg):
        """Enumerate the locations inside the given obj that can contain
        GC pointers.  For each such location, callback(pointer, arg) is
        called, where 'pointer' is an address inside the object.
        Typically, 'callback' is a bound method and 'arg' can be None.
        """
        typeid = self.get_type_id(obj)
        if self.is_gcarrayofgcptr(typeid):
            # a performance shortcut for GcArray(gcptr)
            length = (obj + llmemory.gcarrayofptr_lengthoffset).signed[0]
            item = obj + llmemory.gcarrayofptr_itemsoffset
            while length > 0:
                callback(item, arg)
                item += llmemory.gcarrayofptr_singleitemoffset
                length -= 1
            return
        offsets = self.offsets_to_gc_pointers(typeid)
        i = 0
        while i < len(offsets):
            callback(obj + offsets[i], arg)
            i += 1
        if self.has_gcptr_in_varsize(typeid):
            item = obj + self.varsize_offset_to_variable_part(typeid)
            length = (obj + self.varsize_offset_to_length(typeid)).signed[0]
            offsets = self.varsize_offsets_to_gcpointers_in_var_part(typeid)
            itemlength = self.varsize_item_sizes(typeid)
            while length > 0:
                j = 0
                while j < len(offsets):
                    callback(item + offsets[j], arg)
                    j += 1
                item += itemlength
                length -= 1
    trace._annspecialcase_ = 'specialize:arg(2)'

    def debug_check_consistency(self):
        """To use after a collection.  If self.DEBUG is set, this
        enumerates all roots and traces all objects to check if we didn't
        accidentally free a reachable object or forgot to update a pointer
        to an object that moved.
        """
        if self.DEBUG:
            from pypy.rlib.objectmodel import we_are_translated
            from pypy.rpython.memory.support import AddressDict
            self._debug_seen = AddressDict()
            self._debug_pending = self.AddressStack()
            if not we_are_translated():
                self.root_walker._walk_prebuilt_gc(self._debug_record)
            callback = GCBase._debug_callback
            self.root_walker.walk_roots(callback, callback, callback)
            pending = self._debug_pending
            while pending.non_empty():
                obj = pending.pop()
                self.debug_check_object(obj)
                self.trace(obj, self._debug_callback2, None)
            self._debug_seen.delete()
            self._debug_pending.delete()

    def _debug_record(self, obj):
        seen = self._debug_seen
        if not seen.contains(obj):
            seen.add(obj)
            self._debug_pending.append(obj)
    def _debug_callback(self, root):
        obj = root.address[0]
        ll_assert(bool(obj), "NULL address from walk_roots()")
        self._debug_record(obj)
    def _debug_callback2(self, pointer, ignored):
        obj = pointer.address[0]
        if obj:
            self._debug_record(obj)

    def debug_check_object(self, obj):
        pass


TYPEID_MASK = 0xffff
first_gcflag = 1 << 16
GCFLAG_FORWARDED = first_gcflag
# GCFLAG_EXTERNAL is set on objects not living in the semispace:
# either immortal objects or (for HybridGC) externally raw_malloc'ed
GCFLAG_EXTERNAL = first_gcflag << 1
GCFLAG_FINALIZATION_ORDERING = first_gcflag << 2

class MovingGCBase(GCBase):
    moving_gc = True
    first_unused_gcflag = first_gcflag << 3

    def __init__(self, chunk_size=DEFAULT_CHUNK_SIZE):
        GCBase.__init__(self)
        self.gcheaderbuilder = GCHeaderBuilder(self.HDR)
        self.AddressStack = get_address_stack(chunk_size)
        self.AddressDeque = get_address_deque(chunk_size)
        self.AddressDict = AddressDict
        self.finalizer_lock_count = 0
        self.id_free_list = self.AddressStack()
        self.next_free_id = 1

    def setup(self):
        self.objects_with_finalizers = self.AddressDeque()
        self.run_finalizers = self.AddressDeque()
        self.objects_with_weakrefs = self.AddressStack()
        self.objects_with_id = self.AddressDict()

    def can_move(self, addr):
        return True

    def header(self, addr):
        addr -= self.gcheaderbuilder.size_gc_header
        return llmemory.cast_adr_to_ptr(addr, lltype.Ptr(self.HDR))

    def get_type_id(self, addr):
        tid = self.header(addr).tid
        ll_assert(tid & (GCFLAG_FORWARDED|GCFLAG_EXTERNAL) != GCFLAG_FORWARDED,
                  "get_type_id on forwarded obj")
        # Non-prebuilt forwarded objects are overwritten with a FORWARDSTUB.
        # Although calling get_type_id() on a forwarded object works by itself,
        # we catch it as an error because it's likely that what is then
        # done with the typeid is bogus.
        return tid & TYPEID_MASK

    def init_gc_object(self, addr, typeid, flags=0):
        hdr = llmemory.cast_adr_to_ptr(addr, lltype.Ptr(self.HDR))
        hdr.tid = typeid | flags

    def init_gc_object_immortal(self, addr, typeid, flags=0):
        hdr = llmemory.cast_adr_to_ptr(addr, lltype.Ptr(self.HDR))
        hdr.tid = typeid | flags | GCFLAG_EXTERNAL | GCFLAG_FORWARDED
        # immortal objects always have GCFLAG_FORWARDED set;
        # see get_forwarding_address().

    def get_size(self, obj):
        typeid = self.get_type_id(obj)
        size = self.fixed_size(typeid)
        if self.is_varsize(typeid):
            lenaddr = obj + self.varsize_offset_to_length(typeid)
            length = lenaddr.signed[0]
            size += length * self.varsize_item_sizes(typeid)
            size = llarena.round_up_for_allocation(size)
        return size



    def deal_with_objects_with_finalizers(self, scan):
        # walk over list of objects with finalizers
        # if it is not copied, add it to the list of to-be-called finalizers
        # and copy it, to me make the finalizer runnable
        # We try to run the finalizers in a "reasonable" order, like
        # CPython does.  The details of this algorithm are in
        # pypy/doc/discussion/finalizer-order.txt.
        new_with_finalizer = self.AddressDeque()
        marked = self.AddressDeque()
        pending = self.AddressStack()
        self.tmpstack = self.AddressStack()
        while self.objects_with_finalizers.non_empty():
            x = self.objects_with_finalizers.popleft()
            ll_assert(self._finalization_state(x) != 1, 
                      "bad finalization state 1")
            if self.surviving(x):
                new_with_finalizer.append(self.get_forwarding_address(x))
                continue
            marked.append(x)
            pending.append(x)
            while pending.non_empty():
                y = pending.pop()
                state = self._finalization_state(y)
                if state == 0:
                    self._bump_finalization_state_from_0_to_1(y)
                    self.trace(y, self._append_if_nonnull, pending)
                elif state == 2:
                    self._recursively_bump_finalization_state_from_2_to_3(y)
            scan = self._recursively_bump_finalization_state_from_1_to_2(
                       x, scan)

        while marked.non_empty():
            x = marked.popleft()
            state = self._finalization_state(x)
            ll_assert(state >= 2, "unexpected finalization state < 2")
            newx = self.get_forwarding_address(x)
            if state == 2:
                self.run_finalizers.append(newx)
                # we must also fix the state from 2 to 3 here, otherwise
                # we leave the GCFLAG_FINALIZATION_ORDERING bit behind
                # which will confuse the next collection
                self._recursively_bump_finalization_state_from_2_to_3(x)
            else:
                new_with_finalizer.append(newx)

        self.tmpstack.delete()
        pending.delete()
        marked.delete()
        self.objects_with_finalizers.delete()
        self.objects_with_finalizers = new_with_finalizer
        return scan

    def _append_if_nonnull(pointer, stack):
        if pointer.address[0] != NULL:
            stack.append(pointer.address[0])
    _append_if_nonnull = staticmethod(_append_if_nonnull)

    def _finalization_state(self, obj):
        if self.surviving(obj):
            newobj = self.get_forwarding_address(obj)
            hdr = self.header(newobj)
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

    def _bump_finalization_state_from_0_to_1(self, obj):
        ll_assert(self._finalization_state(obj) == 0,
                  "unexpected finalization state != 0")
        hdr = self.header(obj)
        hdr.tid |= GCFLAG_FINALIZATION_ORDERING

    def _recursively_bump_finalization_state_from_2_to_3(self, obj):
        ll_assert(self._finalization_state(obj) == 2,
                  "unexpected finalization state != 2")
        newobj = self.get_forwarding_address(obj)
        pending = self.tmpstack
        ll_assert(not pending.non_empty(), "tmpstack not empty")
        pending.append(newobj)
        while pending.non_empty():
            y = pending.pop()
            hdr = self.header(y)
            if hdr.tid & GCFLAG_FINALIZATION_ORDERING:     # state 2 ?
                hdr.tid &= ~GCFLAG_FINALIZATION_ORDERING   # change to state 3
                self.trace(y, self._append_if_nonnull, pending)

    def _recursively_bump_finalization_state_from_1_to_2(self, obj, scan):
        # recursively convert objects from state 1 to state 2.
        # Note that copy() copies all bits, including the
        # GCFLAG_FINALIZATION_ORDERING.  The mapping between
        # state numbers and the presence of this bit was designed
        # for the following to work :-)
        self.copy(obj)
        return self.scan_copied(scan)

    def invalidate_weakrefs(self):
        # walk over list of objects that contain weakrefs
        # if the object it references survives then update the weakref
        # otherwise invalidate the weakref
        new_with_weakref = self.AddressStack()
        while self.objects_with_weakrefs.non_empty():
            obj = self.objects_with_weakrefs.pop()
            if not self.surviving(obj):
                continue # weakref itself dies
            obj = self.get_forwarding_address(obj)
            offset = self.weakpointer_offset(self.get_type_id(obj))
            pointing_to = (obj + offset).address[0]
            # XXX I think that pointing_to cannot be NULL here
            if pointing_to:
                if self.surviving(pointing_to):
                    (obj + offset).address[0] = self.get_forwarding_address(
                        pointing_to)
                    new_with_weakref.append(obj)
                else:
                    (obj + offset).address[0] = NULL
        self.objects_with_weakrefs.delete()
        self.objects_with_weakrefs = new_with_weakref

    def update_run_finalizers(self):
        # we are in an inner collection, caused by a finalizer
        # the run_finalizers objects need to be copied
        new_run_finalizer = self.AddressDeque()
        while self.run_finalizers.non_empty():
            obj = self.run_finalizers.popleft()
            new_run_finalizer.append(self.copy(obj))
        self.run_finalizers.delete()
        self.run_finalizers = new_run_finalizer

    def execute_finalizers(self):
        self.finalizer_lock_count += 1
        try:
            while self.run_finalizers.non_empty():
                #print "finalizer"
                if self.finalizer_lock_count > 1:
                    # the outer invocation of execute_finalizers() will do it
                    break
                obj = self.run_finalizers.popleft()
                finalizer = self.getfinalizer(self.get_type_id(obj))
                finalizer(obj)
        finally:
            self.finalizer_lock_count -= 1

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

    def debug_check_object(self, obj):
        """Check the invariants about 'obj' that should be true
        between collections."""
        tid = self.header(obj).tid
        if tid & GCFLAG_EXTERNAL:
            ll_assert(tid & GCFLAG_FORWARDED, "bug: external+!forwarded")
            ll_assert(not (self.tospace <= obj < self.free),
                      "external flag but object inside the semispaces")
        else:
            ll_assert(not (tid & GCFLAG_FORWARDED), "bug: !external+forwarded")
            ll_assert(self.tospace <= obj < self.free,
                      "!external flag but object outside the semispaces")
        ll_assert(not (tid & GCFLAG_FINALIZATION_ORDERING),
                  "unexpected GCFLAG_FINALIZATION_ORDERING")

    def debug_check_can_copy(self, obj):
        ll_assert(not (self.tospace <= obj < self.free),
                  "copy() on already-copied object")

def choose_gc_from_config(config):
    """Return a (GCClass, GC_PARAMS) from the given config object.
    """
    if config.translation.gctransformer != "framework":   # for tests
        config.translation.gc = "marksweep"     # crash if inconsistent

    classes = {"marksweep": "marksweep.MarkSweepGC",
               "statistics": "marksweep.PrintingMarkSweepGC",
               "semispace": "semispace.SemiSpaceGC",
               "generation": "generation.GenerationGC",
               "hybrid": "hybrid.HybridGC",
               }
    try:
        modulename, classname = classes[config.translation.gc].split('.')
    except KeyError:
        raise ValueError("unknown value for translation.gc: %r" % (
            config.translation.gc,))
    module = __import__("pypy.rpython.memory.gc." + modulename,
                        globals(), locals(), [classname])
    GCClass = getattr(module, classname)
    return GCClass, GCClass.TRANSLATION_PARAMS
