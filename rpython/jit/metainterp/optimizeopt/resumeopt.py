
from rpython.jit.metainterp.history import ConstInt, BoxPtr
from rpython.jit.metainterp.resoperation import rop, ResOperation
from rpython.jit.codewriter.jitcode import JitCode

class ResumeFrame(object):
    def __init__(self, pc, jitcode):
        self.pc = pc
        assert isinstance(jitcode, JitCode)
        self.jitcode = jitcode
        self.values = [None] * jitcode.num_regs()

class OptResumeBuilder(object):
    def __init__(self, opt):
        self.framestack = []
        self.last_flushed_pos = 0
        self.opt = opt
        self.virtuals = {}

    def enter_frame(self, pc, jitcode):
        self.framestack.append(ResumeFrame(pc, jitcode))

    def leave_frame(self, op):
        #if self.last_flushed_pos < len(self.framestack) - 1:
        #    self.emit_missing_enter_frame()
        #else:
        #    self.opt.emit_operation(op)
        #    self.last_flushed_pos -= 1
        self.framestack.pop()

    def resume_flush(self):
        return
        for i in range(self.last_flushed_pos, len(self.framestack)):
            frame = self.framestack[i]
            resop = ResOperation(rop.ENTER_FRAME, [ConstInt(frame.pc)],
                                 None, descr=frame.jitcode)
            self.opt.emit_operation(resop)
        self.last_flushed_pos = len(self.framestack)

    def resume_put(self, op):
        self.resume_flush()
        box = op.getarg(0)
        value = self.opt.getvalue(box)
        if value.is_virtual():
            op = ResOperation(rop.RESUME_PUT, [value.resume_box,
                                               op.getarg(1),
                                               op.getarg(2)], None)
            self.opt._newoperations.append(op)
            no = op.getarg(2).getint()
            self.framestack[op.getarg(1).getint()].values[no] = value
        else:
            self.opt.emit_operation(op)

    def new_virtual(self, box):
        xxx
        self.optimizer.emit_operation(rop.RESUME_NEW)

    def new_virtual_struct(self, box, vstruct, structdescr):
        newbox = BoxPtr()
        vstruct.resume_box = newbox
        op = ResOperation(rop.RESUME_NEW, [], newbox, descr=structdescr)
        self.opt._newoperations.append(op)

    def setfield(self, box, fieldbox, descr):
        op = ResOperation(rop.RESUME_SETFIELD_GC, [box, fieldbox], None,
                          descr=descr)
        self.opt._newoperations.append(op)

    def guard_seen(self, op, pendingfields):
        for frame_pos, frame in enumerate(self.framestack):
            for pos_in_frame, value in enumerate(frame.values):
                if value is not None and value.is_forced_virtual():
                    op = ResOperation(rop.RESUME_PUT, [value.get_resume_box(),
                                                       ConstInt(frame_pos),
                                                       ConstInt(pos_in_frame)],
                                                       None)
                    self.opt._newoperations.append(op)
                    frame.values[pos_in_frame] = None
