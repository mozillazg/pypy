
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

    def num_nonempty_regs(self):
        return len(filter(bool, self.registers_i))

class MockMetaInterp(object):
    def __init__(self):
        self.framestack = []

    def newframe(self, jitcode):
        self.framestack.append(Frame(jitcode))

    def popframe(self):
        self.framestack.pop()

class MockCPU(object):
    def get_int_value(self, frame, index):
        assert frame == "myframe"
        return index + 3

class TestResumeDirect(object):
    def test_box_resume_reader(self):
        jitcode = JitCode("jitcode")
        jitcode.setup(num_regs_i=13)
        resume_loop = parse("""
        []
        enter_frame(-1, descr=jitcode1)
        backend_put(10, 0, 1)
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

    def test_nested_call(self):
        jitcode1 = JitCode("jitcode")
        jitcode1.setup(num_regs_i=13)
        jitcode2 = JitCode("jitcode2")
        jitcode2.setup(num_regs_i=9)
        resume_loop = parse("""
        []
        enter_frame(-1, descr=jitcode1)
        backend_put(11, 0, 2)
        enter_frame(12, descr=jitcode2)
        backend_put(12, 0, 3)
        backend_put(8, 1, 4)
        leave_frame()
        backend_put(10, 0, 1)
        leave_frame()
        """, namespace={'jitcode1': jitcode1, 'jitcode2': jitcode2})
        metainterp = MockMetaInterp()
        metainterp.cpu = MockCPU()
        descr = Descr()
        descr.rd_loop = MockLoop()
        descr.rd_loop.rd_bytecode = resume_loop.operations
        descr.rd_bytecode_position = 5
        rebuild_from_resumedata(metainterp, "myframe", descr)
        assert len(metainterp.framestack) == 2
        f = metainterp.framestack[-1]
        f2 = metainterp.framestack[0]
        assert f.num_nonempty_regs() == 1
        assert f2.num_nonempty_regs() == 2
        assert f.registers_i[3].getint() == 12 + 3
        assert f2.registers_i[4].getint() == 8 + 3
        assert f2.registers_i[2].getint() == 11 + 3
        
        descr.rd_bytecode_position = 7
        metainterp.framestack = []
        rebuild_from_resumedata(metainterp, "myframe", descr)
        assert len(metainterp.framestack) == 1
        f = metainterp.framestack[-1]
        assert f.num_nonempty_regs() == 3
        assert f.registers_i[1].getint() == 10 + 3
        assert f.registers_i[2].getint() == 11 + 3
        assert f.registers_i[4].getint() == 8 + 3

