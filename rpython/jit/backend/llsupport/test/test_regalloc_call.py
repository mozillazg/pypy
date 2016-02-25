from rpython.jit.tool.oparser import parse
from rpython.jit.backend.x86.regalloc import RegAlloc
from rpython.jit.backend.x86.regloc import REGLOCS
from rpython.jit.backend.detect_cpu import getcpuclass
from rpython.jit.backend.x86.arch import DEFAULT_FRAME_BYTES
from rpython.jit.metainterp.history import TargetToken
from rpython.jit.metainterp.resoperation import (rop, ResOperation,
        AbstractValue, CountingDict)
from rpython.rtyper.lltypesystem import lltype
from rpython.rtyper.lltypesystem import rffi
from rpython.rtyper.annlowlevel import llhelper
from rpython.jit.codewriter.effectinfo import EffectInfo

eax, ecx, edx, ebx, esp, ebp, esi, edi, r8, r9, r10, r11, r12, r13, r14, r15 = REGLOCS
caller_saved = []
callee_saved = []

CPU = getcpuclass()

def get_param(i):
    # x86 specific!!
    ABI_PARAMS_REGISTERS = [edi, esi, edx, ecx, r8, r9]
    return ABI_PARAMS_REGISTERS[i]

def parse_loop(text, namespace={}):
    ops = parse(text, namespace=namespace)
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
        self.moves.append((prev_loc, loc, 'pos: ' + str(self.regalloc.rm.position)))
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
        self.initial_binding = {var: reg for var, reg in zip(trace.inputargs, binding) }
        tt._x86_arglocs = binding

    def run_allocation(self, free_regs=None):
        inputargs = self.trace.inputargs
        operations = self.trace.operations
        looptoken = FakeLoopToken()
        gcrefs = []

        # force naming of the variables!
        AbstractValue._repr_memo = CountingDict()
        for op in operations:
            for arg in op.getarglist():
                arg.repr_short(arg._repr_memo)
            op.repr_short(op._repr_memo)

        # setup the register allocator
        self.regalloc.prepare_loop(inputargs, operations, looptoken, gcrefs)

        # setup the initial binding the test requires
        for var, reg in self.initial_binding.items():
            self.regalloc.rm.reg_bindings[var] = reg

        # instead of having all machine registers, we want only to provide some
        self.regalloc.rm._change_regs(self.regalloc.all_regs,
                                      self.regalloc.caller_saved)
        if free_regs is None:
            self.regalloc.rm.update_free_registers(
                self.initial_binding.values())
        else:
            self.regalloc.rm.update_free_registers(
                set(self.regalloc.all_regs) - set(free_regs))
        self.regalloc.rm._check_invariants()
        # invoke the allocator!
        self.regalloc.walk_operations(inputargs, operations)

    def initial_register(self, var):
        return self.initial_binding.get(var, None)

    def is_caller_saved(self, var):
        return self.initial_register(var) in self.regalloc.caller_saved

    def is_callee_saved(self, var):
        return self.initial_register(var) in self.regalloc.callee_saved

    def move_count(self):
        return len(self.regalloc.assembler.moves)

    def regalloc_one_step(self, i):
        bindings = self.regalloc.rm.reg_bindings
        print bindings
        for var in bindings:
            if var not in self.initial_binding:
                self.initial_binding[var] = bindings[var]

class TestRegalloc(object):

    def setup_method(self, name):
        cpu = CPU(None, None)
        cpu.setup_once()

        def x(i):
            return i
        FPTR = lltype.Ptr(lltype.FuncType([rffi.UINT], rffi.UINT))
        func_ptr = llhelper(FPTR, x)
        calldescr = cpu.calldescrof(FPTR.TO, FPTR.TO.ARGS, FPTR.TO.RESULT, EffectInfo.MOST_GENERAL)
        targettoken = TargetToken()

        ns = {'calldescr': calldescr, 'targettoken':targettoken}
        self.namespace = ns

    def test_allocate_register_into_jump_register(self):
        tt, ops = parse_loop("""
        [p0,i1]
        i2 = int_add(i1,i1)
        i3 = int_add(i2,i1)
        jump(p0,i2)
        """)
        i2 = ops.operations[0]
        trace_alloc = TraceAllocation(ops, [eax, edx], [r8, r9], [eax, edx], tt)
        trace_alloc.run_allocation()
        i2 = trace_alloc.initial_register(i2)
        assert i2 == edx

    def test_single_move(self):
        tt, ops = parse_loop("""
        [p0,i0]
        i1 = int_add(i0,i0)
        i2 = int_add(i0,i1)
        guard_true(i2) []
        jump(p0,i1)
        """)
        trace_alloc = TraceAllocation(ops, [eax, edx], [r8, r9], [eax, edx], tt)
        trace_alloc.run_allocation()
        assert trace_alloc.move_count() == 1

    def test_prefer_callee_saved_register(self):
        tt, ops = parse_loop("""
        [p0,i0]
        i1 = int_add(i0,i0)
        i2 = int_sub(i0,i1)
        call_n(p0, i1, descr=calldescr)
        i3 = int_mul(i2,i0)
        jump(p0,i2)
        """, namespace=self.namespace)
        i1 = ops.operations[0]
        i2 = ops.operations[1]
        trace_alloc = TraceAllocation(ops, [eax, edx, get_param(0)],
                                      [r8, r9, r10], [eax, r10], tt)
        trace_alloc.run_allocation()
        # we force the allocation to immediately take the first call parameter register
        # the new regalloc will not shuffle register binding around (other than spilling)
        # in the best case this will reduce a lot of movement
        assert trace_alloc.initial_register(i1) == get_param(0)
        assert trace_alloc.is_caller_saved(i1)
        assert trace_alloc.is_callee_saved(i2)
        assert trace_alloc.move_count() == 1

    def test_call_allocate_first_param_to_callee2(self):
        tt, ops = parse_loop("""
        [p0,i0]

        label(p0,i0,descr=targettoken)

        i1 = int_add(i0,i0)
        i2 = int_add(i0,i1)
        call_n(p0, i1, descr=calldescr)
        guard_true(i2) []

        jump(p0,i1,descr=targettoken)
        """, namespace=self.namespace)
        i1 = ops.operations[0]
        i2 = ops.operations[1]
        trace_alloc = TraceAllocation(ops, [eax, edx], [r8, r9], [eax, edx], tt)
        trace_alloc.run_allocation()
        assert trace_alloc.initial_register(i1) == edx
        assert trace_alloc.initial_register(i2) != edx
        assert trace_alloc.move_count() == 1
