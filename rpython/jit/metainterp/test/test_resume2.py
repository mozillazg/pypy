
import py
from rpython.jit.tool.oparser import parse
from rpython.jit.codewriter.jitcode import JitCode
from rpython.jit.metainterp.history import AbstractDescr, Const, INT, Stats
from rpython.jit.metainterp.resume2 import rebuild_from_resumedata,\
     ResumeBytecode, AbstractResumeReader
from rpython.jit.codewriter.format import unformat_assembler
from rpython.jit.codewriter.codewriter import CodeWriter
from rpython.jit.backend.llgraph.runner import LLGraphCPU
from rpython.jit.metainterp.pyjitpl import MetaInterp, MetaInterpStaticData
from rpython.jit.metainterp.jitdriver import JitDriverStaticData
from rpython.jit.metainterp.warmstate import JitCell
from rpython.jit.metainterp.jitexc import DoneWithThisFrameInt
from rpython.jit.metainterp.optimizeopt.util import equaloplists
from rpython.rlib.jit import JitDriver


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
        resume_put_const(1, 0, 2)
        leave_frame()
        """, namespace= {'jitcode1': jitcode})
        descr = Descr()
        descr.rd_resume_bytecode = ResumeBytecode(resume_loop.operations)
        descr.rd_bytecode_position = 3
        metainterp = MockMetaInterp()
        metainterp.cpu = MockCPU()
        rebuild_from_resumedata(metainterp, "myframe", descr)
        assert len(metainterp.framestack) == 1
        f = metainterp.framestack[-1]
        assert f.registers_i[1].getint() == 13
        assert isinstance(f.registers_i[2], Const)
        assert f.registers_i[2].getint() == 1

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
        XXX

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

class AssemblerExecuted(Exception):
    pass

class FakeWarmstate(object):
    enable_opts = []
    
    def __init__(self):
        self.jitcell = JitCell()
    
    def get_location_str(self, greenkey):
        return "foo"

    def jit_cell_at_key(self, greenkey):
        return self.jitcell

    def attach_procedure_to_interp(self, *args):
        pass

    def execute_assembler(self, token, *args):
        raise AssemblerExecuted(*args)

def get_metainterp(assembler, no_reds=0):
    codewriter = CodeWriter()
    ssarepr = unformat_assembler(assembler, name='one')
    jitcode = codewriter.assembler.assemble(ssarepr)
    jitcode.is_portal = True
    reds = ['v' + str(i) for i in range(no_reds)]
    jitdriver_sd = JitDriverStaticData(JitDriver(greens = [],
                                                 reds = reds),
                                       None, INT)
    jitdriver_sd.mainjitcode = jitcode
    jitdriver_sd.warmstate = FakeWarmstate()
    jitdriver_sd.no_loop_header = False
    jitdriver_sd._get_printable_location_ptr = None
    codewriter.setup_jitdriver(jitdriver_sd)
    stats = Stats()
    cpu = LLGraphCPU(None, stats)
    metainterp_sd = MetaInterpStaticData(cpu, None)
    metainterp_sd.finish_setup(codewriter)
    return MetaInterp(metainterp_sd, jitdriver_sd), stats, jitdriver_sd
    
class TestResumeRecorder(object):
    def test_simple(self):
        assembler = """
        L1:
        -live- %i0, %i1, %i2
        jit_merge_point $0, I[], R[], F[], I[%i0, %i1, %i2], R[], F[]
        -live- %i0, %i1, %i2
        int_add %i2, %i0 -> %i2
        int_sub %i1, $1 -> %i1
        goto_if_not_int_gt %i1, $0, L2
        -live- %i0, %i1, %i2, L2
        loop_header $0
        goto L1
        ---
        L2:
        int_mul %i2, $2 -> %i0
        int_return %i0
        """
        metainterp, stats, jitdriver_sd = get_metainterp(assembler, no_reds=3)
        jitcode = jitdriver_sd.mainjitcode
        try:
            metainterp.compile_and_run_once(jitdriver_sd, 6, 7, 0)
        except AssemblerExecuted, e:
            assert e.args == (6, 6, 6)
        else:
            raise Exception("did not exit")
        resume_ops = [o for o in stats.operations if o.is_resume()]
        expected = parse("""
        [i0, i1, i2]
        enter_frame(-1, descr=jitcode)
        resume_put(i0, 0, 2)
        resume_put(i1, 0, 1)
        resume_put(i2, 0, 0)
        resume_set_pc(24)
        """, namespace={'jitcode': jitcode})
        equaloplists(resume_ops, expected.operations, cache=True)

    def test_live_boxes(self):
        assembler = """
        L1:
        -live- %i0, %i1, %i2
        jit_merge_point $0, I[], R[], F[], I[%i0, %i1, %i2], R[], F[]
        -live- %i0, %i1, %i2
        goto_if_not_int_gt %i1, $0, L2
        -live- %i0, %i1, L2
        loop_header $0
        goto L1
        ---
        L2:
        int_return %i0
        """
        metainterp, stats, jitdriver_sd = get_metainterp(assembler, no_reds=3)
        jitcode = jitdriver_sd.mainjitcode
        try:
            metainterp.compile_and_run_once(jitdriver_sd, -1, -1, 0)
        except DoneWithThisFrameInt:
            pass
        resume_ops = [o for o in stats.operations if o.is_resume()]
        expected = parse("""
        [i0, i1, i2]
        enter_frame(-1, descr=jitcode)
        resume_put(i0, 0, 1)
        resume_put(i1, 0, 0)
        resume_set_pc(16)
        leave_frame()
        """, namespace={'jitcode': jitcode})
        equaloplists(resume_ops, expected.operations, cache=True)

    def test_live_boxes_2(self):
        assembler = """
        L1:
        -live- %i0, %i1, %i2
        jit_merge_point $0, I[], R[], F[], I[%i0, %i1, %i2], R[], F[]
        -live- %i0, %i1, %i2
        goto_if_not_int_gt %i1, $0, L2
        -live- %i0, %i1, %i2, L2
        goto_if_not_int_gt %i2, $0, L2
        -live- %i0, %i2, L2
        loop_header $0
        goto L1
        ---
        L2:
        int_return %i0
        """
        metainterp, stats, jitdriver_sd = get_metainterp(assembler, no_reds=3)
        jitcode = jitdriver_sd.mainjitcode
        try:
            metainterp.compile_and_run_once(jitdriver_sd, -1, 13, -1)
        except DoneWithThisFrameInt:
            pass
        resume_ops = [o for o in stats.operations if o.is_resume()]
        expected = parse("""
        [i0, i1, i2]
        enter_frame(-1, descr=jitcode)
        resume_put(i0, 0, 2)
        resume_put(i1, 0, 1)
        resume_put(i2, 0, 0)
        resume_set_pc(16)
        resume_clear(0, 1)
        resume_set_pc(21)
        leave_frame()
        """, namespace={'jitcode': jitcode})
        equaloplists(resume_ops, expected.operations, cache=True)
