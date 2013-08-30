
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
            elif not op.is_resume():
                pos += 1
                continue
            else:
                xxx
            pos += 1

    def resume_put(self, jitframe_index, depth, frontend_position):
        XXX
        jitcode = self.metainterp.framestack[-1].jitcode
        frame = self.metainterp.framestack[- depth - 1]
        if frontend_position < jitcode.num_regs_i():
            self.write_int(frame, frontend_position, jitframe_index)
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

    def enter_frame(self, pc, jitcode):
        if pc != -1:
            self.metainterp.framestack[-1].pc = pc
        self.metainterp.newframe(jitcode)

    def leave_frame(self):
        self.metainterp.popframe()

    def write_int(self, frame, pos, jitframe_index):
        cpu = self.metainterp.cpu
        value = cpu.get_int_value(self.deadframe, jitframe_index)
        frame.registers_i[pos] = BoxInt(value)

class ReconstructingResumeReader(AbstractResumeReader):
    def __init__(self):
        self.framestack = []

    def enter_frame(self, pc, jitcode):
        self.framestack.append([-1] * jitcode.num_regs())

    def put(self, jitframe_index, depth, frontend_position):
        self.framestack[- depth - 1][frontend_position] = jitframe_index

    def leave_frame(self):
        self.framestack.pop()

class SimpleResumeReader(AbstractResumeReader):
    def __init__(self):
        self.framestack = []

    def enter_frame(self, pc, jitcode):
        self.framestack.append(jitcode.num_regs())

    def put(self, *args):
        pass

    def leave_frame(self):
        self.framestack.pop()

def rebuild_from_resumedata(metainterp, deadframe, faildescr):
    BoxResumeReader(metainterp, deadframe).rebuild(faildescr)

def rebuild_locs_from_resumedata(faildescr):
    reader = ReconstructingResumeReader()
    reader.rebuild(faildescr)
    size = 0
    for frame in reader.framestack:
        size += len(frame)
    res = [-1] * size
    i = 0
    for frame in reader.framestack:
        res[i : i + len(frame)] = frame
        i += len(frame)
    return res
