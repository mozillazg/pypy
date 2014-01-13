
import py
from rpython.jit.tool.oparser import parse
from rpython.jit.codewriter.jitcode import JitCode
from rpython.jit.metainterp.history import AbstractDescr
from rpython.jit.metainterp.resume2 import rebuild_from_resumedata,\
     ResumeBytecode, AbstractResumeReader


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
        return len([i for i in self.registers_i if i is not None])

    def dump_registers(self, lst, backend_values):
        lst += [backend_values[x] for x in self.registers_i]
        lst += [backend_values[x] for x in self.registers_r]
        lst += [backend_values[x] for x in self.registers_f]

class MockMetaInterp(object):
    def __init__(self):
        self.cpu = MockCPU()
        self.framestack = []

    def newframe(self, jitcode, record_resume=False):
        f = Frame(jitcode)
        self.framestack.append(f)
        return f

    def popframe(self):
        self.framestack.pop()

class MockCPU(object):
    def get_int_value(self, frame, index):
        assert frame == "myframe"
        return index + 3

class RebuildingResumeReader(AbstractResumeReader):
    def finish(self):
        return [f.registers for f in self.framestack]

def rebuild_locs_from_resumedata(faildescr):
    return RebuildingResumeReader().rebuild(faildescr)

class TestResumeDirect(object):
    def test_box_resume_reader(self):
        jitcode = JitCode("jitcode")
        jitcode.setup(num_regs_i=13, num_regs_r=0, num_regs_f=0)
        resume_loop = parse("""
        []
        enter_frame(-1, descr=jitcode1)
        resume_put(10, 0, 1)
        leave_frame()
        """, namespace={'jitcode1': jitcode})
        descr = Descr()
        descr.rd_resume_bytecode = ResumeBytecode(resume_loop.operations)
        descr.rd_bytecode_position = 2
        metainterp = MockMetaInterp()
        metainterp.cpu = MockCPU()
        rebuild_from_resumedata(metainterp, "myframe", descr)
        assert len(metainterp.framestack) == 1
        f = metainterp.framestack[-1]
        assert f.registers_i[1].getint() == 13

    def test_nested_call(self):
        jitcode1 = JitCode("jitcode")
        jitcode1.setup(num_regs_i=13, num_regs_r=0, num_regs_f=0)
        jitcode2 = JitCode("jitcode2")
        jitcode2.setup(num_regs_i=9, num_regs_r=0, num_regs_f=0)
        resume_loop = parse("""
        []
        enter_frame(-1, descr=jitcode1)
        resume_put(11, 0, 2)
        enter_frame(12, descr=jitcode2)
        resume_put(12, 1, 3)
        resume_put(8, 0, 4)
        leave_frame()
        resume_put(10, 0, 1)
        leave_frame()
        """, namespace={'jitcode1': jitcode1, 'jitcode2': jitcode2})
        metainterp = MockMetaInterp()
        metainterp.cpu = MockCPU()
        descr = Descr()
        descr.rd_resume_bytecode = ResumeBytecode(resume_loop.operations)
        descr.rd_bytecode_position = 5
        state = rebuild_from_resumedata(metainterp, "myframe", descr)
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

    def test_bridge(self):
        jitcode1 = JitCode("jitcode")
        jitcode1.setup(num_regs_i=13, num_regs_r=0, num_regs_f=0)
        base = parse("""
        []
        enter_frame(-1, descr=jitcode1)
        resume_put(42, 0, 0)
        # here is the split caused by a guard
        resume_put(1, 0, 1)
        leave_frame()
        """, namespace={'jitcode1': jitcode1})
        bridge = parse("""
        []
        resume_put(2, 0, 1)
        """)
        descr = Descr()
        descr.rd_bytecode_position = 1
        parent = ResumeBytecode(base.operations)
        b = ResumeBytecode(bridge.operations, parent=parent,
                           parent_position=2)
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
        jitcode1.setup(num_regs_i=1, num_regs_r=0, num_regs_f=0)
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
        []
        enter_frame(-1, descr=jitcode1)
        resume_put(11, 0, 1)
        enter_frame(12, descr=jitcode2)
        resume_put(12, 1, 0)
        resume_put(8, 0, 0)
        leave_frame()
        leave_frame()
        """, namespace={'jitcode1': jitcode1,
                        'jitcode2': jitcode2})
        descr = Descr()
        descr.rd_resume_bytecode = ResumeBytecode(resume_loop.operations)
        descr.rd_bytecode_position = 5
        locs = rebuild_locs_from_resumedata(descr)
        assert locs == [[8, 11], [12]]

    def test_resume_put_const(self):
        xxx
