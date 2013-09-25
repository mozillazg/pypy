
from rpython.jit.metainterp.resoperation import rop
from rpython.jit.metainterp.history import BoxInt
from rpython.jit.codewriter.jitcode import JitCode

class ResumeBytecode(object):
    def __init__(self, opcodes, parent=None, parent_position=-1, loop=None):
        self.opcodes = opcodes
        self.parent = parent
        self.parent_position = parent_position
        self.loop = loop

class AbstractResumeReader(object):
    def rebuild(self, faildescr):
        self._rebuild_until(faildescr.rd_resume_bytecode,
                            faildescr.rd_bytecode_position)
        self.finish()

    def finish(self):
        pass

    def _rebuild_until(self, rb, position):
        if rb.parent is not None:
            self._rebuild_until(rb.parent, rb.parent_position)
        self.interpret_until(rb.opcodes, position)

    def interpret_until(self, bytecode, until, pos=0):
        while pos < until:
            op = bytecode[pos]
            if op.getopnum() == rop.ENTER_FRAME:
                descr = op.getdescr()
                assert isinstance(descr, JitCode)
                self.enter_frame(op.getarg(0).getint(), descr)
            elif op.getopnum() == rop.LEAVE_FRAME:
                self.leave_frame()
            elif op.getopnum() == rop.RESUME_PUT:
                self.resume_put(op.getarg(0), op.getarg(1).getint(),
                         op.getarg(2).getint())
            elif op.getopnum() == rop.RESUME_NEW:
                self.resume_new(op.result, op.getdescr())
            elif op.getopnum() == rop.RESUME_SETFIELD_GC:
                self.resume_setfield_gc(op.getarg(0), op.getarg(1),
                                        op.getdescr())
            elif op.getopnum() == rop.BACKEND_ATTACH:
                self.resume_backend_attach(op.getarg(0), op.getarg(1).getint())
            elif not op.is_resume():
                pos += 1
                continue
            else:
                xxx
            pos += 1

    def resume_put(self, box, depth, frontend_position):
        jitcode = self.metainterp.framestack[-1].jitcode
        frame = self.metainterp.framestack[- depth - 1]
        if frontend_position < jitcode.num_regs_i():
            self.put_box_int(frame, frontend_position, box)
        elif frontend_position < (jitcode.num_regs_r() + jitcode.num_regs_i()):
            xxx
        else:
            assert frontend_position < jitcode.num_regs()
            xxx

class DirectResumeReader(AbstractResumeReader):
    pass

class BoxResumeReader(AbstractResumeReader):
    def __init__(self, metainterp, deadframe):
        self.metainterp = metainterp
        self.deadframe = deadframe
        self.backend_values = {}

    def resume_backend_attach(self, box, position):
        self.backend_values[box] = position

    def enter_frame(self, pc, jitcode):
        if pc != -1:
            self.metainterp.framestack[-1].pc = pc
        self.metainterp.newframe(jitcode)

    def leave_frame(self):
        self.metainterp.popframe()

    def put_box_int(self, frame, position, box):
        frame.registers_i[position] = box

    def finish(self):
        cpu = self.metainterp.cpu
        for box, position in self.backend_values.iteritems():
            if box.type == 'i':
                intval = cpu.get_int_value(self.deadframe, position)
                assert isinstance(box, BoxInt)
                box.value = intval
            else:
                xxx

def rebuild_from_resumedata(metainterp, deadframe, faildescr):
    BoxResumeReader(metainterp, deadframe).rebuild(faildescr)
