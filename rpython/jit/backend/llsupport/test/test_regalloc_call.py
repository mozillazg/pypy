from rpython.jit.tool.oparser import parse
from rpython.jit.backend.x86.regalloc import RegAlloc
from rpython.jit.backend.x86.regloc import REGLOCS
from rpython.jit.backend.detect_cpu import getcpuclass
from rpython.jit.backend.x86.arch import DEFAULT_FRAME_BYTES
from rpython.jit.metainterp.history import TargetToken
from rpython.jit.metainterp.resoperation import rop, ResOperation

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
class FakeAssembler(object):
    cpu = CPU(None, None)
    current_clt = None
    target_tokens_currently_compiling = {}
    def __init__(self):
        self.mc = FakeMachineCodeBuilder()
        self.moves = []
        self.pushes = []

    def regalloc_mov(self, prev_loc, loc):
        self.moves.append((prev_loc, loc))
    def regalloc_push(self, loc):
        import pdb; pdb.set_trace()
        self.pushes.append(loc)
    def regalloc_pop(self, loc):
        pass

    def regalloc_mov(self, prev, loc): pass
    def dump(self, *args): pass
    def regalloc_perform(self, *args): pass
    def label(self): pass
    def closing_jump(self, target): pass

CPURegalloc = RegAlloc
class FakeRegAlloc(CPURegalloc):
    def __init__(self, tracealloc, caller_saved, callee_saved):
        self.caller_saved = caller_saved
        self.callee_saved = callee_saved
        self.all_regs = caller_saved[:] + callee_saved
        self.free_regs = caller_saved[:] + callee_saved
        CPURegalloc.__init__(self, FakeAssembler(), False)
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
        self.initial_binding = { str(var): reg for var, reg in zip(trace.inputargs, binding) }
        looptoken = FakeLoopToken()
        gcrefs = None
        tt._x86_arglocs = binding

        for op in trace.operations:
            for arg in op.getarglist():
                pass
        self.regalloc.prepare_loop(self.trace.inputargs, self.trace.operations, looptoken, gcrefs)

        for var, reg in zip(trace.inputargs, binding):
            self.regalloc.rm.reg_bindings[var] = reg
        fr = self.regalloc.free_regs
        self.regalloc.rm.free_regs = [reg for reg in fr if reg not in binding]

        self.regalloc.rm.all_regs = self.regalloc.all_regs
        self.regalloc.rm.save_around_call_regs = self.regalloc.caller_saved

        self.regalloc.walk_operations(trace.inputargs, trace.operations)

    def initial_register(self, name):
        return self.initial_binding.get(name, None)

    def move_count(self):
        return len(self.regalloc.assembler.moves)

    def regalloc_one_step(self, i):
        bindings = self.regalloc.rm.reg_bindings
        for var in bindings:
            varname = str(var)
            if varname not in self.initial_binding:
                self.initial_binding[varname] = bindings[var]

class TestRegalloc(object):

    def test_allocate_register_into_jump_register(self):
        tt, ops = parse_loop("""
        [i0,i1]
        i2 = int_add(i0,i1)
        i3 = int_add(i2,i1)
        i4 = int_add(i3,i0)
        jump(i4,i2)
        """)
        trace_alloc = TraceAllocation(ops, [eax, edx], [r8, r9], [eax, edx], tt)
        assert trace_alloc.initial_register('i2') == edx
        assert trace_alloc.initial_register('i0') == eax
        assert trace_alloc.initial_register('i4') == eax
        assert trace_alloc.move_count() == 0

