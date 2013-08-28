
from rpython.jit.metainterp.resoperation import rop
from rpython.jit.metainterp.history import BoxInt
from rpython.jit.codewriter.jitcode import JitCode

class AbstractResumeReader(object):
    def __init__(self, metainterp, deadframe):
        self.metainterp = metainterp
        self.deadframe = deadframe

    def rebuild(self, faildescr):
        bytecode = faildescr.rd_loop.rd_bytecode
        pos = faildescr.rd_bytecode_position
        self.interpret_until(bytecode, pos)

    def interpret_until(self, bytecode, until):
        pos = 0
        while pos < until:
            op = bytecode[pos]
            if op.getopnum() == rop.ENTER_FRAME:
                descr = op.getdescr()
                assert isinstance(descr, JitCode)
                self.enter_frame(op.getarg(0).getint(), descr)
            elif op.getopnum() == rop.LEAVE_FRAME:
                self.leave_frame()
            elif op.getopnum() == rop.RESUME_PUT:
                self.put(op.getarg(0).getint(), op.getarg(1).getint(),
                         op.getarg(2).getint())
            else:
                xxx
            pos += 1

    def enter_frame(self, pc, jitcode):
        if pc != -1:
            self.metainterp.framestack[-1].pc = pc
        self.metainterp.newframe(jitcode)

    def leave_frame(self):
        self.metainterp.popframe()

    def put(self, jitframe_index, depth, frontend_position):
        jitcode = self.metainterp.framestack[-1].jitcode
        cpu = self.metainterp.cpu
        frame = self.metainterp.framestack[- depth - 1]
        if frontend_position < jitcode.num_regs_i():
            self.write_int(frame, frontend_position,
                           cpu.get_int_value(self.deadframe, jitframe_index))
        elif frontend_position < (jitcode.num_regs_r() + jitcode.num_regs_i()):
            xxx
        else:
            assert frontend_position < jitcode.num_regs()
            xxx

class DirectResumeReader(AbstractResumeReader):
    pass

class BoxResumeReader(AbstractResumeReader):
    def write_int(self, frame, pos, value):
        frame.registers_i[pos] = BoxInt(value)

def rebuild_from_resumedata(metainterp, deadframe, faildescr):
    BoxResumeReader(metainterp, deadframe).rebuild(faildescr)
