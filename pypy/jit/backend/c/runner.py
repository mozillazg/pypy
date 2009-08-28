from pypy.rpython.lltypesystem import lltype, llmemory, rffi, rstr
from pypy.jit.backend.model import AbstractCPU
from pypy.jit.backend.c.compile import Compiler, get_c_type, get_class_for_type
from pypy.jit.backend.c.compile import CallDescr, ArrayDescr, get_c_array_descr
from pypy.jit.metainterp import history
from pypy.jit.metainterp.history import BoxInt, BoxPtr
from pypy.jit.backend.x86 import symbolic

WORD = rffi.sizeof(lltype.Signed)


class CCPU(AbstractCPU):
    is_oo = False

    def __init__(self, rtyper, stats, translate_support_code=False):
        self.rtyper = rtyper
        self.call_descrs = {}
        self.compiler = Compiler(translate_support_code)
        self.translate_support_code = translate_support_code

    def compile_operations(self, loop, guard_op=None):
        self.compiler.compile_operations(loop, guard_op)

    def set_future_value_int(self, index, intvalue):
        self.compiler.c_jit_al[index] = intvalue

    def set_future_value_ptr(self, index, ptrvalue):
        self.compiler.c_jit_ap[index] = ptrvalue

    def execute_operations(self, loop):
        return self.compiler.run(loop)

    def get_latest_value_int(self, index):
        return self.compiler.c_jit_al[index]

    def get_latest_value_ptr(self, index):
        return self.compiler.c_jit_ap[index]

    @staticmethod
    def arraydescrof(A):
        return get_c_array_descr(A.OF)

    def calldescrof(self, FUNC, ARGS, RESULT):
        args_cls = [get_class_for_type(ARG) for ARG in ARGS]
        cls_result = get_class_for_type(RESULT)
        ct_result = get_c_type(RESULT)
        key = (tuple(args_cls), cls_result, ct_result)
        try:
            return self.call_descrs[key]
        except KeyError:
            pass
        descr = CallDescr(args_cls, cls_result, ct_result)
        self.call_descrs[key] = descr
        return descr

    def do_arraylen_gc(self, args, arraydescr):
        ofs = 0    #self.gc_ll_descr.array_length_ofs
        gcref = args[0].getptr(llmemory.GCREF)
        length = rffi.cast(rffi.CArrayPtr(lltype.Signed), gcref)[ofs/WORD]
        return BoxInt(length)

    def do_getarrayitem_gc(self, args, arraydescr):
        assert isinstance(arraydescr, ArrayDescr)
        field = args[1].getint()
        gcref = args[0].getptr(llmemory.GCREF)
        size = arraydescr.item_size
        ofs = WORD     #XXX!
        if size == 1:
            return BoxInt(ord(rffi.cast(rffi.CArrayPtr(lltype.Char), gcref)
                              [ofs + field]))
        elif size == WORD:
            val = (rffi.cast(rffi.CArrayPtr(lltype.Signed), gcref)
                   [ofs/WORD + field])
            return arraydescr.item_cls._c_jit_make(val)
        else:
            raise NotImplementedError("size = %d" % size)

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

    def do_call(self, args, calldescr):
        assert isinstance(calldescr, CallDescr)
        loop = calldescr.get_loop_for_call(self.compiler)
        history.set_future_values(self, args)
        self.compiler.run(loop)
        # Note: if an exception is set, the rest of the code does a bit of
        # nonsense but nothing wrong (the return value should be ignored)
        if calldescr.ret_class is None:
            return None
        elif calldescr.ret_class is BoxPtr:
            return BoxPtr(self.get_latest_value_ptr(0))
        else:
            return BoxInt(self.get_latest_value_int(0))

    def do_newstr(self, args, descr=None):
        xxx#...

    @staticmethod
    def cast_adr_to_int(addr):
        return rffi.cast(lltype.Signed, addr)


CPU = CCPU

import pypy.jit.metainterp.executor
pypy.jit.metainterp.executor.make_execute_list(CPU)
