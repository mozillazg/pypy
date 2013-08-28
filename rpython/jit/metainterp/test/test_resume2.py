
from rpython.jit.tool.oparser import parse
from rpython.jit.codewriter.jitcode import JitCode
from rpython.jit.metainterp.history import AbstractDescr
from rpython.jit.metainterp.resume2 import rebuild_from_resumedata

class Descr(AbstractDescr):
    pass

class MockLoop(object):
    pass

class Frame(object):
    def __init__(self, jitcode):
        self.jitcode = jitcode
        self.registers_i = [None] * jitcode.num_regs_i()

class MockMetaInterp(object):
    def __init__(self):
        self.framestack = []

    def newframe(self, jitcode):
        self.framestack.append(Frame(jitcode))

class MockCPU(object):
    def get_int_value(self, frame, index):
        assert frame == "myframe"
        assert index == 10
        return 13

class TestResumeDirect(object):
    def test_direct_resume_reader(self):
        jitcode = JitCode("jitcode")
        jitcode.setup(num_regs_i=13)
        resume_loop = parse("""
        []
        enter_frame(-1, descr=jitcode1)
        resume_put(10, 0, 1)
        leave_frame()
        """, namespace={'jitcode1': jitcode})
        descr = Descr()
        descr.rd_loop = MockLoop()
        descr.rd_loop.rd_bytecode = resume_loop.operations
        descr.rd_bytecode_position = 2
        metainterp = MockMetaInterp()
        metainterp.cpu = MockCPU()
        rebuild_from_resumedata(metainterp, "myframe", descr)
        assert len(metainterp.framestack) == 1
        f = metainterp.framestack[-1]
        assert f.registers_i[1].getint() == 13
