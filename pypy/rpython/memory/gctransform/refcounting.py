import py
from pypy.rpython.memory.gctransform.transform import GCTransformer
from pypy.rpython.memory.gctransform.transform import mallocHelpers, RTTIPTR
from pypy.rpython.memory.gctransform.support import find_gc_ptrs_in_type, \
     _static_deallocator_body_for_type, LLTransformerOp, ll_call_destructor
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.translator.backendopt.support import var_needsgc
from pypy.rpython import rmodel
from pypy.rlib.rarithmetic import ovfcheck
from pypy.rlib.debug import ll_assert
from pypy.rpython.rbuiltin import gen_cast
import sys

counts = {}

## def print_call_chain(ob):
##     import sys
##     f = sys._getframe(1)
##     stack = []
##     flag = False
##     while f:
##         if f.f_locals.get('self') is ob:
##             stack.append((f.f_code.co_name, f.f_locals.get('TYPE')))
##             if not flag:
##                 counts[f.f_code.co_name] = counts.get(f.f_code.co_name, 0) + 1
##                 print counts
##                 flag = True
##         f = f.f_back
##     stack.reverse()
##     for i, (a, b) in enumerate(stack):
##         print ' '*i, a, repr(b)[:100-i-len(a)], id(b)

ADDRESS_VOID_FUNC = lltype.FuncType([llmemory.Address], lltype.Void)

class RefcountingGCTransformer(GCTransformer):

    # xxx not all objects need a typeptr, but refcounting is a bit
    # deprecated now, being not efficient at all
    HDR = lltype.Struct("header", ("refcount", lltype.Signed),
                                  ("typeptr", RTTIPTR))

    TYPEINFO = lltype.Struct("typeinfo",
                             ("dealloc", lltype.Ptr(ADDRESS_VOID_FUNC)))

    def __init__(self, translator):
        super(RefcountingGCTransformer, self).__init__(translator, inline=True)
        self.deallocator_graphs_needing_transforming = []

        # create incref, etc  graph

        gchelpers = self.gchelpers
        gc_header_offset = gchelpers.gc_header_offset
        HDRPTR = lltype.Ptr(self.HDR)

        def ll_incref(adr):
            if adr:
                gcheader = gchelpers.header(adr)
                gcheader.refcount = gcheader.refcount + 1
        def ll_decref(adr):
            if adr:
                gcheader = gchelpers.header(adr)
                refcount = gcheader.refcount - 1
                gcheader.refcount = refcount
                if refcount == 0:
                    typeinfo = gchelpers.typeof(adr)
                    typeinfo.dealloc(adr)

        def ll_no_pointer_dealloc(adr):
            llmemory.raw_free(adr)

        mh = mallocHelpers()
        mh.allocate = llmemory.raw_malloc
        def ll_malloc_fixedsize(size):
            size = gc_header_offset + size
            result = mh._ll_malloc_fixedsize(size)
            llmemory.raw_memclear(result, size)
            result += gc_header_offset
            return result
        def ll_malloc_fixedsize_rtti(size, rtti):
            size = gc_header_offset + size
            result = mh._ll_malloc_fixedsize(size)
            llmemory.raw_memclear(result, size)
            llmemory.cast_adr_to_ptr(result, HDRPTR).typeptr = rtti
            result += gc_header_offset
            return result
        def ll_malloc_varsize_no_length_rtti(length, size, itemsize, rtti):
            try:
                fixsize = gc_header_offset + size
                varsize = ovfcheck(itemsize * length)
                tot_size = ovfcheck(fixsize + varsize)
            except OverflowError:
                raise MemoryError()
            result = mh._ll_malloc_fixedsize(tot_size)
            llmemory.raw_memclear(result, tot_size)
            llmemory.cast_adr_to_ptr(result, HDRPTR).typeptr = rtti
            result += gc_header_offset
            return result
        def ll_malloc_varsize_rtti(length, size, itemsize, lengthoffset, rtti):
            result = ll_malloc_varsize_no_length_rtti(length, size,
                                                      itemsize, rtti)
            (result + lengthoffset).signed[0] = length
            return result

        if self.translator:
            self.increfptr = self.inittime_helper(
                ll_incref, [llmemory.Address], lltype.Void)
            self.decrefptr = self.inittime_helper(
                ll_decref, [llmemory.Address], lltype.Void)
            self.no_pointer_dealloc_ptr = self.inittime_helper(
                ll_no_pointer_dealloc, [llmemory.Address], lltype.Void)
            self.malloc_fixedsize_ptr = self.inittime_helper(
                ll_malloc_fixedsize_rtti, [lltype.Signed, RTTIPTR],
                llmemory.Address)
            self.malloc_varsize_no_length_ptr = self.inittime_helper(
                ll_malloc_varsize_no_length_rtti, [lltype.Signed]*3+[RTTIPTR],
                llmemory.Address)
            self.malloc_varsize_ptr = self.inittime_helper(
                ll_malloc_varsize_rtti, [lltype.Signed]*4+[RTTIPTR],
                llmemory.Address)
            self.mixlevelannotator.finish()
            self.mixlevelannotator.backend_optimize()
        # cache graphs:
        self.static_deallocator_funcptrs = {}

    def finish_helpers(self, **kwds):
        GCTransformer.finish_helpers(self, **kwds)
        from pypy.translator.backendopt.malloc import remove_mallocs
        seen = {}
        graphs = []
        for fptr in self.static_deallocator_funcptrs.itervalues():
            graph = fptr._obj.graph
            if graph in seen:
                continue
            seen[graph] = True
            graphs.append(graph)
        remove_mallocs(self.translator, graphs)

    def var_needs_set_transform(self, var):
        return var_needsgc(var)

    def push_alive_nopyobj(self, var, llops):
        v_adr = gen_cast(llops, llmemory.Address, var)
        llops.genop("direct_call", [self.increfptr, v_adr])

    def pop_alive_nopyobj(self, var, llops):
        v_adr = gen_cast(llops, llmemory.Address, var)
        llops.genop("direct_call", [self.decrefptr, v_adr])

    def gct_fv_gc_malloc(self, hop, flags, TYPE, c_size):
        rtti = lltype.getRuntimeTypeInfo(TYPE, self.rtticache)
        c_rtti = rmodel.inputconst(RTTIPTR, rtti)
        v_raw = hop.genop("direct_call",
                          [self.malloc_fixedsize_ptr, c_size, c_rtti],
                          resulttype=llmemory.Address)
        return v_raw

    def gct_fv_gc_malloc_varsize(self, hop, flags, TYPE, v_length, c_const_size, c_item_size,
                                                                   c_offset_to_length):
        rtti = lltype.getRuntimeTypeInfo(TYPE, self.rtticache)
        c_rtti = rmodel.inputconst(RTTIPTR, rtti)
        if c_offset_to_length is None:
            v_raw = hop.genop("direct_call",
                               [self.malloc_varsize_no_length_ptr, v_length,
                                c_const_size, c_item_size, c_rtti],
                               resulttype=llmemory.Address)
        else:
            v_raw = hop.genop("direct_call",
                               [self.malloc_varsize_ptr, v_length,
                                c_const_size, c_item_size, c_offset_to_length,
                                c_rtti],
                               resulttype=llmemory.Address)
        return v_raw

    def static_deallocation_funcptr_for_type(self, TYPE):
        """The 'static deallocator' for a type is the function that can
        free a pointer that we know points exactly to a TYPE structure
        (and not to a larger structure that starts with TYPE).  This
        function is the one that ends up in the 'dealloc' field of
        TYPEINFO.
        """
        if TYPE in self.static_deallocator_funcptrs:
            return self.static_deallocator_funcptrs[TYPE]
        #print_call_chain(self)

        if TYPE._gckind == 'cpy':
            return # you don't really have an RPython deallocator for PyObjects
        assert TYPE._gckind == 'gc'

        rtti = lltype.getRuntimeTypeInfo(TYPE, self.rtticache)
        destrptr = rtti.destructor_funcptr
        if destrptr is not None:
            DESTR_ARG = lltype.typeOf(destrptr).TO.ARGS[0]
        else:
            DESTR_ARG = None

        if destrptr is None and not find_gc_ptrs_in_type(TYPE):
            p = self.no_pointer_dealloc_ptr.value
            self.static_deallocator_funcptrs[TYPE] = p
            return p

        if destrptr is not None:
            body = '\n'.join(_static_deallocator_body_for_type('v', TYPE, 3))
            src = """
def ll_deallocator(addr):
    exc_instance = llop.gc_fetch_exception(EXC_INSTANCE_TYPE)
    try:
        v = llmemory.cast_adr_to_ptr(addr, PTR_TYPE)
        gcheader = llmemory.cast_adr_to_ptr(addr - gc_header_offset, HDRPTR)
        # refcount is at zero, temporarily bump it to 1:
        gcheader.refcount = 1
        destr_v = lltype.cast_pointer(DESTR_ARG, v)
        ll_call_destructor(destrptr, destr_v)
        refcount = gcheader.refcount - 1
        gcheader.refcount = refcount
        if refcount == 0:
%s
            llmemory.raw_free(addr)
    except:
        pass
    llop.gc_restore_exception(lltype.Void, exc_instance)
    pop_alive(exc_instance)
    # XXX layering of exceptiontransform versus gcpolicy

""" % (body,)
        else:
            call_del = None
            body = '\n'.join(_static_deallocator_body_for_type('v', TYPE))
            src = ('def ll_deallocator(addr):\n' +
                   '    v = llmemory.cast_adr_to_ptr(addr, PTR_TYPE)\n' +
                   body + '\n' +
                   '    llmemory.raw_free(addr)\n')
        d = {'pop_alive': LLTransformerOp(self.pop_alive),
             'llop': llop,
             'lltype': lltype,
             'destrptr': destrptr,
             'gc_header_offset': self.gcheaderbuilder.size_gc_header,
             'llmemory': llmemory,
             'PTR_TYPE': lltype.Ptr(TYPE),
             'DESTR_ARG': DESTR_ARG,
             'EXC_INSTANCE_TYPE': self.translator.rtyper.exceptiondata.lltype_of_exception_value,
             'll_call_destructor': ll_call_destructor,
             'HDRPTR':lltype.Ptr(self.HDR)}
        exec src in d
        this = d['ll_deallocator']
        fptr = self.annotate_finalizer(this, [llmemory.Address], lltype.Void)
        self.static_deallocator_funcptrs[TYPE] = fptr
        for p in find_gc_ptrs_in_type(TYPE):
            self.static_deallocation_funcptr_for_type(p.TO)
        return fptr

    def initialize_constant_header(self, hdr, TYPE, value):
        hdr.refcount = sys.maxint // 2

    def initialize_typeinfo(self, typeinfo, rtti, TYPE):
        fn = self.static_deallocation_funcptr_for_type(TYPE)
        typeinfo.dealloc = fn
