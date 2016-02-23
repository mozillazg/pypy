from rpython.jit.tool.oparser import parse
from rpython.jit.backend.x86.regalloc import RegAlloc
from rpython.jit.backend.x86.regloc import REGLOCS
from rpython.jit.backend.detect_cpu import getcpuclass
from rpython.jit.backend.x86.arch import DEFAULT_FRAME_BYTES
from rpython.jit.metainterp.history import TargetToken
from rpython.jit.metainterp.resoperation import (rop, ResOperation,
        AbstractValue, CountingDict)

class FakeReg(object):
    def __init__(self, i):
        self.n = i
    def __repr__(self):
        return 'r%d' % self.n

eax, ecx, edx, ebx, esp, ebp, esi, edi, r8, r9, r10, r11, r12, r13, r14, r15 = REGLOCS
caller_saved = []
callee_saved = []

CPU = getcpuclass()

def parse_loop(text):
    ops = parse(text)
    tt = None
    tt = TargetToken(ops.operations[-1].getdescr())
    for op in ops.operations:
        if op.getopnum() == rop.JUMP:
            assert tt is not None
            op.setdescr(tt)
    return tt, ops

class FakeMachineCodeBuilder(object):
    _frame_size = DEFAULT_FRAME_BYTES
    def mark_op(self, op):
        pass
    def get_relative_pos(self): return 0
    def UD2(self): pass

class FakeAssembler(object):
    cpu = CPU(None, None)
    current_clt = None
    target_tokens_currently_compiling = {}
    def __init__(self, regalloc):
        self.mc = FakeMachineCodeBuilder()
        self.regalloc = regalloc
        self.moves = []
        self.pushes = []

    def regalloc_mov(self, prev_loc, loc):
        self.moves.append((prev_loc, loc))
        print "mov bindings: ", self.regalloc.rm.reg_bindings
        print prev_loc, "->", loc
    def regalloc_push(self, loc):
        self.pushes.append(loc)
    def regalloc_pop(self, loc):
        pass
    def dump(self, *args): pass
    def regalloc_perform(self, *args): pass
    def regalloc_perform_guard(self, *args): pass
    def guard_success_cc(self, *args): pass
    def label(self): pass
    def closing_jump(self, target): pass

CPURegalloc = RegAlloc
class FakeRegAlloc(CPURegalloc):
    def __init__(self, tracealloc, caller_saved, callee_saved):
        self.caller_saved = caller_saved
        self.callee_saved = callee_saved
        self.all_regs = caller_saved[:] + callee_saved
        self.free_regs = caller_saved[:] + callee_saved
        CPURegalloc.__init__(self, FakeAssembler(self), False)
        self.tracealloc = tracealloc
        self.steps = set()

    def flush_loop(self):
        pass

    def possibly_free_vars_for_op(self, op):
        i = self.rm.position
        if i not in self.steps:
            self.steps.add(i)
            self.tracealloc.regalloc_one_step(i)
        CPURegalloc.possibly_free_vars_for_op(self, op)

class FakeLoopToken(object):
    def __init__(self):
        self.compiled_loop_token = None

class TraceAllocation(object):
    def __init__(self, trace, caller_saved, callee_saved, binding, tt):
        self.trace = trace
        self.regalloc = FakeRegAlloc(self, caller_saved, callee_saved)
        self.initial_binding = { var: reg for var, reg in zip(trace.inputargs, binding) }
        looptoken = FakeLoopToken()
        gcrefs = []
        tt._x86_arglocs = binding

        AbstractValue._repr_memo = CountingDict()
        for op in trace.operations:
            for arg in op.getarglist():
                arg.repr_short(arg._repr_memo)
                pass
            op.repr_short(op._repr_memo)
        self.regalloc.prepare_loop(self.trace.inputargs, self.trace.operations, looptoken, gcrefs)

        for var, reg in zip(trace.inputargs, binding):
            self.regalloc.rm.reg_bindings[var] = reg
        fr = self.regalloc.free_regs
        self.regalloc.rm.free_regs = [reg for reg in fr if reg not in binding]

        self.regalloc.rm.all_regs = self.regalloc.all_regs
        self.regalloc.rm.save_around_call_regs = self.regalloc.caller_saved

        self.regalloc.walk_operations(trace.inputargs, trace.operations)

    def initial_register(self, var):
        return self.initial_binding.get(var, None)

    def move_count(self):
        return len(self.regalloc.assembler.moves)

    def regalloc_one_step(self, i):
        bindings = self.regalloc.rm.reg_bindings
        print bindings
        for var in bindings:
            if var not in self.initial_binding:
                self.initial_binding[var] = bindings[var]

class TestRegalloc(object):

    def test_allocate_register_into_jump_register(self):
        tt, ops = parse_loop("""
        [p0,i1]
        i2 = int_add(i1,i1)
        i3 = int_add(i2,i1)
        jump(p0,i2)
        """)
        trace_alloc = TraceAllocation(ops, [eax, edx], [r8, r9], [eax, edx], tt)
        i2 = trace_alloc.initial_register('i2')
        assert i2 == edx

    def test_2allocate_register_into_jump_register2(self):
        tt, ops = parse_loop("""
        [p0,i1]
        i2 = int_add(i1,i1)
        i3 = int_add(i2,i1)
        guard_true(i3) []
        jump(p0,i2)
        """)
        i2 = ops.operations[0]
        i3 = ops.operations[1]
        trace_alloc = TraceAllocation(ops, [eax, edx], [r8, r9], [eax, edx], tt)
        assert trace_alloc.initial_register(i2) == edx
        assert trace_alloc.initial_register(i3) != edx

