from pypy.rpython.lltypesystem import lltype, llmemory, llarena
from pypy.rlib.debug import ll_assert


class GCData(object):
    """The GC information tables, and the query functions that the GC
    calls to decode their content.  The encoding of this information
    is done by encode_type_shape().  These two places should be in sync,
    obviously, but in principle no other code should depend on the
    details of the encoding in TYPE_INFO.
    """
    _alloc_flavor_ = 'raw'

    OFFSETS_TO_GC_PTR = lltype.Array(lltype.Signed)
    ADDRESS_VOID_FUNC = lltype.FuncType([llmemory.Address], lltype.Void)
    FINALIZERTYPE = lltype.Ptr(ADDRESS_VOID_FUNC)

    # structure describing the layout of a type
    TYPE_INFO = lltype.Struct("type_info",
        ("flags",          lltype.Signed),    # T_... flags, see below
        ("finalizer",      FINALIZERTYPE),
        ("fixedsize",      lltype.Signed),
        ("ofstoptrs",      lltype.Ptr(OFFSETS_TO_GC_PTR)),
        ("varitemsize",    lltype.Signed),
        ("ofstovar",       lltype.Signed),
        ("ofstolength",    lltype.Signed),
        ("varofstoptrs",   lltype.Ptr(OFFSETS_TO_GC_PTR)),
        ("weakptrofs",     lltype.Signed),
        )

    def q_is_varsize(self, typeinfo):
        return (typeinfo.flags & T_IS_VARSIZE) != 0

    def q_has_gcptr_in_varsize(self, typeinfo):
        return (typeinfo.flags & T_HAS_GCPTR_IN_VARSIZE) != 0

    def q_is_gcarrayofgcptr(self, typeinfo):
        return (typeinfo.flags & T_IS_GCARRAYOFGCPTR) != 0

    def q_finalizer(self, typeinfo):
        return typeinfo.finalizer

    def q_offsets_to_gc_pointers(self, typeinfo):
        return typeinfo.ofstoptrs

    def q_fixed_size(self, typeinfo):
        return typeinfo.fixedsize

    def q_varsize_item_sizes(self, typeinfo):
        return typeinfo.varitemsize

    def q_varsize_offset_to_variable_part(self, typeinfo):
        return typeinfo.ofstovar

    def q_varsize_offset_to_length(self, typeinfo):
        return typeinfo.ofstolength

    def q_varsize_offsets_to_gcpointers_in_var_part(self, typeinfo):
        return typeinfo.varofstoptrs

    def q_weakpointer_offset(self, typeinfo):
        return typeinfo.weakptrofs

    def set_query_functions(self, gc):
        gc.set_query_functions(
            self.q_is_varsize,
            self.q_has_gcptr_in_varsize,
            self.q_is_gcarrayofgcptr,
            self.q_finalizer,
            self.q_offsets_to_gc_pointers,
            self.q_fixed_size,
            self.q_varsize_item_sizes,
            self.q_varsize_offset_to_variable_part,
            self.q_varsize_offset_to_length,
            self.q_varsize_offsets_to_gcpointers_in_var_part,
            self.q_weakpointer_offset)

# For the q_xxx functions that return flags, we use bits in the 'flags'
# field.  The idea is that at some point, some GCs could copy these bits
# into the header of each object to allow for an indirection-free decoding.
# (Not all combinations of the 3 flags are meaningful; in fact, only 4 are)

T_IS_VARSIZE           = 0x1
T_HAS_GCPTR_IN_VARSIZE = 0x2
T_IS_GCARRAYOFGCPTR    = 0x4
T_first_unused_bit     = 0x8

def get_type_flags(TYPE):
    """Compute the 'flags' for the type.
    """
    if not TYPE._is_varsize():
        return 0     # not var-sized

    if (isinstance(TYPE, lltype.GcArray)
        and isinstance(TYPE.OF, lltype.Ptr)
        and TYPE.OF.TO._gckind == 'gc'):
        # a simple GcArray(gcptr)
        return T_IS_VARSIZE | T_HAS_GCPTR_IN_VARSIZE | T_IS_GCARRAYOFGCPTR

    if isinstance(TYPE, lltype.Struct):
        ARRAY = TYPE._flds[TYPE._arrayfld]
    else:
        ARRAY = TYPE
    assert isinstance(ARRAY, lltype.Array)
    if ARRAY.OF != lltype.Void and len(offsets_to_gc_pointers(ARRAY.OF)) > 0:
        # var-sized, with gc pointers in the variable part
        return T_IS_VARSIZE | T_HAS_GCPTR_IN_VARSIZE
    else:
        # var-sized, but no gc pointer in the variable part
        return T_IS_VARSIZE


def encode_type_shape(builder, info, TYPE):
    """Encode the shape of the TYPE into the TYPE_INFO structure 'info'."""
    offsets = offsets_to_gc_pointers(TYPE)
    info.flags = get_type_flags(TYPE)
    info.ofstoptrs = builder.offsets2table(offsets, TYPE)
    info.finalizer = builder.make_finalizer_funcptr_for_type(TYPE)
    info.weakptrofs = weakpointer_offset(TYPE)
    if not TYPE._is_varsize():
        info.fixedsize = llarena.round_up_for_allocation(
            llmemory.sizeof(TYPE))
        info.ofstolength = -1
        # note about round_up_for_allocation(): in the 'info' table
        # we put a rounded-up size only for fixed-size objects.  For
        # varsize ones, the GC must anyway compute the size at run-time
        # and round up that result.
    else:
        info.fixedsize = llmemory.sizeof(TYPE, 0)
        if isinstance(TYPE, lltype.Struct):
            ARRAY = TYPE._flds[TYPE._arrayfld]
            ofs1 = llmemory.offsetof(TYPE, TYPE._arrayfld)
            info.ofstolength = ofs1 + llmemory.ArrayLengthOffset(ARRAY)
            info.ofstovar = ofs1 + llmemory.itemoffsetof(ARRAY, 0)
            # XXX we probably don't need isrpystring any more
            if ARRAY._hints.get('isrpystring'):
                info.fixedsize = llmemory.sizeof(TYPE, 1)
        else:
            ARRAY = TYPE
            info.ofstolength = llmemory.ArrayLengthOffset(ARRAY)
            info.ofstovar = llmemory.itemoffsetof(TYPE, 0)
        assert isinstance(ARRAY, lltype.Array)
        if ARRAY.OF != lltype.Void:
            offsets = offsets_to_gc_pointers(ARRAY.OF)
        else:
            offsets = ()
        info.varofstoptrs = builder.offsets2table(offsets, ARRAY.OF)
        info.varitemsize = llmemory.sizeof(ARRAY.OF)

# ____________________________________________________________


class TypeLayoutBuilder(object):

    def __init__(self):
        self.typeinfos = {}      # {LLTYPE: TYPE_INFO}
        self.seen_roots = {}
        # the following are lists of addresses of gc pointers living inside the
        # prebuilt structures.  It should list all the locations that could
        # possibly point to a GC heap object.
        # this lists contains pointers in GcStructs and GcArrays
        self.addresses_of_static_ptrs = []
        # this lists contains pointers in raw Structs and Arrays
        self.addresses_of_static_ptrs_in_nongc = []
        # if not gc.prebuilt_gc_objects_are_static_roots, then
        # additional_roots_sources counts the number of locations
        # within prebuilt GC objects that are of type Ptr(Gc)
        self.additional_roots_sources = 0
        self.finalizer_funcptrs = {}
        self.offsettable_cache = {}

    def get_type_info(self, TYPE):
        try:
            return self.typeinfos[TYPE]
        except KeyError:
            assert isinstance(TYPE, (lltype.GcStruct, lltype.GcArray))
            # Record the new type description as a TYPE_INFO structure.
            info = lltype.malloc(GCData.TYPE_INFO, immortal=True, zero=True)
            encode_type_shape(self, info, TYPE)
            self.typeinfos[TYPE] = info
            return info

    def offsets2table(self, offsets, TYPE):
        try:
            return self.offsettable_cache[TYPE]
        except KeyError:
            cachedarray = lltype.malloc(GCData.OFFSETS_TO_GC_PTR,
                                        len(offsets), immortal=True)
            for i, value in enumerate(offsets):
                cachedarray[i] = value
            self.offsettable_cache[TYPE] = cachedarray
            return cachedarray

    def finalizer_funcptr_for_type(self, TYPE):
        if TYPE in self.finalizer_funcptrs:
            return self.finalizer_funcptrs[TYPE]
        fptr = self.make_finalizer_funcptr_for_type(TYPE)
        self.finalizer_funcptrs[TYPE] = fptr
        return fptr

    def make_finalizer_funcptr_for_type(self, TYPE):
        # must be overridden for proper finalizer support
        return lltype.nullptr(GCData.ADDRESS_VOID_FUNC)

    def initialize_gc_query_function(self, gc):
        return GCData(self.type_info_list).set_query_functions(gc)

    def consider_constant(self, TYPE, value, gc):
        if value is not lltype.top_container(value):
            return
        if id(value) in self.seen_roots:
            return
        self.seen_roots[id(value)] = True

        if isinstance(TYPE, (lltype.GcStruct, lltype.GcArray)):
            typeinfo = self.get_type_info(TYPE)
            hdr = gc.gcheaderbuilder.new_header(value)
            adr = llmemory.cast_ptr_to_adr(hdr)
            gc.init_gc_object_immortal(adr, typeinfo)

        # The following collects the addresses of all the fields that have
        # a GC Pointer type, inside the current prebuilt object.  All such
        # fields are potential roots: unless the structure is immutable,
        # they could be changed later to point to GC heap objects.
        adr = llmemory.cast_ptr_to_adr(value._as_ptr())
        if TYPE._gckind == "gc":
            if not gc.prebuilt_gc_objects_are_static_roots:
                for a in gc_pointers_inside(value, adr):
                    self.additional_roots_sources += 1
                return
            else:
                appendto = self.addresses_of_static_ptrs
        else:
            appendto = self.addresses_of_static_ptrs_in_nongc
        for a in gc_pointers_inside(value, adr, mutable_only=True):
            appendto.append(a)

# ____________________________________________________________
#
# Helpers to discover GC pointers inside structures

def offsets_to_gc_pointers(TYPE):
    offsets = []
    if isinstance(TYPE, lltype.Struct):
        for name in TYPE._names:
            FIELD = getattr(TYPE, name)
            if isinstance(FIELD, lltype.Array):
                continue    # skip inlined array
            baseofs = llmemory.offsetof(TYPE, name)
            suboffsets = offsets_to_gc_pointers(FIELD)
            for s in suboffsets:
                try:
                    knownzero = s == 0
                except TypeError:
                    knownzero = False
                if knownzero:
                    offsets.append(baseofs)
                else:
                    offsets.append(baseofs + s)
        # sanity check
        #ex = lltype.Ptr(TYPE)._example()
        #adr = llmemory.cast_ptr_to_adr(ex)
        #for off in offsets:
        #    (adr + off)
    elif isinstance(TYPE, lltype.Ptr) and TYPE.TO._gckind == 'gc':
        offsets.append(0)
    return offsets

def weakpointer_offset(TYPE):
    if TYPE == WEAKREF:
        return llmemory.offsetof(WEAKREF, "weakptr")
    return -1

def gc_pointers_inside(v, adr, mutable_only=False):
    t = lltype.typeOf(v)
    if isinstance(t, lltype.Struct):
        if mutable_only and t._hints.get('immutable'):
            return
        for n, t2 in t._flds.iteritems():
            if isinstance(t2, lltype.Ptr) and t2.TO._gckind == 'gc':
                yield adr + llmemory.offsetof(t, n)
            elif isinstance(t2, (lltype.Array, lltype.Struct)):
                for a in gc_pointers_inside(getattr(v, n),
                                            adr + llmemory.offsetof(t, n),
                                            mutable_only):
                    yield a
    elif isinstance(t, lltype.Array):
        if mutable_only and t._hints.get('immutable'):
            return
        if isinstance(t.OF, lltype.Ptr) and t.OF.TO._gckind == 'gc':
            for i in range(len(v.items)):
                yield adr + llmemory.itemoffsetof(t, i)
        elif isinstance(t.OF, lltype.Struct):
            for i in range(len(v.items)):
                for a in gc_pointers_inside(v.items[i],
                                            adr + llmemory.itemoffsetof(t, i),
                                            mutable_only):
                    yield a

def zero_gc_pointers(p):
    TYPE = lltype.typeOf(p).TO
    zero_gc_pointers_inside(p, TYPE)

def zero_gc_pointers_inside(p, TYPE):
    if isinstance(TYPE, lltype.Struct):
        for name, FIELD in TYPE._flds.items():
            if isinstance(FIELD, lltype.Ptr) and FIELD.TO._gckind == 'gc':
                setattr(p, name, lltype.nullptr(FIELD.TO))
            elif isinstance(FIELD, lltype.ContainerType):
                zero_gc_pointers_inside(getattr(p, name), FIELD)
    elif isinstance(TYPE, lltype.Array):
        ITEM = TYPE.OF
        if isinstance(ITEM, lltype.Ptr) and ITEM.TO._gckind == 'gc':
            null = lltype.nullptr(ITEM.TO)
            for i in range(p._obj.getlength()):
                p[i] = null
        elif isinstance(ITEM, lltype.ContainerType):
            for i in range(p._obj.getlength()):
                zero_gc_pointers_inside(p[i], ITEM)

########## weakrefs ##########
# framework: weakref objects are small structures containing only an address

WEAKREF = lltype.GcStruct("weakref", ("weakptr", llmemory.Address))
WEAKREFPTR = lltype.Ptr(WEAKREF)
sizeof_weakref= llmemory.sizeof(WEAKREF)
empty_weakref = lltype.malloc(WEAKREF, immortal=True)
empty_weakref.weakptr = llmemory.NULL

def ll_weakref_deref(wref):
    wref = llmemory.cast_weakrefptr_to_ptr(WEAKREFPTR, wref)
    return wref.weakptr

def convert_weakref_to(targetptr):
    # Prebuilt weakrefs don't really need to be weak at all,
    # but we need to emulate the structure expected by ll_weakref_deref().
    if not targetptr:
        return empty_weakref
    else:
        link = lltype.malloc(WEAKREF, immortal=True)
        link.weakptr = llmemory.cast_ptr_to_adr(targetptr)
        return link
