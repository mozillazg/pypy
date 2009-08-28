from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.jit.backend.model import AbstractCPU
from pypy.jit.backend.c.compile import Compiler, get_c_type, get_class_for_type
from pypy.jit.backend.c.compile import CallDescr
from pypy.jit.metainterp import history
from pypy.jit.metainterp.history import BoxInt, BoxPtr


class CCPU(AbstractCPU):
    is_oo = False

    def __init__(self, rtyper, stats, translate_support_code=False):
        self.rtyper = rtyper
        self.call_descrs = {}
        self.compiler = Compiler(translate_support_code)

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
