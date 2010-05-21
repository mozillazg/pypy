from pypy.rlib.jit import JitDriver
from pypy.jit.metainterp.test.test_basic import LLJitMixin, OOJitMixin
from pypy.jit.metainterp.blackhole import BlackholeInterpBuilder
from pypy.jit.codewriter.assembler import JitCode
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.llinterp import LLException


class FakeCodeWriter:
    pass
class FakeAssembler:
    pass
class FakeCPU:
    def bh_call_i(self, func, calldescr, args_i, args_r, args_f):
        assert func == 321
        assert calldescr == "<calldescr>"
        if args_i[0] < 0:
            raise LLException("etype", "evalue")
        return args_i[0] * 2

def getblackholeinterp(insns, descrs=[]):
    cw = FakeCodeWriter()
    cw.cpu = FakeCPU()
    cw.assembler = FakeAssembler()
    cw.assembler.insns = insns
    cw.assembler.descrs = descrs
    builder = BlackholeInterpBuilder(cw)
    return builder.acquire_interp()

def test_simple():
    jitcode = JitCode("test")
    jitcode.setup("\x00\x00\x01\x02"
                  "\x01\x02",
                  [])
    blackholeinterp = getblackholeinterp({'int_add/ii>i': 0,
                                          'int_return/i': 1})
    blackholeinterp.setposition(jitcode, 0)
    blackholeinterp.setarg_i(0, 40)
    blackholeinterp.setarg_i(1, 2)
    blackholeinterp.run()
    assert blackholeinterp.final_result_i() == 42

def test_simple_const():
    jitcode = JitCode("test")
    jitcode.setup("\x00\x30\x01\x02"
                  "\x01\x02",
                  [])
    blackholeinterp = getblackholeinterp({'int_sub/ci>i': 0,
                                          'int_return/i': 1})
    blackholeinterp.setposition(jitcode, 0)
    blackholeinterp.setarg_i(1, 6)
    blackholeinterp.run()
    assert blackholeinterp.final_result_i() == 42

def test_simple_bigconst():
    jitcode = JitCode("test")
    jitcode.setup("\x00\xFD\x01\x02"
                  "\x01\x02",
                  [666, 666, 10042, 666])
    blackholeinterp = getblackholeinterp({'int_sub/ii>i': 0,
                                          'int_return/i': 1})
    blackholeinterp.setposition(jitcode, 0)
    blackholeinterp.setarg_i(1, 10000)
    blackholeinterp.run()
    assert blackholeinterp.final_result_i() == 42

def test_simple_loop():
    jitcode = JitCode("test")
    jitcode.setup("\x00\x16\x02\x10\x00"  # L1: goto_if_not_int_gt %i0, 2, L2
                  "\x01\x17\x16\x17"      #     int_add %i1, %i0, %i1
                  "\x02\x16\x01\x16"      #     int_sub %i0, $1, %i0
                  "\x03\x00\x00"          #     goto L1
                  "\x04\x17",             # L2: int_return %i1
                  [])
    blackholeinterp = getblackholeinterp({'goto_if_not_int_gt/icL': 0,
                                          'int_add/ii>i': 1,
                                          'int_sub/ic>i': 2,
                                          'goto/L': 3,
                                          'int_return/i': 4})
    blackholeinterp.setposition(jitcode, 0)
    blackholeinterp.setarg_i(0x16, 6)    # %i0
    blackholeinterp.setarg_i(0x17, 100)  # %i1
    blackholeinterp.run()
    assert blackholeinterp.final_result_i() == 100+6+5+4+3

def test_simple_exception():
    jitcode = JitCode("test")
    jitcode.setup(    # residual_call_ir_i $<* fn g>, <Descr>, I[%i9], R[], %i8
                  "\x01\xFF\x00\x00\x01\x09\x00\x08"
                  "\x00\x0D\x00"          #     catch_exception L1
                  "\x02\x08"              #     int_return %i8
                  "\x03\x2A",             # L1: int_return $42
                  [321])   # <-- address of the function g
    blackholeinterp = getblackholeinterp({'catch_exception/L': 0,
                                          'residual_call_ir_i/idIR>i': 1,
                                          'int_return/i': 2,
                                          'int_return/c': 3},
                                         ["<calldescr>"])
    #
    blackholeinterp.setposition(jitcode, 0)
    blackholeinterp.setarg_i(0x9, 100)
    blackholeinterp.run()
    assert blackholeinterp.final_result_i() == 200
    #
    blackholeinterp.setposition(jitcode, 0)
    blackholeinterp.setarg_i(0x9, -100)
    blackholeinterp.run()
    assert blackholeinterp.final_result_i() == 42
