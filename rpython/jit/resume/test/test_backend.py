
from rpython.jit.metainterp.history import JitCellToken
from rpython.jit.metainterp.history import BasicFailDescr
from rpython.jit.codewriter.jitcode import JitCode
from rpython.jit.tool.oparser import parse
from rpython.jit.metainterp.optimizeopt.util import equaloplists
from rpython.jit.resume.test.test_frontend import rebuild_locs_from_resumedata
from rpython.rtyper.lltypesystem import lltype

class MockJitCode(JitCode):
    def __init__(self, no, index):
        self.no = no
        self.global_index = index
        self.name = 'frame-%d' % index

    def num_regs(self):
        return self.no

    def __repr__(self):
        return 'MockJitCode(%d)' % self.no

class MockStaticData(object):
    def __init__(self, jitcodes, descrs):
        self.alljitcodes = jitcodes
        self.opcode_descrs = descrs

def preparse(inp):
    return "\n".join([s.strip() for s in inp.split("\n") if s.strip()])

class ResumeTest(object):
    def setup_method(self, meth):
        self.cpu = self.CPUClass(None, None)
        self.cpu.setup_once()

    def test_simple(self):
        jitcode = MockJitCode(3, 1)
        loop = parse("""
        [i0]
        enter_frame(-1, descr=jitcode)
        resume_put(i0, 0, 2)
        resume_put(1, 0, 1)
        guard_true(i0)
        leave_frame()
        """, namespace={'jitcode': jitcode})
        looptoken = JitCellToken()
        self.cpu.compile_loop(None, loop.inputargs, loop.operations,
                              looptoken)
        descr = loop.operations[3].getdescr()
        assert descr.rd_bytecode_position == 15
        staticdata = MockStaticData([None, jitcode], [])
        res = descr.rd_resume_bytecode.dump(staticdata,
                                            descr.rd_bytecode_position)
        expected_resume = preparse("""
        enter_frame -1 frame-1
        resume_put (3, 28) 0 2
        resume_put (1, 1) 0 1
        """)
        assert res == expected_resume

    def test_resume_new(self):
        jitcode = JitCode("name")
        jitcode.global_index = 1
        jitcode.setup(num_regs_i=1, num_regs_r=0, num_regs_f=0)
        S = lltype.GcStruct('S', ('field', lltype.Signed))
        structdescr = self.cpu.sizeof(S)
        structdescr.global_descr_index = 0
        fielddescr = self.cpu.fielddescrof(S, 'field')
        fielddescr.global_descr_index = 1
        namespace = {'jitcode':jitcode, 'structdescr':structdescr,
                     'fielddescr':fielddescr}
        loop = parse("""
        [i0, i1]
        enter_frame(-1, descr=jitcode)
        p0 = resume_new(descr=structdescr)
        resume_setfield_gc(p0, i0, descr=fielddescr)
        resume_put(p0, 0, 0)
        i2 = int_lt(i1, 13)
        guard_true(i2)
        leave_frame()
        finish()
        """, namespace=namespace)
        looptoken = JitCellToken()
        self.cpu.compile_loop(None, loop.inputargs, loop.operations,
                              looptoken)
        staticdata = MockStaticData([None, jitcode], [structdescr, fielddescr])
        descr = loop.operations[5].getdescr()
        res = descr.rd_resume_bytecode.dump(staticdata,
                                            descr.rd_bytecode_position)
        expected_resume = preparse("""
        enter_frame -1 name
        0 = resume_new 0
        resume_setfield_gc (2, 0) (3, 28) 1
        resume_put (2, 0) 0 0
        """)
        assert res == expected_resume

    def test_spill(self):
        jitcode = JitCode("name")
        jitcode.setup(num_regs_i=2, num_regs_r=0, num_regs_f=0)
        jitcode.global_index = 0
        faildescr1 = BasicFailDescr(1)
        faildescr2 = BasicFailDescr(2)
        loop = parse("""
        [i0]
        enter_frame(-1, descr=jitcode)
        i2 = int_add(i0, 1)
        resume_put(i2, 0, 1)
        guard_true(i0, descr=faildescr1)
        force_spill(i2)
        guard_true(i0, descr=faildescr2)
        leave_frame()
        """, namespace={'jitcode':jitcode, 'faildescr1':faildescr1,
                        'faildescr2':faildescr2})
        looptoken = JitCellToken()
        self.cpu.compile_loop(None, loop.inputargs, loop.operations,
                              looptoken)

        staticdata = MockStaticData([jitcode], [])
        expected_resume = preparse("""
        enter_frame -1 name
        resume_put (3, 1) 0 1
        resume_put (3, 29) 0 1
        """)
        descr1 = loop.operations[3].getdescr()
        descr2 = loop.operations[5].getdescr()
        assert descr1.rd_bytecode_position == 10
        assert descr2.rd_bytecode_position == 15
        res = descr2.rd_resume_bytecode.dump(staticdata,
                                             descr2.rd_bytecode_position)
        assert res == expected_resume

    def test_bridge(self):
        jitcode = JitCode("name")
        jitcode.global_index = 0
        jitcode.setup(num_regs_i=1, num_regs_r=0, num_regs_f=0)
        loop = parse("""
        [i0]
        enter_frame(-1, descr=jitcode)
        i1 = int_lt(i0, 10)
        resume_put(i1, 0, 0)
        guard_true(i1)
        leave_frame()
        """, namespace={'jitcode': jitcode})

        looptoken = JitCellToken()
        self.cpu.compile_loop(None, loop.inputargs, loop.operations,
                              looptoken)

        descr = loop.operations[3].getdescr()

        bridge = parse("""
        [i0]
        force_spill(i0)
        guard_false(i0)
        """)
        staticdata = MockStaticData([jitcode], [])
        locs = rebuild_locs_from_resumedata(descr, staticdata)
        self.cpu.compile_bridge(None, descr, [bridge.inputargs], locs,
                                bridge.operations, looptoken)

        descr = bridge.operations[-1].getdescr()
        res = descr.rd_resume_bytecode.dump(staticdata,
                                            descr.rd_bytecode_position)
        assert res == "resume_put (3, 28) 0 0"
