from rpython.jit.backend.zarch import conditions as con
from rpython.jit.backend.zarch import registers as reg
from rpython.jit.backend.zarch.assembler import AssemblerZARCH
from rpython.jit.backend.zarch import locations as loc
from rpython.jit.backend.zarch.test.support import run_asm
from rpython.jit.backend.detect_cpu import getcpuclass
from rpython.jit.metainterp.resoperation import rop
from rpython.jit.codewriter import longlong

from rpython.rtyper.annlowlevel import llhelper
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.jit.metainterp.history import JitCellToken
from rpython.jit.backend.model import CompiledLoopToken
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.rtyper.annlowlevel import llhelper
from rpython.rlib.objectmodel import specialize
from rpython.rlib.debug import ll_assert

CPU = getcpuclass()

class TestRunningAssembler(object):
    def setup_method(self, method):
        cpu = CPU(None, None)
        self.a = AssemblerZARCH(cpu)
        self.a.setup_once()
        token = JitCellToken()
        clt = CompiledLoopToken(cpu, 0)
        clt.allgcrefs = []
        token.compiled_loop_token = clt
        self.a.setup(token)

    def test_make_operation_list(self):
        i = rop.INT_ADD
        from rpython.jit.backend.zarch import assembler
        assert assembler.asm_operations[i] \
            is AssemblerZARCH.emit_op_int_add.im_func

    def test_load_small_int_to_reg(self):
        self.a.mc.LGHI(reg.r2, loc.imm(123))
        self.a.jmpto(reg.r14)
        assert run_asm(self.a) == 123

    def test_prolog_epilog(self):
        self.a.gen_func_prolog()
        self.a.mc.LGHI(reg.r2, loc.imm(123))
        self.a.gen_func_epilog()
        assert run_asm(self.a) == 123

    def test_simple_func(self):
        # enter
        self.a.mc.STMG(reg.r11, reg.r15, loc.addr(reg.sp, -96))
        self.a.mc.AHI(reg.sp, loc.imm(-96))
        self.a.mc.BRASL(reg.r14, loc.imm(8+6))
        self.a.mc.LMG(reg.r11, reg.r15, loc.addr(reg.sp, 0))
        self.a.jmpto(reg.r14)

        addr = self.a.mc.get_relative_pos()
        assert addr & 0x1 == 0
        self.a.gen_func_prolog()
        self.a.mc.LGHI(reg.r2, loc.imm(321))
        self.a.gen_func_epilog()
        assert run_asm(self.a) == 321

