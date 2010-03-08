from pypy.jit.backend.llsupport.gc import GcLLDescription
from pypy.rlib.debug import fatalerror
from pypy.rpython.lltypesystem import lltype, llmemory, rffi, rstr
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.annlowlevel import llhelper
from pypy.jit.metainterp.history import BoxPtr, ConstPtr
from pypy.jit.metainterp.history import AbstractDescr
from pypy.jit.metainterp.resoperation import ResOperation, rop
from pypy.jit.backend.llsupport import symbolic
from pypy.jit.backend.llsupport.descr import BaseSizeDescr, BaseArrayDescr
from pypy.jit.backend.llsupport.descr import get_field_descr
from pypy.jit.backend.llsupport.descr import GcPtrFieldDescr
from pypy.jit.backend.llsupport.descr import get_call_descr
from pypy.rlib.rarithmetic import r_ulonglong, r_uint

from pypy.rpython.memory import gctypelayout
from pypy.rpython.memory.gctypelayout import _check_typeid
from pypy.rpython.memory.gcheader import GCHeaderBuilder
from pypy.rpython.memory.gctransform import framework


# ____________________________________________________________
# All code below is for our framework GCs


class GcRefHandler:
    """Handles all constant GCREFs stored in the assembler.
    This includes the fact that some of these constants may end up stored
    with an extra offset, e.g. as the address out of which a GETFIELD_GC
    on them should fetch data.
    """
    # The idea is to store in an array of type CONSTGCREF_ARRAY a list
    # of pairs (gcref, addr), where 'gcref' is some GC-tracked object,
    # and 'addr' is the address in the assembler where 'gcref' was used.
    # This usually means that 'gcref' is currently stored at 'addr', but
    # it may also be the case that there is a small offset; e.g. a
    # GETFIELD_GC(ConstPtr(0x123450), descr=<offset 8>) will end up as
    # an assembler instruction like MOV EAX, [0x123458].
    #
    CONSTGCREF_ARRAY = lltype.GcArray(("gcref", llmemory.GCREF),
                                      ("addr", llmemory.Address))
    gcrefarray_lengthoffset = llmemory.ArrayLengthOffset(CONSTGCREF_ARRAY)
    gcrefarray_itemsoffset = llmemory.ArrayItemsOffset(CONSTGCREF_ARRAY)
    gcrefarray_singleitemoffset = llmemory.ItemOffset(CONSTGCREF_ARRAY.OF)
    gcrefarrayitem_gcref = llmemory.offsetof(CONSTGCREF_ARRAY.OF, "gcref")
    gcrefarrayitem_addr  = llmemory.offsetof(CONSTGCREF_ARRAY.OF, "addr")

    def __init__(self, layoutbuilder):
        self.constgcref_array_type_id = layoutbuilder.get_type_id(
            self.CONSTGCREF_ARRAY)
        self.full_constgcref_array_type_id = llop.combine_ushort(
            lltype.Signed,
            self.constgcref_array_type_id,
            0)

    def _freeze_(self):
        return True

    def start_tracing_varsized_part(self, obj, typeid):
        """Called by the GC just before tracing the object 'obj'."""
        fulltypeid = llop.combine_ushort(lltype.Signed, typeid, 0)
        if fulltypeid == self.full_constgcref_array_type_id:
            self.do_start_stop_tracing(obj, False)

    def stop_tracing_varsized_part(self, obj, typeid):
        """Called by the GC just after tracing the object 'obj'."""
        fulltypeid = llop.combine_ushort(lltype.Signed, typeid, 0)
        if fulltypeid == self.full_constgcref_array_type_id:
            self.do_start_stop_tracing(obj, True)

    def do_start_stop_tracing(self, obj, done):
        # Before tracing an object of type CONSTGCREF_ARRAY
        # (done=False), we take all addresses in the assembler and
        # subtract the gcrefs from them.  This leaves the assembler in a
        # broken state: the numbers in the assembler now are just the
        # offsets from the start of the objects.  After tracing
        # (done=True), we add again the gcrefs to the addresses in the
        # assembler, fixing up the numbers.  For any object that moved,
        # that object's address in the assembler is now fixed.
        length = (obj + self.gcrefarray_lengthoffset).signed[0]
        item = obj + self.gcrefarray_itemsoffset
        while length > 0:
            gcref = (item + self.gcrefarrayitem_gcref).address[0]
            if gcref:
                gcref = llmemory.cast_adr_to_int(gcref)
                addr = (item + self.gcrefarrayitem_addr).address[0]
                if done:
                    addr.signed[0] += gcref
                else:
                    addr.signed[0] -= gcref
            item += self.gcrefarray_singleitemoffset
            length -= 1
    do_start_stop_tracing._dont_inline_ = True
    do_start_stop_tracing._annspecialcase_ = 'specialize:arg(2)'


class GcRootMap_asmgcc:
    """Handles locating the stack roots in the assembler.
    This is the class supporting --gcrootfinder=asmgcc.
    """
    LOC_REG       = 0
    LOC_ESP_PLUS  = 1
    LOC_EBP_PLUS  = 2
    LOC_EBP_MINUS = 3

    GCMAP_ARRAY = rffi.CArray(llmemory.Address)
    CALLSHAPE_ARRAY = rffi.CArray(rffi.UCHAR)

    def __init__(self):
        self._gcmap = lltype.nullptr(self.GCMAP_ARRAY)
        self._gcmap_curlength = 0
        self._gcmap_maxlength = 0

    def initialize(self):
        # hack hack hack.  Remove these lines and see MissingRTypeAttribute
        # when the rtyper tries to annotate these methods only when GC-ing...
        self.gcmapstart()
        self.gcmapend()

    def gcmapstart(self):
        return llmemory.cast_ptr_to_adr(self._gcmap)

    def gcmapend(self):
        addr = self.gcmapstart()
        if self._gcmap_curlength:
            addr += llmemory.sizeof(llmemory.Address)*self._gcmap_curlength
        return addr

    def put(self, retaddr, callshapeaddr):
        """'retaddr' is the address just after the CALL.
        'callshapeaddr' is the address returned by encode_callshape()."""
        index = self._gcmap_curlength
        if index + 2 > self._gcmap_maxlength:
            self._enlarge_gcmap()
        self._gcmap[index] = retaddr
        self._gcmap[index+1] = callshapeaddr
        self._gcmap_curlength = index + 2

    def _enlarge_gcmap(self):
        newlength = 250 + self._gcmap_maxlength * 2
        newgcmap = lltype.malloc(self.GCMAP_ARRAY, newlength, flavor='raw')
        oldgcmap = self._gcmap
        for i in range(self._gcmap_curlength):
            newgcmap[i] = oldgcmap[i]
        self._gcmap = newgcmap
        self._gcmap_maxlength = newlength
        if oldgcmap:
            lltype.free(oldgcmap, flavor='raw')

    def get_basic_shape(self):
        return [chr(self.LOC_EBP_PLUS  | 4),    # return addr: at   4(%ebp)
                chr(self.LOC_EBP_MINUS | 4),    # saved %ebx:  at  -4(%ebp)
                chr(self.LOC_EBP_MINUS | 8),    # saved %esi:  at  -8(%ebp)
                chr(self.LOC_EBP_MINUS | 12),   # saved %edi:  at -12(%ebp)
                chr(self.LOC_EBP_PLUS  | 0),    # saved %ebp:  at    (%ebp)
                chr(0)]

    def _encode_num(self, shape, number):
        assert number >= 0
        flag = 0
        while number >= 0x80:
            shape.append(chr((number & 0x7F) | flag))
            flag = 0x80
            number >>= 7
        shape.append(chr(number | flag))

    def add_ebp_offset(self, shape, offset):
        assert (offset & 3) == 0
        if offset >= 0:
            num = self.LOC_EBP_PLUS | offset
        else:
            num = self.LOC_EBP_MINUS | (-offset)
        self._encode_num(shape, num)

    def add_ebx(self, shape):
        shape.append(chr(self.LOC_REG | 4))

    def add_esi(self, shape):
        shape.append(chr(self.LOC_REG | 8))

    def add_edi(self, shape):
        shape.append(chr(self.LOC_REG | 12))

    def add_ebp(self, shape):
        shape.append(chr(self.LOC_REG | 16))

    def compress_callshape(self, shape):
        # Similar to compress_callshape() in trackgcroot.py.
        # XXX so far, we always allocate a new small array (we could regroup
        # them inside bigger arrays) and we never try to share them.
        length = len(shape)
        compressed = lltype.malloc(self.CALLSHAPE_ARRAY, length,
                                   flavor='raw')
        for i in range(length):
            compressed[length-1-i] = rffi.cast(rffi.UCHAR, shape[i])
        return llmemory.cast_ptr_to_adr(compressed)


class WriteBarrierDescr(AbstractDescr):
    def __init__(self, gc_ll_descr):
        self.llop1 = gc_ll_descr.llop1
        self.WB_FUNCPTR = gc_ll_descr.WB_FUNCPTR
        self.fielddescr_tid = get_field_descr(gc_ll_descr,
                                              gc_ll_descr.GCClass.HDR, 'tid')
        self.jit_wb_if_flag = gc_ll_descr.GCClass.JIT_WB_IF_FLAG
        # if convenient for the backend, we also compute the info about
        # the flag as (byte-offset, single-byte-flag).
        import struct
        value = struct.pack("i", self.jit_wb_if_flag)
        assert value.count('\x00') == len(value) - 1    # only one byte is != 0
        i = 0
        while value[i] == '\x00': i += 1
        self.jit_wb_if_flag_byteofs = i
        self.jit_wb_if_flag_singlebyte = struct.unpack('b', value[i])[0]

    def get_write_barrier_fn(self, cpu):
        llop1 = self.llop1
        funcptr = llop1.get_write_barrier_failing_case(self.WB_FUNCPTR)
        funcaddr = llmemory.cast_ptr_to_adr(funcptr)
        return cpu.cast_adr_to_int(funcaddr)


class GcLLDescr_framework(GcLLDescription):

    def __init__(self, gcdescr, translator, llop1=llop):
        GcLLDescription.__init__(self, gcdescr, translator)
        assert self.translate_support_code, "required with the framework GC"
        self.translator = translator
        self.llop1 = llop1

        # to find roots in the assembler, make a GcRootMap
        name = gcdescr.config.translation.gcrootfinder
        try:
            cls = globals()['GcRootMap_' + name]
        except KeyError:
            raise NotImplementedError("--gcrootfinder=%s not implemented"
                                      " with the JIT" % (name,))
        gcrootmap = cls()
        self.gcrootmap = gcrootmap

        # make a TransformerLayoutBuilder and save it on the translator
        # where it can be fished and reused by the FrameworkGCTransformer
        self.layoutbuilder = framework.TransformerLayoutBuilder(translator)
        self.layoutbuilder.delay_encoding()
        self.gcrefhandler = GcRefHandler(self.layoutbuilder)
        self.translator._jit2gc = {
            'layoutbuilder': self.layoutbuilder,
            'gcmapstart': lambda: gcrootmap.gcmapstart(),
            'gcmapend': lambda: gcrootmap.gcmapend(),
            'start_tracing_varsized_part':
                               self.gcrefhandler.start_tracing_varsized_part,
            'stop_tracing_varsized_part':
                               self.gcrefhandler.stop_tracing_varsized_part,
            }
        self.GCClass = self.layoutbuilder.GCClass
        self.moving_gc = self.GCClass.moving_gc
        self.HDRPTR = lltype.Ptr(self.GCClass.HDR)
        self.gcheaderbuilder = GCHeaderBuilder(self.HDRPTR.TO)
        (self.array_basesize, _, self.array_length_ofs) = \
             symbolic.get_array_token(lltype.GcArray(lltype.Signed), True)
        min_ns = self.GCClass.TRANSLATION_PARAMS['min_nursery_size']
        self.max_size_of_young_obj = self.GCClass.get_young_fixedsize(min_ns)

        # make a malloc function, with three arguments
        def malloc_basic(size, tid):
            type_id = llop.extract_ushort(rffi.USHORT, tid)
            has_finalizer = bool(tid & (1<<16))
            _check_typeid(type_id)
            try:
                res = llop1.do_malloc_fixedsize_clear(llmemory.GCREF,
                                                      type_id, size, True,
                                                      has_finalizer, False)
            except MemoryError:
                fatalerror("out of memory (from JITted code)")
                res = lltype.nullptr(llmemory.GCREF.TO)
            #llop.debug_print(lltype.Void, "\tmalloc_basic", size, type_id,
            #                 "-->", res)
            return res
        self.malloc_basic = malloc_basic
        self.GC_MALLOC_BASIC = lltype.Ptr(lltype.FuncType(
            [lltype.Signed, lltype.Signed], llmemory.GCREF))
        self.WB_FUNCPTR = lltype.Ptr(lltype.FuncType(
            [llmemory.Address, llmemory.Address], lltype.Void))
        self.write_barrier_descr = WriteBarrierDescr(self)
        #
        def malloc_array(itemsize, tid, num_elem):
            type_id = llop.extract_ushort(rffi.USHORT, tid)
            _check_typeid(type_id)
            try:
                return llop1.do_malloc_varsize_clear(
                    llmemory.GCREF,
                    type_id, num_elem, self.array_basesize, itemsize,
                    self.array_length_ofs, True)
            except MemoryError:
                fatalerror("out of memory (from JITted code)")
                return lltype.nullptr(llmemory.GCREF.TO)
        self.malloc_array = malloc_array
        self.GC_MALLOC_ARRAY = lltype.Ptr(lltype.FuncType(
            [lltype.Signed] * 3, llmemory.GCREF))
        #
        (str_basesize, str_itemsize, str_ofs_length
         ) = symbolic.get_array_token(rstr.STR, True)
        (unicode_basesize, unicode_itemsize, unicode_ofs_length
         ) = symbolic.get_array_token(rstr.UNICODE, True)
        str_type_id = self.layoutbuilder.get_type_id(rstr.STR)
        unicode_type_id = self.layoutbuilder.get_type_id(rstr.UNICODE)
        #
        def malloc_str(length):
            try:
                return llop1.do_malloc_varsize_clear(
                    llmemory.GCREF,
                    str_type_id, length, str_basesize, str_itemsize,
                    str_ofs_length, True)
            except MemoryError:
                fatalerror("out of memory (from JITted code)")
                return lltype.nullptr(llmemory.GCREF.TO)
        def malloc_unicode(length):
            try:
                return llop1.do_malloc_varsize_clear(
                    llmemory.GCREF,
                    unicode_type_id, length, unicode_basesize,unicode_itemsize,
                    unicode_ofs_length, True)
            except MemoryError:
                fatalerror("out of memory (from JITted code)")
                return lltype.nullptr(llmemory.GCREF.TO)
        self.malloc_str = malloc_str
        self.malloc_unicode = malloc_unicode
        self.GC_MALLOC_STR_UNICODE = lltype.Ptr(lltype.FuncType(
            [lltype.Signed], llmemory.GCREF))
        def malloc_fixedsize_slowpath(size):
            try:
                gcref = llop1.do_malloc_fixedsize_clear(llmemory.GCREF,
                                            0, size, True, False, False)
            except MemoryError:
                fatalerror("out of memory (from JITted code)")
                return r_ulonglong(0)
            res = rffi.cast(lltype.Signed, gcref)
            nurs_free = llop1.gc_adr_of_nursery_free(llmemory.Address).signed[0]
            return r_ulonglong(nurs_free) << 32 | r_ulonglong(r_uint(res))
        self.malloc_fixedsize_slowpath = malloc_fixedsize_slowpath
        self.MALLOC_FIXEDSIZE_SLOWPATH = lltype.FuncType([lltype.Signed],
                                                 lltype.UnsignedLongLong)

    def get_nursery_free_addr(self):
        nurs_addr = llop.gc_adr_of_nursery_free(llmemory.Address)
        return rffi.cast(lltype.Signed, nurs_addr)

    def get_nursery_top_addr(self):
        nurs_top_addr = llop.gc_adr_of_nursery_top(llmemory.Address)
        return rffi.cast(lltype.Signed, nurs_top_addr)

    def get_malloc_fixedsize_slowpath_addr(self):
        fptr = llhelper(lltype.Ptr(self.MALLOC_FIXEDSIZE_SLOWPATH),
                        self.malloc_fixedsize_slowpath)
        return rffi.cast(lltype.Signed, fptr)

    def initialize(self):
        self.gcrootmap.initialize()

    def init_size_descr(self, S, descr):
        type_id = self.layoutbuilder.get_type_id(S)
        assert not self.layoutbuilder.is_weakref(type_id)
        has_finalizer = bool(self.layoutbuilder.has_finalizer(S))
        flags = int(has_finalizer) << 16
        descr.tid = llop.combine_ushort(lltype.Signed, type_id, flags)

    def init_array_descr(self, A, descr):
        type_id = self.layoutbuilder.get_type_id(A)
        descr.tid = llop.combine_ushort(lltype.Signed, type_id, 0)

    def gc_malloc(self, sizedescr):
        assert isinstance(sizedescr, BaseSizeDescr)
        return self.malloc_basic(sizedescr.size, sizedescr.tid)

    def gc_malloc_array(self, arraydescr, num_elem):
        assert isinstance(arraydescr, BaseArrayDescr)
        itemsize = arraydescr.get_item_size(self.translate_support_code)
        return self.malloc_array(itemsize, arraydescr.tid, num_elem)

    def gc_malloc_str(self, num_elem):
        return self.malloc_str(num_elem)

    def gc_malloc_unicode(self, num_elem):
        return self.malloc_unicode(num_elem)

    def args_for_new(self, sizedescr):
        assert isinstance(sizedescr, BaseSizeDescr)
        return [sizedescr.size, sizedescr.tid]

    def args_for_new_array(self, arraydescr):
        assert isinstance(arraydescr, BaseArrayDescr)
        itemsize = arraydescr.get_item_size(self.translate_support_code)
        return [itemsize, arraydescr.tid]

    def get_funcptr_for_new(self):
        return llhelper(self.GC_MALLOC_BASIC, self.malloc_basic)

    def get_funcptr_for_newarray(self):
        return llhelper(self.GC_MALLOC_ARRAY, self.malloc_array)

    def get_funcptr_for_newstr(self):
        return llhelper(self.GC_MALLOC_STR_UNICODE, self.malloc_str)

    def get_funcptr_for_newunicode(self):
        return llhelper(self.GC_MALLOC_STR_UNICODE, self.malloc_unicode)

    def do_write_barrier(self, gcref_struct, gcref_newptr):
        hdr_addr = llmemory.cast_ptr_to_adr(gcref_struct)
        hdr_addr -= self.gcheaderbuilder.size_gc_header
        hdr = llmemory.cast_adr_to_ptr(hdr_addr, self.HDRPTR)
        if hdr.tid & self.GCClass.JIT_WB_IF_FLAG:
            # get a pointer to the 'remember_young_pointer' function from
            # the GC, and call it immediately
            llop1 = self.llop1
            funcptr = llop1.get_write_barrier_failing_case(self.WB_FUNCPTR)
            funcptr(llmemory.cast_ptr_to_adr(gcref_struct),
                    llmemory.cast_ptr_to_adr(gcref_newptr))

    def rewrite_assembler(self, cpu, operations):
        # Add COND_CALLs to the write barrier before SETFIELD_GC and
        # SETARRAYITEM_GC operations.
        newops = []
        for op in operations:
            if op.opnum == rop.DEBUG_MERGE_POINT:
                continue
            # ---------- write barrier for SETFIELD_GC ----------
            if op.opnum == rop.SETFIELD_GC:
                v = op.args[1]
                if isinstance(v, BoxPtr) or (isinstance(v, ConstPtr) and
                                             bool(v.value)): # store a non-NULL
                    self._gen_write_barrier(newops, op.args[0], v)
                    op = ResOperation(rop.SETFIELD_RAW, op.args, None,
                                      descr=op.descr)
            # ---------- write barrier for SETARRAYITEM_GC ----------
            if op.opnum == rop.SETARRAYITEM_GC:
                v = op.args[2]
                if isinstance(v, BoxPtr) or (isinstance(v, ConstPtr) and
                                             bool(v.value)): # store a non-NULL
                    self._gen_write_barrier(newops, op.args[0], v)
                    op = ResOperation(rop.SETARRAYITEM_RAW, op.args, None,
                                      descr=op.descr)
            # ----------
            newops.append(op)
        del operations[:]
        operations.extend(newops)

    def _gen_write_barrier(self, newops, v_base, v_value):
        args = [v_base, v_value]
        newops.append(ResOperation(rop.COND_CALL_GC_WB, args, None,
                                   descr=self.write_barrier_descr))

    def can_inline_malloc(self, descr):
        assert isinstance(descr, BaseSizeDescr)
        if descr.size < self.max_size_of_young_obj:
            has_finalizer = bool(descr.tid & (1<<16))
            if has_finalizer:
                return False
            return True
        return False

    def has_write_barrier_class(self):
        return WriteBarrierDescr
