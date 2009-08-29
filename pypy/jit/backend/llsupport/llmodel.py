import sys
from pypy.rpython.lltypesystem import lltype, llmemory, rffi, rstr
from pypy.rlib.objectmodel import we_are_translated, specialize
from pypy.rlib.unroll import unrolling_iterable
from pypy.jit.metainterp.history import BoxInt, BoxPtr
from pypy.jit.backend.model import AbstractCPU
from pypy.jit.backend.llsupport import symbolic
from pypy.jit.backend.llsupport.descr import get_field_descr, get_array_descr
from pypy.jit.backend.llsupport.descr import AbstractFieldDescr
from pypy.jit.backend.llsupport.descr import AbstractArrayDescr

WORD         = rffi.sizeof(lltype.Signed)
SIZEOF_CHAR  = rffi.sizeof(lltype.Char)
SIZEOF_SHORT = rffi.sizeof(rffi.SHORT)
SIZEOF_INT   = rffi.sizeof(rffi.INT)

unroll_basic_sizes = unrolling_iterable([(lltype.Signed, WORD),
                                         (lltype.Char,   SIZEOF_CHAR),
                                         (rffi.SHORT,    SIZEOF_SHORT),
                                         (rffi.INT,      SIZEOF_INT)])

def _check_addr_range(x):
    if sys.platform == 'linux2':
        # this makes assumption about address ranges that are valid
        # only on linux (?)
        assert x == 0 or x > (1<<20) or x < (-1<<20)        


class AbstractLLCPU(AbstractCPU):

    def __init__(self, rtyper, stats, translate_support_code=False,
                 gcdescr=None):
        from pypy.jit.backend.llsupport.gc import get_ll_description
        self.rtyper = rtyper
        self.stats = stats
        self.translate_support_code = translate_support_code
        self.gc_ll_descr = get_ll_description(gcdescr, self)

    # ------------------- helpers and descriptions --------------------

    @staticmethod
    def cast_adr_to_int(x):
        res = rffi.cast(lltype.Signed, x)
        return res

    def cast_int_to_gcref(self, x):
        if not we_are_translated():
            _check_addr_range(x)
        return rffi.cast(llmemory.GCREF, x)

    def fielddescrof(self, STRUCT, fieldname):
        return get_field_descr(STRUCT, fieldname, self.translate_support_code)

    def unpack_fielddescr(self, fielddescr):
        assert isinstance(fielddescr, AbstractFieldDescr)
        ofs = fielddescr.offset
        size = fielddescr.get_field_size(self.translate_support_code)
        ptr = fielddescr.is_pointer_field()
        return ofs, size, ptr
    unpack_fielddescr._always_inline_ = True

    def arraydescrof(self, A):
        return get_array_descr(A)

    def unpack_arraydescr(self, arraydescr):
        assert isinstance(arraydescr, AbstractArrayDescr)
        ofs = arraydescr.get_base_size(self.translate_support_code)
        size = arraydescr.get_item_size(self.translate_support_code)
        ptr = arraydescr.is_array_of_pointers()
        return ofs, size, ptr
    unpack_arraydescr._always_inline_ = True

    def do_arraylen_gc(self, args, arraydescr):
        assert isinstance(arraydescr, AbstractArrayDescr)
        ofs = arraydescr.get_ofs_length(self.translate_support_code)
        gcref = args[0].getptr_base()
        length = rffi.cast(rffi.CArrayPtr(lltype.Signed), gcref)[ofs/WORD]
        return BoxInt(length)

    def do_getarrayitem_gc(self, args, arraydescr):
        itemindex = args[1].getint()
        gcref = args[0].getptr_base()
        ofs, size, ptr = self.unpack_arraydescr(arraydescr)
        #
        for TYPE, itemsize in unroll_basic_sizes:
            if size == itemsize:
                val = (rffi.cast(rffi.CArrayPtr(TYPE), gcref)
                       [ofs/itemsize + itemindex])
                val = rffi.cast(lltype.Signed, val)
                break
        else:
            raise NotImplementedError("size = %d" % size)
        if ptr:
            return BoxPtr(self.cast_int_to_gcref(val))
        else:
            return BoxInt(val)

    def _new_do_len(TP):
        def do_strlen(self, args, descr=None):
            basesize, itemsize, ofs_length = symbolic.get_array_token(TP,
                                                self.translate_support_code)
            gcref = args[0].getptr(llmemory.GCREF)
            v = rffi.cast(rffi.CArrayPtr(lltype.Signed), gcref)[ofs_length/WORD]
            return BoxInt(v)
        return do_strlen

    do_strlen = _new_do_len(rstr.STR)
    do_unicodelen = _new_do_len(rstr.UNICODE)

    def do_strgetitem(self, args, descr=None):
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR,
                                                    self.translate_support_code)
        gcref = args[0].getptr(llmemory.GCREF)
        i = args[1].getint()
        v = rffi.cast(rffi.CArrayPtr(lltype.Char), gcref)[basesize + i]
        return BoxInt(ord(v))

    @specialize.argtype(1)
    def _base_do_getfield(self, gcref, fielddescr):
        ofs, size, ptr = self.unpack_fielddescr(fielddescr)
        for TYPE, itemsize in unroll_basic_sizes:
            if size == itemsize:
                val = rffi.cast(rffi.CArrayPtr(TYPE), gcref)[ofs/itemsize]
                val = rffi.cast(lltype.Signed, val)
                break
        else:
            raise NotImplementedError("size = %d" % size)
        if ptr:
            return BoxPtr(self.cast_int_to_gcref(val))
        else:
            return BoxInt(val)

    def do_getfield_gc(self, args, fielddescr):
        gcref = args[0].getptr(llmemory.GCREF)
        return self._base_do_getfield(gcref, fielddescr)

    def do_getfield_raw(self, args, fielddescr):
        return self._base_do_getfield(args[0].getint(), fielddescr)


import pypy.jit.metainterp.executor
pypy.jit.metainterp.executor.make_execute_list(AbstractLLCPU)
