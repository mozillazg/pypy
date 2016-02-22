from rpython.jit.tool.oparser import parse
from rpython.jit.backend.x86.regalloc import RegAlloc
from rpython.jit.backend.detect_cpu import getcpuclass
from rpython.jit.backend.x86.arch import DEFAULT_FRAME_BYTES
from rpython.jit.metainterp.history import TargetToken
from rpython.jit.metainterp.resoperation import rop, ResOperation

class FakeReg(object):
    def __init__(self, i):
        self.n = i
    def __repr__(self):
        return 'r%d' % self.n

r1, r2, r3, r4, r5, r6, r7, r8, r9, r10 = [FakeReg(i) for i in range(1,11)]

CPU = getcpuclass()

def parse_loop(text):
    ops = parse(text)
    tt = None
    tt = TargetToken(ops.operations[-1].getdescr())
    ops.operations = [ResOperation(rop.LABEL, ops.inputargs, None, descr=tt)] + ops.operations
    for op in ops.operations:
        if op.getopnum() == rop.JUMP:
            assert tt is not None
            op.setdescr(tt)
    return ops

class FakeMachineCodeBuilder(object):
    _frame_size = DEFAULT_FRAME_BYTES
    def mark_op(self, op):
        pass
    def get_relative_pos(self): return 0
class FakeAssembler(object):
    cpu = CPU(None, None)
    current_clt = None
    target_tokens_currently_compiling = {}
    def __init__(self):
        self.mc = FakeMachineCodeBuilder()
    def regalloc_mov(self, prev, loc): pass
    def dump(self, *args): pass
    def regalloc_perform(self, *args): pass
    def label(self): pass
    def closing_jump(self, target): pass

CPURegalloc = RegAlloc
class FakeRegAlloc(CPURegalloc):
    def __init__(self, caller_saved, callee_saved):
        self.all_regs = callee_saved[:] + callee_saved
        CPURegalloc.__init__(self, FakeAssembler(), False)
    def flush_loop(self): pass

class FakeLoopToken(object):
    def __init__(self):
        self.compiled_loop_token = None

class TraceAllocation(object):
    def __init__(self, trace, caller_saved, callee_saved, binding):
        self.trace = trace
        self.regalloc = FakeRegAlloc(caller_saved, callee_saved)
        self.initial_binding = binding
        looptoken = FakeLoopToken()
        gcrefs = None
        for op in trace.operations:
            for arg in op.getarglist():
                pass
            pass
        self.regalloc.prepare_loop(self.trace.inputargs, self.trace.operations, looptoken, gcrefs)
        self.regalloc.walk_operations(trace.inputargs, trace.operations)

    def initial_register(self, name):
        pass

class TestRegalloc(object):

    def test_allocate_register_into_jump_register(self):
        ops = parse_loop("""
        [p0,i1]
        i2 = int_add(i1,i1)
        i3 = int_add(i2,i1)
        jump(p0,i2)
        """)
        trace_alloc = TraceAllocation(ops, [r1, r2], [r3, r4], {'p0': r1, 'i1': r2})
        i2 = trace_alloc.initial_register('i2')
        i1 = trace_alloc.initial_register('i1')
        assert i2 == i1

