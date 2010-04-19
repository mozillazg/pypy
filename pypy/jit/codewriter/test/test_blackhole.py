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
