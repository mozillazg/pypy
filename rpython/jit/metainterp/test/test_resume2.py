
import py
from rpython.jit.tool.oparser import parse
from rpython.jit.codewriter.jitcode import JitCode
from rpython.jit.metainterp.history import AbstractDescr
from rpython.jit.metainterp.resume2 import rebuild_from_resumedata,\
     ResumeBytecode, BoxResumeReader


class Descr(AbstractDescr):
    pass

class MockLoop(object):
    pass

class Frame(object):
    def __init__(self, jitcode):
        self.jitcode = jitcode
        self.registers_i = [None] * jitcode.num_regs_i()
        self.registers_r = [None] * jitcode.num_regs_r()
        self.registers_f = [None] * jitcode.num_regs_f()

    def num_nonempty_regs(self):
        return len(filter(bool, self.registers_i))

    def dump_registers(self, lst, backend_values):
        lst += [backend_values[x] for x in self.registers_i]
        lst += [backend_values[x] for x in self.registers_r]
        lst += [backend_values[x] for x in self.registers_f]

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

class RebuildingResumeReader(BoxResumeReader):
    def __init__(self):
        self.backend_values = {}
        self.metainterp = MockMetaInterp()

    def finish(self):
        l = []
        for frame in self.metainterp.framestack:
            frame.dump_registers(l, self.backend_values)
        return l

def rebuild_locs_from_resumedata(faildescr):
    return RebuildingResumeReader().rebuild(faildescr)

class TestResumeDirect(object):
    def test_box_resume_reader(self):
        jitcode = JitCode("jitcode")
        jitcode.setup(num_regs_i=13)
        resume_loop = parse("""
        [i0]
        enter_frame(-1, descr=jitcode1)
        resume_put(i0, 0, 1)
        backend_attach(i0, 10)
        leave_frame()
        """, namespace={'jitcode1': jitcode})
        descr = Descr()
        descr.rd_resume_bytecode = ResumeBytecode(resume_loop.operations)
        descr.rd_bytecode_position = 3
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
        [i0, i1, i2, i3]
        enter_frame(-1, descr=jitcode1)
        resume_put(i0, 0, 2)
        backend_attach(i0, 11)
        enter_frame(12, descr=jitcode2)
        resume_put(i1, 0, 3)
        resume_put(i2, 1, 4)
        backend_attach(i1, 12)
        backend_attach(i2, 8)
        leave_frame()
        backend_attach(i3, 10)
        resume_put(i3, 0, 1)
        leave_frame()
        """, namespace={'jitcode1': jitcode1, 'jitcode2': jitcode2})
        metainterp = MockMetaInterp()
        metainterp.cpu = MockCPU()
        descr = Descr()
        descr.rd_resume_bytecode = ResumeBytecode(resume_loop.operations)
        descr.rd_bytecode_position = 8
        rebuild_from_resumedata(metainterp, "myframe", descr)
        assert len(metainterp.framestack) == 2
        f = metainterp.framestack[-1]
        f2 = metainterp.framestack[0]
        assert f.num_nonempty_regs() == 1
        assert f2.num_nonempty_regs() == 2
        assert f.registers_i[3].getint() == 12 + 3
        assert f2.registers_i[4].getint() == 8 + 3
        assert f2.registers_i[2].getint() == 11 + 3

        descr.rd_bytecode_position = 11
        metainterp.framestack = []
        rebuild_from_resumedata(metainterp, "myframe", descr)
        assert len(metainterp.framestack) == 1
        f = metainterp.framestack[-1]
        assert f.num_nonempty_regs() == 3
        assert f.registers_i[1].getint() == 10 + 3
        assert f.registers_i[2].getint() == 11 + 3
        assert f.registers_i[4].getint() == 8 + 3

    def test_bridge(self):
        jitcode1 = JitCode("jitcode")
        jitcode1.setup(num_regs_i=13)
        base = parse("""
        [i0, i1]
        enter_frame(-1, descr=jitcode1)
        resume_put(i0, 0, 0)
        backend_attach(i0, 42)
        # here is the split caused by a guard
        resume_put(i1, 0, 1)
        backend_attach(i1, 1)
        """, namespace={'jitcode1': jitcode1})
        bridge = parse("""
        [i2]
        resume_put(i2, 0, 1)
        backend_attach(i2, 2)
        """)
        descr = Descr()
        descr.rd_bytecode_position = 2
        parent = ResumeBytecode(base.operations)
        b = ResumeBytecode(bridge.operations, parent=parent,
                           parent_position=3)
        descr.rd_resume_bytecode = b
        metainterp = MockMetaInterp()
        metainterp.cpu = MockCPU()
        rebuild_from_resumedata(metainterp, "myframe", descr)
        f = metainterp.framestack[-1]
        assert f.num_nonempty_regs() == 2
        assert f.registers_i[0].getint() == 42 + 3
        assert f.registers_i[1].getint() == 2 + 3

    def test_new(self):
        py.test.skip("finish")
        jitcode1 = JitCode("jitcode")
        jitcode1.setup(num_regs_i=1)
        base = parse("""
        []
        enter_frame(-1, descr=jitcode)
        i0 = new(descr=structdescr)
        resume_setfield(i0, 13, descr=fielddescr)
        backend_put(12,
        leave_frame()
        """, namespace={'jitcode':jitcode1})

    def test_reconstructing_resume_reader(self):
        jitcode1 = JitCode("jitcode")
        jitcode1.setup(num_regs_i=2, num_regs_f=0, num_regs_r=0)
        jitcode2 = JitCode("jitcode2")
        jitcode2.setup(num_regs_i=1, num_regs_f=0, num_regs_r=0)
        resume_loop = parse("""
        [i0, i1, i2, i3]
        enter_frame(-1, descr=jitcode1)
        resume_put(i0, 0, 1)
        backend_attach(i0, 11)
        enter_frame(12, descr=jitcode2)
        resume_put(i1, 0, 0)
        backend_attach(i1, 12)
        resume_put(i3, 1, 0)
        backend_attach(i3, 8)
        leave_frame()
        leave_frame()
        """, namespace={'jitcode1': jitcode1,
                        'jitcode2': jitcode2})
        descr = Descr()
        descr.rd_resume_bytecode = ResumeBytecode(resume_loop.operations)
        descr.rd_bytecode_position = 8
        locs = rebuild_locs_from_resumedata(descr)
        assert locs == [8, 11, 12]
