from pypy.rpython.lltypesystem import lltype, rffi
from pypy.jit.backend.model import AbstractCPU
from pypy.jit.backend.c.compile import Compiler
from pypy.jit.metainterp.history import AbstractDescr, getkind


class CCPU(AbstractCPU):
    is_oo = False

    def __init__(self, rtyper, stats):
        self.rtyper = rtyper
        self.call_descr = {'int': CallDescr('long'),
                           'ptr': CallDescr('char*')}
        self.compiler = Compiler()

    def compile_operations(self, loop, guard_op=None):
        self.compiler.compile_operations(loop, guard_op)

    def calldescrof(self, FUNC, ARGS, RESULT):
        return self.call_descr[getkind(RESULT)]

    @staticmethod
    def cast_adr_to_int(addr):
        return rffi.cast(lltype.Signed, addr)

    def set_future_value_int(self, index, intvalue):
        self.compiler.c_jit_al[index] = intvalue

    def execute_operations(self, loop):
        return self.compiler.run(loop)

    def get_latest_value_int(self, index):
        return self.compiler.c_jit_al[index]


CPU = CCPU

# ____________________________________________________________

class CallDescr(AbstractDescr):
    def __init__(self, ret_c_type):
        self.ret_c_type = ret_c_type
