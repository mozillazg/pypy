import weakref
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rlib.debug import ll_assert


# this is global because a header cannot be a header of more than one GcObj
header2obj = weakref.WeakKeyDictionary()


class GCHeaderBuilder(object):

    def __init__(self, HDR, TYPEINFO):
        """NOT_RPYTHON"""
        self.HDR = HDR
        self.TYPEINFO = TYPEINFO
        self.obj2header = weakref.WeakKeyDictionary()
        self.rtti2typeinfo = weakref.WeakKeyDictionary()
        self.size_gc_header = llmemory.GCHeaderOffset(self)
        self.size_gc_typeinfo = llmemory.GCTypeInfoOffset(self)
        self.rtticache = {}

    def header_of_object(self, gcptr):
        # XXX hackhackhack
        gcptr = gcptr._as_obj()
        if isinstance(gcptr, llmemory._gctransformed_wref):
            return self.obj2header[gcptr._ptr._as_obj()]
        return self.obj2header[gcptr]

    def object_from_header(headerptr):
        return header2obj[headerptr._as_obj()]
    object_from_header = staticmethod(object_from_header)

    def get_header(self, gcptr):
        return self.obj2header.get(gcptr._as_obj(), None)

    def attach_header(self, gcptr, headerptr):
        gcobj = gcptr._as_obj()
        assert gcobj not in self.obj2header
        # sanity checks
        assert gcobj._TYPE._gckind == 'gc'
        assert not isinstance(gcobj._TYPE, lltype.GcOpaqueType)
        assert not gcobj._parentstructure()
        self.obj2header[gcobj] = headerptr
        header2obj[headerptr._obj] = gcptr._as_ptr()

    def new_header(self, gcptr):
        headerptr = lltype.malloc(self.HDR, immortal=True)
        self.attach_header(gcptr, headerptr)
        return headerptr

    def typeinfo_from_rtti(self, rttiptr):
        rttiptr = lltype.cast_pointer(lltype.Ptr(lltype.RuntimeTypeInfo),
                                      rttiptr)
        return self.rtti2typeinfo[rttiptr._obj]

    def new_typeinfo(self, rttiptr):
        rttiptr = lltype.cast_pointer(lltype.Ptr(lltype.RuntimeTypeInfo),
                                      rttiptr)
        rtti = rttiptr._obj
        assert rtti not in self.rtti2typeinfo
        typeinfo = lltype.malloc(self.TYPEINFO, immortal=True)
        self.rtti2typeinfo[rtti] = typeinfo
        return typeinfo

    def cast_rtti_to_typeinfo(self, rttiptr):
        # this is RPython
        ll_assert(bool(rttiptr), "NULL rtti pointer")
        addr = llmemory.cast_ptr_to_adr(rttiptr)
        addr += self.size_gc_typeinfo
        return llmemory.cast_adr_to_ptr(addr, lltype.Ptr(self.TYPEINFO))

    def getRtti(self, TYPE):
        return lltype.getRuntimeTypeInfo(TYPE, self.rtticache)

    def _freeze_(self):
        return True     # for reads of size_gc_header
