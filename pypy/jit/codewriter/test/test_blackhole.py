from pypy.jit.codewriter.assembler import JitCode
from pypy.jit.codewriter.blackhole import BlackholeInterpreter


def test_simple():
    jitcode = JitCode("test")
    jitcode.setup("\x00\x00\x01\x02"
                  "\x01\x02",
                  [])
    blackholeinterp = BlackholeInterpreter()
    blackholeinterp.setup_insns({'int_add/iii': 0,
                                 'int_return/i': 1})
    blackholeinterp.setarg_i(0, 40)
    blackholeinterp.setarg_i(1, 2)
    blackholeinterp.run(jitcode, 0)
    assert blackholeinterp.result_i == 42

def test_simple_const():
    jitcode = JitCode("test")
    jitcode.setup("\x00\x30\x01\x02"
                  "\x01\x02",
                  [])
    blackholeinterp = BlackholeInterpreter()
    blackholeinterp.setup_insns({'int_sub/cii': 0,
                                 'int_return/i': 1})
    blackholeinterp.setarg_i(1, 6)
    blackholeinterp.run(jitcode, 0)
    assert blackholeinterp.result_i == 42

def test_simple_loop():
    jitcode = JitCode("test")
    jitcode.setup("\x00\x10\x00\x16\x02"  # L1: goto_if_not_int_gt L2, %i0, 2
                  "\x01\x17\x16\x17"      #     int_add %i1, %i0, %i1
                  "\x02\x16\x01\x16"      #     int_sub %i0, $1, %i0
                  "\x03\x00\x00"          #     goto L1
                  "\x04\x17",             # L2: int_return %i1
                  [])
    blackholeinterp = BlackholeInterpreter()
    blackholeinterp.setup_insns({'goto_if_not_int_gt/Lic': 0,
                                 'int_add/iii': 1,
                                 'int_sub/ici': 2,
                                 'goto/L': 3,
                                 'int_return/i': 4})
    blackholeinterp.setarg_i(0x16, 6)
    blackholeinterp.setarg_i(0x17, 100)
    blackholeinterp.run(jitcode, 0)
    assert blackholeinterp.result_i == 100+6+5+4+3
