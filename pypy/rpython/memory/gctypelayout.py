from pypy.rpython.lltypesystem import lltype, llmemory, llarena, llgroup
from pypy.rpython.lltypesystem import rclass
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rlib.objectmodel import we_are_translated
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

    # structure describing the layout of a typeid
    TYPE_INFO = lltype.Struct("type_info",
        ("infobits",       lltype.Signed),    # combination of the T_xxx consts
        ("finalizer",      FINALIZERTYPE),
        ("fixedsize",      lltype.Signed),
        ("ofstoptrs",      lltype.Ptr(OFFSETS_TO_GC_PTR)),
        hints={'immutable': True},
        )
    VARSIZE_TYPE_INFO = lltype.Struct("varsize_type_info",
        ("header",         TYPE_INFO),
        ("varitemsize",    lltype.Signed),
        ("ofstovar",       lltype.Signed),
        ("ofstolength",    lltype.Signed),
        ("varofstoptrs",   lltype.Ptr(OFFSETS_TO_GC_PTR)),
        hints={'immutable': True},
        )
    TYPE_INFO_PTR = lltype.Ptr(TYPE_INFO)
    VARSIZE_TYPE_INFO_PTR = lltype.Ptr(VARSIZE_TYPE_INFO)

    def __init__(self, type_info_group):
        assert isinstance(type_info_group, llgroup.group)
        self.type_info_group = type_info_group
        self.type_info_group_ptr = type_info_group._as_ptr()

    def get(self, typeid):
        _check_typeid(typeid)
        return llop.get_group_member(GCData.TYPE_INFO_PTR,
                                     self.type_info_group_ptr,
                                     typeid)

    def get_varsize(self, typeid):
        _check_typeid(typeid)
        return llop.get_group_member(GCData.VARSIZE_TYPE_INFO_PTR,
                                     self.type_info_group_ptr,
                                     typeid)

    def q_is_varsize(self, typeid):
        infobits = self.get(typeid).infobits
        return (infobits & T_IS_VARSIZE) != 0

    def q_has_gcptr_in_varsize(self, typeid):
        infobits = self.get(typeid).infobits
        return (infobits & T_HAS_GCPTR_IN_VARSIZE) != 0

    def q_is_gcarrayofgcptr(self, typeid):
        infobits = self.get(typeid).infobits
        return (infobits & T_IS_GCARRAY_OF_GCPTR) != 0

    def q_finalizer(self, typeid):
        return self.get(typeid).finalizer

    def q_offsets_to_gc_pointers(self, typeid):
        return self.get(typeid).ofstoptrs

    def q_fixed_size(self, typeid):
        return self.get(typeid).fixedsize

    def q_varsize_item_sizes(self, typeid):
        return self.get_varsize(typeid).varitemsize

    def q_varsize_offset_to_variable_part(self, typeid):
        return self.get_varsize(typeid).ofstovar

    def q_varsize_offset_to_length(self, typeid):
        return self.get_varsize(typeid).ofstolength

    def q_varsize_offsets_to_gcpointers_in_var_part(self, typeid):
        return self.get_varsize(typeid).varofstoptrs

    def q_weakpointer_offset(self, typeid):
        infobits = self.get(typeid).infobits
        if infobits & T_IS_WEAKREF:
            return weakptr_offset
        return -1

    def q_member_index(self, typeid):
        infobits = self.get(typeid).infobits
        return infobits & T_MEMBER_INDEX

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
            self.q_weakpointer_offset,
            self.q_member_index)


# the lowest 16bits are used to store group member index
T_MEMBER_INDEX         = 0xffff
T_IS_VARSIZE           = 0x10000
T_HAS_GCPTR_IN_VARSIZE = 0x20000
T_IS_GCARRAY_OF_GCPTR  = 0x40000
T_IS_WEAKREF           = 0x80000

def _check_typeid(typeid):
    ll_assert(llop.is_group_member_nonzero(lltype.Bool, typeid),
              "invalid type_id")


def encode_type_shape(builder, info, TYPE, index):
    """Encode the shape of the TYPE into the TYPE_INFO structure 'info'."""
    offsets = offsets_to_gc_pointers(TYPE)
    infobits = index
    info.ofstoptrs = builder.offsets2table(offsets, TYPE)
    info.finalizer = builder.make_finalizer_funcptr_for_type(TYPE)
    if not TYPE._is_varsize():
        info.fixedsize = llarena.round_up_for_allocation(
            llmemory.sizeof(TYPE), builder.GCClass.object_minimal_size)
        # note about round_up_for_allocation(): in the 'info' table
        # we put a rounded-up size only for fixed-size objects.  For
        # varsize ones, the GC must anyway compute the size at run-time
        # and round up that result.
    else:
        infobits |= T_IS_VARSIZE
        varinfo = lltype.cast_pointer(GCData.VARSIZE_TYPE_INFO_PTR, info)
        info.fixedsize = llmemory.sizeof(TYPE, 0)
        if isinstance(TYPE, lltype.Struct):
            ARRAY = TYPE._flds[TYPE._arrayfld]
            ofs1 = llmemory.offsetof(TYPE, TYPE._arrayfld)
            varinfo.ofstolength = ofs1 + llmemory.ArrayLengthOffset(ARRAY)
            varinfo.ofstovar = ofs1 + llmemory.itemoffsetof(ARRAY, 0)
        else:
            assert isinstance(TYPE, lltype.GcArray)
            ARRAY = TYPE
            if (isinstance(ARRAY.OF, lltype.Ptr)
                and ARRAY.OF.TO._gckind == 'gc'):
                infobits |= T_IS_GCARRAY_OF_GCPTR
            varinfo.ofstolength = llmemory.ArrayLengthOffset(ARRAY)
            varinfo.ofstovar = llmemory.itemoffsetof(TYPE, 0)
        assert isinstance(ARRAY, lltype.Array)
        if ARRAY.OF != lltype.Void:
            offsets = offsets_to_gc_pointers(ARRAY.OF)
        else:
            offsets = ()
        if len(offsets) > 0:
            infobits |= T_HAS_GCPTR_IN_VARSIZE
        varinfo.varofstoptrs = builder.offsets2table(offsets, ARRAY.OF)
        varinfo.varitemsize = llmemory.sizeof(ARRAY.OF)
    if TYPE == WEAKREF:
        infobits |= T_IS_WEAKREF
    info.infobits = infobits

# ____________________________________________________________


class TypeLayoutBuilder(object):
    can_add_new_types = True
    can_encode_type_shape = True    # set to False initially by the JIT

    size_of_fixed_type_info = llmemory.sizeof(GCData.TYPE_INFO)

    def __init__(self, GCClass, lltype2vtable=None):
        self.GCClass = GCClass
        self.lltype2vtable = lltype2vtable
        self.make_type_info_group()
        self.id_of_type = {}      # {LLTYPE: type_id}
        # This is a list of the GC objects that must be kept alive in all
        # cases.  It lists all prebuilt GcStructs and GcArrays that are
        # directly referenced from the code, and those that are referenced
        # from an immutable GC pointer in some raw Struct or Array.  It
        # does not list prebuilt GC objects that are only referenced from
        # other prebuilt GC objects.  This is the basic 'root set'.
        self.root_prebuilt_gc = []
        # This is a list of all the locations in raw Structs and Arrays
        # of type GC pointer that could possibly be modified.  They are
        # locations that might point to either a prebuilt or a heap GC
        # object.
        self.addresses_of_gc_ptrs_in_nongc = []
        #
        self.seen_roots = {}         # set of objects in root_prebuilt_gc
        self.seen_gcs = {}           # set of all gc objects seen so far
        self.seen_nongcs = {}        # set of all non-gc objects seen so far
        #
        self.finalizer_funcptrs = {}
        self.offsettable_cache = {}

    def make_type_info_group(self):
        self.type_info_group = llgroup.group("typeinfo")
        # don't use typeid 0, may help debugging
        DUMMY = lltype.Struct("dummy", ('x', lltype.Signed))
        dummy = lltype.malloc(DUMMY, immortal=True, zero=True)
        self.type_info_group.add_member(dummy)

    def get_type_id(self, TYPE):
        try:
            return self.id_of_type[TYPE]
        except KeyError:
            assert self.can_add_new_types
            assert isinstance(TYPE, (lltype.GcStruct, lltype.GcArray))
            # Record the new type_id description as a TYPE_INFO structure.
            # build the TYPE_INFO structure
            if not TYPE._is_varsize():
                fullinfo = lltype.malloc(GCData.TYPE_INFO,
                                         immortal=True, zero=True)
                info = fullinfo
            else:
                fullinfo = lltype.malloc(GCData.VARSIZE_TYPE_INFO,
                                         immortal=True, zero=True)
                info = fullinfo.header
            type_id = self.type_info_group.add_member(fullinfo)
            if self.can_encode_type_shape:
                encode_type_shape(self, info, TYPE, type_id.index)
            else:
                self._pending_type_shapes.append((info, TYPE, type_id.index))
            # store it
            self.id_of_type[TYPE] = type_id
            self.add_vtable_after_typeinfo(TYPE)
            return type_id

    def add_vtable_after_typeinfo(self, TYPE):
        # if gcremovetypeptr is False, then lltype2vtable is None and it
        # means that we don't have to store the vtables in type_info_group.
        if self.lltype2vtable is None:
            return
        # does the type have a vtable?
        vtable = self.lltype2vtable.get(TYPE, None)
        if vtable is not None:
            # yes.  check that in this case, we are not varsize
            assert not TYPE._is_varsize()
            vtable = lltype.normalizeptr(vtable)
            self.type_info_group.add_member(vtable)
        else:
            # no vtable from lltype2vtable -- double-check to be sure
            # that it's not a subclass of OBJECT.
            while isinstance(TYPE, lltype.GcStruct):
                assert TYPE is not rclass.OBJECT
                _, TYPE = TYPE._first_struct()

    def get_info(self, type_id):
        return llop.get_group_member(GCData.TYPE_INFO_PTR,
                                     self.type_info_group._as_ptr(),
                                     type_id)

    def get_info_varsize(self, type_id):
        return llop.get_group_member(GCData.VARSIZE_TYPE_INFO_PTR,
                                     self.type_info_group._as_ptr(),
                                     type_id)

    def is_weakref(self, type_id):
        return self.get_info(type_id).infobits & T_IS_WEAKREF

    def encode_type_shapes_now(self):
        if not self.can_encode_type_shape:
            self.can_encode_type_shape = True
            for info, TYPE, index in self._pending_type_shapes:
                encode_type_shape(self, info, TYPE, index)
            del self._pending_type_shapes

    def delay_encoding(self):
        # used by the JIT
        self._pending_type_shapes = []
        self.can_encode_type_shape = False

    def offsets2table(self, offsets, TYPE):
        if len(offsets) == 0:
            TYPE = lltype.Void    # we can share all zero-length arrays
        try:
            return self.offsettable_cache[TYPE]
        except KeyError:
            cachedarray = lltype.malloc(GCData.OFFSETS_TO_GC_PTR,
                                        len(offsets), immortal=True)
            for i, value in enumerate(offsets):
                cachedarray[i] = value
            self.offsettable_cache[TYPE] = cachedarray
            return cachedarray

    def close_table(self):
        # make sure we no longer add members to the type_info_group.
        self.can_add_new_types = False
        self.offsettable_cache = None
        return self.type_info_group

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
        return GCData(self.type_info_group).set_query_functions(gc)

    def consider_constant_gcobj(self, TYPE, value, gc, add_root):
        """This is supposed to be called for every Struct, Array, GcStruct
        or GcArray.
        GcArray.  'add_root' is a flag that tells if the gc object must
        be recorded in self.root_prebuilt_gc or not.
        """
        assert value._parentstructure() is None
        assert isinstance(TYPE, (lltype.GcStruct, lltype.GcArray))
        if id(value) not in self.seen_gcs:
            self.seen_gcs[id(value)] = value
            # initialize the gc header of the object
            typeid = self.get_type_id(TYPE)
            hdr = gc.gcheaderbuilder.new_header(value)
            adr = llmemory.cast_ptr_to_adr(hdr)
            gc.init_gc_object_immortal(adr, typeid)
        #
        if add_root:
            # if the GC object is referenced from "outside"
            self.add_root(value)

    def consider_constant_nongcobj(self, TYPE, value):
        """This is supposed to be called once for every raw Struct
        or Array.

        elif TYPE._kind != "gc":
            # we have a raw structure or array
            if id(value) not in self.seen_nongcs:
                self.seen_nongcs[id(value)] = value
                adr = llmemory.cast_ptr_to_adr(value._as_ptr())
                for a, immutable in enum_gc_pointers_inside(value, adr):
                    if immutable:
                        # an immutable GC ref: find out what it points to
                        ptr = a.ptr
                        if ptr:
                            ......
                        ...
            
        #
        # do the rest only once, even if we are called multiple times
        if id(value) in self.seen_constants:
            return
        self.seen_constants[id(value)] = value
        #
        if is_gc_object:
        else:
            # for non-gc objects: find their mutable gc references
            ........
        for a in mutable_gc_pointers_inside(value, adr):
            
            ...

        adr = llmemory.cast_ptr_to_adr(value._as_ptr())
        if TYPE._gckind == "gc":
            if gc.prebuilt_gc_objects_are_static_roots:
                appendto = self.addresses_of_static_ptrs
            else:
                return
        else:
            appendto = self.addresses_of_static_ptrs_in_nongc
            appendto.append(a)

    def add_root(self, value):
        if id(value) not in self.seen_roots:
            self.seen_roots[id(value)] = True
            self.root_prebuilt_gc.append(value)

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

def enum_gc_pointers_inside(v, adr):
    """Enumerate the GC pointers from the constant struct or array 'v'.
    For each of them, yields (addr-of-field, mutable-flag).
    """
    t = lltype.typeOf(v)
    if isinstance(t, lltype.Struct):
        fully_immutable = t._hints.get('immutable', False)
        if 'immutable_fields' in t._hints:
            immutable_fields = t._hints['immutable_fields'].fields
        else:
            immutable_fields = ()
        for n, t2 in t._flds.iteritems():
            if isinstance(t2, lltype.Ptr) and t2.TO._gckind == 'gc':
                yield (adr + llmemory.offsetof(t, n),
                       fully_immutable or n in immutable_fields)
            elif isinstance(t2, (lltype.Array, lltype.Struct)):
                for a in enum_gc_pointers_inside(getattr(v, n),
                                            adr + llmemory.offsetof(t, n)):
                    yield a
    elif isinstance(t, lltype.Array):
        fully_immutable = t._hints.get('immutable', False)
        if isinstance(t.OF, lltype.Ptr) and t.OF.TO._gckind == 'gc':
            for i in range(len(v.items)):
                yield (adr + llmemory.itemoffsetof(t, i), fully_immutable)
        elif isinstance(t.OF, lltype.Struct):
            for i in range(len(v.items)):
                for a in enum_gc_pointers_inside(v.items[i],
                                            adr + llmemory.itemoffsetof(t, i)):
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
weakptr_offset = llmemory.offsetof(WEAKREF, "weakptr")

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
