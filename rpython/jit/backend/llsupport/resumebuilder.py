
from rpython.jit.metainterp.resoperation import rop
from rpython.jit.metainterp.history import ConstInt
from rpython.jit.codewriter.jitcode import JitCode

class LivenessAnalyzer(object):
    def __init__(self):
        self.framestack = []

    def enter_frame(self, jitcode):
        assert isinstance(jitcode, JitCode)
        self.framestack.append([None] * jitcode.num_regs())

    def put(self, value, depth, position):
        # - depth - 1 can be expressed as ~depth (haha)
        self.framestack[- depth - 1][position] = value

    def get_live_info(self):
        return self.framestack

    def leave_frame(self):
        self.framestack.pop()

class ResumeBuilder(object):
    def __init__(self, regalloc):
        self.framestack = []
        self.newops = []
        self.regalloc = regalloc

    def process(self, op):
        oplist[op.getopnum()](self, op)

    def process_enter_frame(self, op):
        self.framestack.append(op.getdescr())
        self.newops.append(op)

    def _find_position_for_box(self, v):
        return self.regalloc.loc(v).get_jitframe_position()

    def process_resume_put(self, op):
        pos = self._find_position_for_box(op.getarg(0))
        self.newops.append(op.copy_and_change(rop.BACKEND_PUT,
                                              args=[ConstInt(pos),
                                                    op.getarg(1),
                                                    op.getarg(2)]))

    def process_leave_frame(self, op):
        self.framestack.pop()
        self.newops.append(op)

    def get_position(self):
        return len(self.newops)

    def not_implemented_op(self, op):
        print "Not implemented", op.getopname()
        raise NotImplementedError(op.getopname())

oplist = [ResumeBuilder.not_implemented_op] * rop._LAST
for name, value in ResumeBuilder.__dict__.iteritems():
    if name.startswith('process_'):
        num = getattr(rop, name[len('process_'):].upper())
        oplist[num] = value

