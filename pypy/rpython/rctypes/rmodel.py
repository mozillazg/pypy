from pypy.rpython.rmodel import Repr, inputconst
from pypy.rpython.error import TyperError
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.annotation.model import SomeCTypesObject
from pypy.annotation.pairtype import pairtype


# header common to boxes with a destructor
RCBOX_HEADER = lltype.GcStruct('rcbox',
                               ('rtti', lltype.Ptr(lltype.RuntimeTypeInfo)))
P_RCBOX_HEADER = lltype.Ptr(RCBOX_HEADER)
lltype.attachRuntimeTypeInfo(RCBOX_HEADER)


class CTypesRepr(Repr):
    "Base class for the Reprs representing ctypes object."

    # Attributes that are types:
    #
    #  * 'ctype'        is the ctypes type.
    #
    #  * 'll_type'      is the low-level type representing the raw C data,
    #                   like Signed or Array(...).
    #
    #  * 'c_data_type'  is a low-level container type that also represents
    #                   the raw C data; the difference is that we can take
    #                   an lltype pointer to it.  For primitives or pointers
    #                   this is a FixedSizeArray with a single item of
    #                   type 'll_type'.  Otherwise, c_data_type == ll_type.
    #
    #  * 'lowleveltype' is the Repr's choosen low-level type for the RPython
    #                   variables.  It's a Ptr to a GcStruct.  This is a box
    #                   traked by our GC around the raw 'c_data_type'-shaped
    #                   data.
    #
    #  * 'r_memoryowner.lowleveltype' is the lowleveltype of the repr for the
    #                                 same ctype but for ownsmemory=True.

    def __init__(self, rtyper, s_ctypesobject, ll_type):
        # s_ctypesobject: the annotation to represent
        # ll_type: the low-level type representing the raw
        #          data, which is then embedded in a box.
        ctype = s_ctypesobject.knowntype

        self.rtyper = rtyper
        self.ctype = ctype
        self.ll_type = ll_type
        self.ownsmemory = s_ctypesobject.ownsmemory

        self.c_data_type = self.get_c_data_type(ll_type)

        fields = [("c_data", lltype.Ptr(self.c_data_type))]
        content_keepalive_type = self.get_content_keepalive_type()
        if content_keepalive_type:
            fields.append(( "keepalive", content_keepalive_type ))

        if self.ownsmemory:
            self.autofree_fields = ("c_data",)
            self.r_memoryowner = self
        else:
            self.autofree_fields = ()
            s_memoryowner = SomeCTypesObject(ctype, ownsmemory=True)
            self.r_memoryowner = rtyper.getrepr(s_memoryowner)
            # the box that really owns our C data - it is usually a box of
            # type r_memoryowner.lowleveltype, but ocasionally it can be
            # any larger struct or array type and we only point somewhere
            # inside it
            fields.append(
                ( "c_data_owner_keepalive", P_RCBOX_HEADER ))

        if self.autofree_fields:
            fields.insert(0, ("header", RCBOX_HEADER))

        keywords = {'hints': {'autofree_fields': self.autofree_fields}}
        self.lowleveltype = lltype.Ptr(
                lltype.GcStruct( "CtypesBox_%s" % (ctype.__name__,),
                    *fields,
                    **keywords
                )
            )
        if self.autofree_fields:
            lltype.attachRuntimeTypeInfo(self.lowleveltype.TO)
        self.const_cache = {} # store generated const values+original value

    def _setup_repr_final(self):
        if self.autofree_fields:
            # XXX should be done by the gctransform from the GcStruct hint
            from pypy.annotation import model as annmodel
            from pypy.rpython.unroll import unrolling_iterable
            autofree_fields = unrolling_iterable(self.autofree_fields)

            def ll_rctypes_free(box):
                for fieldname in autofree_fields:
                    p = getattr(box, fieldname)
                    llmemory.raw_free(llmemory.cast_ptr_to_adr(p))

            args_s = [annmodel.SomePtr(P_RCBOX_HEADER)]
            graph = self.rtyper.annotate_helper(ll_rctypes_query, args_s)
            queryptr = self.rtyper.getcallable(graph)

            args_s = [annmodel.SomePtr(self.lowleveltype)]
            graph = self.rtyper.annotate_helper(ll_rctypes_free, args_s)
            destrptr = self.rtyper.getcallable(graph)
            lltype.attachRuntimeTypeInfo(self.lowleveltype.TO,
                                         queryptr, destrptr)

            # make sure the RCBOX_HEADER itself has got a query function
            lltype.attachRuntimeTypeInfo(RCBOX_HEADER, queryptr)

    def get_content_keepalive_type(self):
        """Return the type of the extra keepalive field used for the content
        of this object."""
        return None

    def get_extra_autofree_fields(self):
        return []

    def ctypecheck(self, value):
        return isinstance(value, self.ctype)

    def basic_instantiate_prebuilt(self):
        TYPE = self.lowleveltype.TO
        result = lltype.malloc(TYPE, immortal = True, zero = True)
        if self.autofree_fields:
            result.header.rtti = lltype.getRuntimeTypeInfo(TYPE)
        return result

    def genop_basic_instantiate(self, llops):
        # XXX the whole rtti business is a bit over-obscure
        TYPE = self.lowleveltype.TO
        c1 = inputconst(lltype.Void, TYPE)
        v_box = llops.genop("malloc", [c1], resulttype=self.lowleveltype)
        if self.autofree_fields:
            c_hdr = inputconst(lltype.Void, 'header')
            c_rtti = inputconst(lltype.Void, 'rtti')
            rtti = lltype.getRuntimeTypeInfo(TYPE)
            v_rtti = inputconst(lltype.typeOf(rtti), rtti)
            llops.genop("setinteriorfield", [v_box, c_hdr, c_rtti, v_rtti])
            for fieldname in self.autofree_fields:
                FIELDTYPE = getattr(TYPE, fieldname)
                c_name = inputconst(lltype.Void, fieldname)
                v_null = inputconst(FIELDTYPE, lltype.nullptr(FIELDTYPE.TO))
                llops.genop("setfield", [v_box, c_name, v_null])
        return v_box

    def convert_const(self, value):
        if self.ctypecheck(value):
            key = "by_id", id(value)
            keepalive = value
        else:
            if self.ownsmemory:
                raise TyperError("convert_const(%r) but repr owns memory" % (
                    value,))
            key = "by_value", value
            keepalive = None
        try:
            return self.const_cache[key][0]
        except KeyError:
            self.setup()
            p = self.r_memoryowner.basic_instantiate_prebuilt()
            p.c_data = lltype.malloc(self.r_memoryowner.c_data_type,
                                     immortal = True,
                                     zero = True)
            self.initialize_const(p, value)
            if self.ownsmemory:
                result = p
            else:
                # we must return a non-memory-owning box that keeps the
                # memory-owning box alive
                result = self.basic_instantiate_prebuilt()
                result.c_data = p.c_data    # initialize c_data pointer
                result.c_data_owner_keepalive = p.header
            self.const_cache[key] = result, keepalive
            return result

    def get_c_data(self, llops, v_box):
        inputargs = [v_box, inputconst(lltype.Void, "c_data")]
        return llops.genop('getfield', inputargs,
                           lltype.Ptr(self.c_data_type))

    def get_c_data_owner(self, llops, v_box):
        if self.ownsmemory:
            return llops.genop('cast_pointer', [v_box],
                               resulttype=P_RCBOX_HEADER)
        else:
            c_name = inputconst(lltype.Void, "c_data_owner_keepalive")
            return llops.genop('getfield', [v_box, c_name],
                               resulttype=P_RCBOX_HEADER)

    def allocate_instance(self, llops):
        v_box = self.genop_basic_instantiate(llops)
        TYPE = self.c_data_type
        if TYPE._is_varsize():
            raise TyperError("allocating array with unknown length")
        if self.ownsmemory:
            # XXX use zero=True instead, and malloc instead of raw_malloc?
            c_size = inputconst(lltype.Signed, llmemory.sizeof(TYPE))
            v_rawaddr = llops.genop("raw_malloc", [c_size],
                                    resulttype=llmemory.Address)
            llops.genop("raw_memclear", [v_rawaddr, c_size])
            v_rawdata = llops.genop("cast_adr_to_ptr", [v_rawaddr],
                                    resulttype=lltype.Ptr(TYPE))
            c_datafieldname = inputconst(lltype.Void, "c_data")
            llops.genop("setfield", [v_box, c_datafieldname, v_rawdata])
        return v_box

    def allocate_instance_varsize(self, llops, v_length):
        v_box = self.genop_basic_instantiate(llops)
        TYPE = self.c_data_type
        if not TYPE._is_varsize():
            raise TyperError("allocating non-array with specified length")
        if self.ownsmemory:
            # XXX use zero=True instead, and malloc instead of raw_malloc?
            assert isinstance(TYPE, lltype.Array)
            c_fixedsize = inputconst(lltype.Signed, llmemory.sizeof(TYPE, 0))
            c_itemsize = inputconst(lltype.Signed, llmemory.sizeof(TYPE.OF))
            v_varsize = llops.genop("int_mul", [c_itemsize, v_length],
                                    resulttype=lltype.Signed)
            v_size = llops.genop("int_add", [c_fixedsize, v_varsize],
                                 resulttype=lltype.Signed)
            v_rawaddr = llops.genop("raw_malloc", [v_size],
                                    resulttype=llmemory.Address)
            llops.genop("raw_memclear", [v_rawaddr, v_size])
            v_rawdata = llops.genop("cast_adr_to_ptr", [v_rawaddr],
                                    resulttype=lltype.Ptr(TYPE))
            c_datafieldname = inputconst(lltype.Void, "c_data")
            llops.genop("setfield", [v_box, c_datafieldname, v_rawdata])
        else:
            raise TyperError("allocate_instance_varsize on an alias box")
        return v_box

    def allocate_instance_ref(self, llops, v_c_data, v_c_data_owner):
        """Only if self.ownsmemory is false.  This allocates a new instance
        and initialize its c_data pointer."""
        if self.ownsmemory:
            raise TyperError("allocate_instance_ref: %r owns its memory" % (
                self,))
        v_box = self.allocate_instance(llops)
        inputargs = [v_box, inputconst(lltype.Void, "c_data"), v_c_data]
        llops.genop('setfield', inputargs)
        v_c_data_owner = cast_to_header(llops, v_c_data_owner)
        c_name = inputconst(lltype.Void, "c_data_owner_keepalive")
        llops.genop('setfield', [v_box, c_name, v_c_data_owner])
        return v_box

    def return_c_data(self, llops, v_c_data, v_c_data_owner):
        """Turn a raw C pointer to the data into a memory-alias box.
        Used when the data is returned from an operation or C function call.
        Special-cased in PrimitiveRepr.
        """
        return self.allocate_instance_ref(llops, v_c_data, v_c_data_owner)


class __extend__(pairtype(CTypesRepr, CTypesRepr)):

    def convert_from_to((r_from, r_to), v, llops):
        """Transparent conversion from the memory-owned to the memory-aliased
        version of the same ctypes repr."""
        if (r_from.ctype == r_to.ctype and
            r_from.ownsmemory and not r_to.ownsmemory):
            v_c_data = r_from.get_c_data(llops, v)
            v_result =  r_to.allocate_instance_ref(llops, v_c_data, v)
            # copy all the 'keepalive' information
            if hasattr(r_from.lowleveltype.TO, 'keepalive'):
                copykeepalive(llops, r_from.lowleveltype.TO.keepalive,
                              v, (), v_result, ())
            return v_result
        else:
            return NotImplemented


class CTypesRefRepr(CTypesRepr):
    """Base class for ctypes repr that have some kind of by-reference
    semantics, like structures and arrays."""

    def get_c_data_type(self, ll_type):
        assert isinstance(ll_type, lltype.ContainerType)
        return ll_type

    def get_c_data_or_value(self, llops, v_box):
        return self.get_c_data(llops, v_box)


class CTypesValueRepr(CTypesRepr):
    """Base class for ctypes repr that have some kind of by-value
    semantics, like primitives and pointers."""

    def get_c_data_type(self, ll_type):
        return lltype.FixedSizeArray(ll_type, 1)

    def getvalue_from_c_data(self, llops, v_c_data):
        return llops.genop('getarrayitem', [v_c_data, C_ZERO],
                resulttype=self.ll_type)

    def setvalue_inside_c_data(self, llops, v_c_data, v_value):
        llops.genop('setarrayitem', [v_c_data, C_ZERO, v_value])

    def getvalue(self, llops, v_box):
        """Reads from the 'value' field of the raw data."""
        v_c_data = self.get_c_data(llops, v_box)
        return self.getvalue_from_c_data(llops, v_c_data)

    def setvalue(self, llops, v_box, v_value):
        """Writes to the 'value' field of the raw data."""
        v_c_data = self.get_c_data(llops, v_box)
        self.setvalue_inside_c_data(llops, v_c_data, v_value)

    get_c_data_or_value = getvalue

    def initialize_const(self, p, value):
        if self.ctypecheck(value):
            value = value.value
        p.c_data[0] = value

    def return_value(self, llops, v_value, v_content_owner=None):
        # like return_c_data(), but when the input is only the value
        # field instead of the c_data pointer
        r_temp = self.r_memoryowner
        v_owned_box = r_temp.allocate_instance(llops)
        r_temp.setvalue(llops, v_owned_box, v_value)
        return llops.convertvar(v_owned_box, r_temp, self)

    def rtype_is_true(self, hop):
        [v_box] = hop.inputargs(self)
        v_value = self.getvalue(hop.llops, v_box)
        return hop.gendirectcall(ll_is_true, v_value)

# ____________________________________________________________

def ll_is_true(x):
    return bool(x)

C_ZERO = inputconst(lltype.Signed, 0)

def ll_rctypes_query(rcboxheader):
    return rcboxheader.rtti

def cast_to_header(llops, v_box):
    if v_box.concretetype != P_RCBOX_HEADER:
        assert v_box.concretetype.TO.header == RCBOX_HEADER
        v_box = llops.genop('cast_pointer', [v_box],
                            resulttype=P_RCBOX_HEADER)
    return v_box

def copykeepalive(llops, TYPE, v_box,     srcsuboffset,
                               v_destbox, destsuboffset):
    # copy (a part of) the 'keepalive' data over
    c_keepalive = inputconst(lltype.Void, 'keepalive')
    genreccopy_rel(llops, TYPE,
                   v_box,     (c_keepalive,) + srcsuboffset,
                   v_destbox, (c_keepalive,) + destsuboffset)

def reccopy(source, dest):
    # copy recursively a structure or array onto another.
    T = lltype.rawTypeOf(source).TO
    assert T == lltype.rawTypeOf(dest).TO
    if isinstance(T, (lltype.Array, lltype.FixedSizeArray)):
        assert source._obj.getlength() == dest._obj.getlength()
        ITEMTYPE = T.OF
        for i in range(source._obj.getlength()):
            if isinstance(ITEMTYPE, lltype.ContainerType):
                subsrc = source[i]
                subdst = dest[i]
                reccopy(subsrc, subdst)
            else:
                # this is a hack XXX de-hack this
                llvalue = source._obj.getitem(i, uninitialized_ok=True)
                dest._obj.setitem(i, llvalue)
    elif isinstance(T, lltype.Struct):
        for name in T._names:
            FIELDTYPE = getattr(T, name)
            if isinstance(FIELDTYPE, lltype.ContainerType):
                subsrc = getattr(source, name)
                subdst = getattr(dest,   name)
                reccopy(subsrc, subdst)
            else:
                # this is a hack XXX de-hack this
                llvalue = source._obj._getattr(name, uninitialized_ok=True)
                setattr(dest._obj, name, llvalue)
    else:
        raise TypeError(T)

def reccopy_arrayitem(source, destarray, destindex):
    ITEMTYPE = lltype.rawTypeOf(destarray).TO.OF
    if isinstance(ITEMTYPE, lltype.Primitive):
        destarray[destindex] = source
    else:
        reccopy(source, destarray[destindex])

def enum_interior_offsets(T, prefix=()):
    # generate all (offsets-tuple, FIELD_TYPE) for all interior fields
    # in TYPE and in substructs of TYPE.  Not for arrays so far.

    if isinstance(T, lltype.ContainerType):
        if isinstance(T, lltype.FixedSizeArray):
            # XXX don't do that if the length is large
            ITEMTYPE = T.OF
            for i in range(T.length):
                c_i = inputconst(lltype.Signed, i)
                offsets = prefix + (c_i,)
                for access in enum_interior_offsets(ITEMTYPE, offsets):
                    yield access

        elif isinstance(T, lltype.Array):
            raise NotImplementedError("XXX genreccopy() for arrays")

        elif isinstance(T, lltype.Struct):
            for name in T._names:
                FIELDTYPE = getattr(T, name)
                cname = inputconst(lltype.Void, name)
                offsets = prefix + (cname,)
                for access in enum_interior_offsets(FIELDTYPE, offsets):
                    yield access

        else:
            raise TypeError(T)

    else:
        yield prefix, T


def genreccopy_rel(llops, TYPE, v_source, sourceoffsets, v_dest, destoffsets):
    # helper to generate the llops that copy recursively a structure
    # or array onto another.  The copy starts at the given tuple-of-offsets
    # prefixes, e.g. (Constant(5),) to mean the 5th sub-element of a
    # fixed-size array.  This function doesn't work for general arrays yet.
    # It works with primitive types too, as long as destoffsets != ().

    for offsets, FIELDTYPE in enum_interior_offsets(TYPE):
        if sourceoffsets or offsets:
            args = [v_source]
            args.extend(sourceoffsets)
            args.extend(offsets)
            v_value = llops.genop('getinteriorfield', args,
                                  resulttype=FIELDTYPE)
        else:
            v_value = v_source
        if destoffsets or offsets:
            args = [v_dest]
            args.extend(destoffsets)
            args.extend(offsets)
            args.append(v_value)
            llops.genop('setinteriorfield', args)
        else:
            assert TYPE == v_dest.concretetype
            raise TypeError("cannot copy into a v_dest of type %r" % (TYPE,))

def genreccopy(llops, v_source, v_dest):
    TYPE = v_source.concretetype.TO
    assert TYPE == v_dest.concretetype.TO
    genreccopy_rel(llops, TYPE, v_source, (), v_dest, ())

def genreccopy_arrayitem(llops, v_source, v_destarray, v_destindex):
    ITEMTYPE = v_destarray.concretetype.TO.OF
    if isinstance(ITEMTYPE, lltype.ContainerType):
        # copy into the array's substructure
        assert ITEMTYPE == v_source.concretetype.TO
    else:
        # copy a primitive or pointer value into the array item
        assert ITEMTYPE == v_source.concretetype
    genreccopy_rel(llops, ITEMTYPE, v_source, (), v_destarray, (v_destindex,))

def genreccopy_structfield(llops, v_source, v_deststruct, fieldname):
    c_name = inputconst(lltype.Void, fieldname)
    FIELDTYPE = getattr(v_deststruct.concretetype.TO, fieldname)
    if isinstance(FIELDTYPE, lltype.ContainerType):
        # copy into the substructure
        assert FIELDTYPE == v_source.concretetype.TO
    else:
        # copy a primitive or pointer value into the struct field
        assert FIELDTYPE == v_source.concretetype
    genreccopy_rel(llops, FIELDTYPE, v_source, (), v_deststruct, (c_name,))
