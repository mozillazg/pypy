
from rpython.jit.metainterp.resoperation import rop
from rpython.jit.metainterp.history import BoxInt, BoxPtr, BoxFloat
from rpython.jit.codewriter.jitcode import JitCode
from rpython.rlib import rstack

class ResumeBytecode(object):
    def __init__(self, opcodes, parent=None, parent_position=-1, loop=None):
        self.opcodes = opcodes
        self.parent = parent
        self.parent_position = parent_position
        self.loop = loop

class ResumeFrame(object):
    def __init__(self, jitcode):
        self.registers = [-1] * jitcode.num_regs()
        self.jitcode = jitcode
        self.pc = -1
        
class AbstractResumeReader(object):
    def __init__(self):
        self.framestack = []

    def rebuild(self, faildescr):
        self._rebuild_until(faildescr.rd_resume_bytecode,
                            faildescr.rd_bytecode_position)
        return self.finish()

    def finish(self):
        pass

    def enter_frame(self, pc, jitcode):
        if self.framestack:
            assert pc != -1
            self.framestack[-1].pc = pc
        self.framestack.append(ResumeFrame(jitcode))

    def resume_put(self, jitframe_pos_const, frame_no, frontend_position):
        jitframe_pos = jitframe_pos_const.getint()
        self.framestack[frame_no].registers[frontend_position] = jitframe_pos

    def resume_set_pc(self, pc):
        self.framestack[-1].pc = pc

    def leave_frame(self):
        self.framestack.pop()

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
            elif op.getopnum() == rop.RESUME_SET_PC:
                self.resume_set_pc(op.getarg(0).getint())
            elif not op.is_resume():
                pos += 1
                continue
            else:
                xxx
            pos += 1

    def read_int(self, jitframe_pos):
        return self.metainterp.cpu.get_int_value(self.deadframe, jitframe_pos)

class DirectResumeReader(AbstractResumeReader):
    def __init__(self, binterpbuilder, cpu, deadframe):
        self.bhinterpbuilder = binterpbuilder
        self.cpu = cpu
        self.deadframe = deadframe
        self.bhinterp_stack = []

    def enter_frame(self, pc, jitcode):
        if pc != -1:
            self.bhinterp_stack[-1].position = pc
        self.bhinterp_stack.append(self.bhinterpbuilder.acquire_interp())
        self.bhinterp_stack[-1].setposition(jitcode, 0)

    def put_box_int(self, frame_no, frontend_position, jitframe_pos):
        val = self.cpu.get_int_value(self.deadframe, jitframe_pos)
        self.bhinterp_stack[frame_no].registers_i[frontend_position] = val

    def put_box_ref(self, frame_no, frontend_position, jitframe_pos):
        val = self.cpu.get_ref_value(self.deadframe, jitframe_pos)
        self.bhinterp_stack[frame_no].registers_r[frontend_position] = val

    def resume_set_pc(self, pc):
        self.bhinterp_stack[-1].position = pc

    def leave_frame(self):
        bhinterp = self.bhinterp_stack.pop()
        self.bhinterpbuilder.release_interp(bhinterp)

    def finish(self):
        self.bhinterp_stack[0].nextblackholeinterp = None
        for i in range(1, len(self.bhinterp_stack)):
            self.bhinterp_stack[i].nextblackholeinterp = self.bhinterp_stack[i - 1]
        return self.bhinterp_stack[-1]

class BoxResumeReader(AbstractResumeReader):
    def __init__(self, metainterp, deadframe):
        self.metainterp = metainterp
        self.deadframe = deadframe
        AbstractResumeReader.__init__(self)

    def get_int_box(self, pos):
        return BoxInt(self.metainterp.cpu.get_int_value(self.deadframe, pos))

    def get_ref_box(self, pos):
        return BoxPtr(self.metainterp.cpu.get_ref_value(self.deadframe, pos))

    def get_float_box(self, pos):
        return BoxFloat(self.metainterp.cpu.get_float_value(self.deadframe,
                                                            pos))

    def finish(self):
        for frame in self.framestack:
            jitcode = frame.jitcode
            miframe = self.metainterp.newframe(jitcode)
            miframe.pc = frame.pc
            pos = 0
            for i in range(jitcode.num_regs_i()):
                miframe.registers_i[i] = self.get_int_box(frame.registers[pos])
                pos += 1
            for i in range(jitcode.num_regs_r()):
                miframe.registers_r[i] = self.get_ref_box(frame.registers[pos])
                pos += 1
            for i in range(jitcode.num_regs_f()):
                jitframe_pos = frame.registers[pos]
                miframe.registers_f[i] = self.get_float_box(jitframe_pos)
                pos += 1
            
def rebuild_from_resumedata(metainterp, deadframe, faildescr):
    return BoxResumeReader(metainterp, deadframe).rebuild(faildescr)

def blackhole_from_resumedata(interpbuilder, metainterp_sd, faildescr,
                              deadframe, all_virtuals=None):
    assert all_virtuals is None
    #rstack._stack_criticalcode_start()
    #try:
    #    xxx consume vrefs and random shit
    #finally:
    #    rstack._stack_criticalcode_stop()
    cpu = metainterp_sd.cpu
    last_bhinterp = DirectResumeReader(interpbuilder, cpu,
                                       deadframe).rebuild(faildescr)
    
    return last_bhinterp
