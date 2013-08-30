
from rpython.jit.metainterp.history import JitCellToken
from rpython.jit.codewriter.jitcode import JitCode
from rpython.jit.tool.oparser import parse
from rpython.jit.metainterp.optimizeopt.util import equaloplists

class MockJitCode(JitCode):
    def __init__(self, no):
        self.no = no

    def num_regs(self):
        return self.no

    def __repr__(self):
        return 'MockJitCode(%d)' % self.no

class ResumeTest(object):
    def setup_method(self, meth):
        self.cpu = self.CPUClass(None, None)
        self.cpu.setup_once()

    def test_simple(self):
        jitcode = MockJitCode(3)
        loop = parse("""
        [i0]
        enter_frame(-1, descr=jitcode)
        resume_put(i0, 0, 2)
        guard_true(i0)
        leave_frame()
        """, namespace={'jitcode': jitcode})
        looptoken = JitCellToken()
        self.cpu.compile_loop(None, loop.inputargs, loop.operations,
                              looptoken)
        descr = loop.operations[2].getdescr()
        assert descr.rd_bytecode_position == 2
        expected_resume = parse("""
        []
        enter_frame(-1, descr=jitcode)
        backend_put(28, 0, 2)
        leave_frame()
        """, namespace={'jitcode': jitcode}).operations
        equaloplists(descr.rd_resume_bytecode.opcodes, expected_resume)
