
from rpython.jit.metainterp.resoperation import rop
from rpython.jit.metainterp.history import BoxInt
from rpython.jit.codewriter.jitcode import JitCode
from rpython.rlib import rstack

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
        return self.finish()

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
            elif op.getopnum() == rop.RESUME_SET_PC:
                self.resume_set_pc(op.getarg(0).getint())
            elif not op.is_resume():
                pos += 1
                continue
            else:
                xxx
            pos += 1

    def resume_put(self, jitframe_pos_const, frame_no, frontend_position):
        jitframe_pos = jitframe_pos_const.getint()
        jitcode = self.get_jitcode(frame_no)
        if frontend_position < jitcode.num_regs_i():
            self.put_box_int(frame_no, frontend_position, jitframe_pos)
        elif frontend_position < (jitcode.num_regs_r() + jitcode.num_regs_i()):
            self.put_box_ref(frame_no, frontend_position - jitcode.num_regs_i(),
                             jitframe_pos)
        else:
            assert frontend_position < jitcode.num_regs()
            self.put_box_float(frame_no,
                               frontend_position - jitcode.num_regs_r()
                               - jitcode.num_regs_i(), jitframe_pos)

    def read_int(self, jitframe_pos):
        return self.metainterp.cpu.get_int_value(self.deadframe, jitframe_pos)

class DirectResumeReader(AbstractResumeReader):
    def __init__(self, binterpbuilder, cpu, deadframe):
        self.bhinterpbuilder = binterpbuilder
        self.cpu = cpu
        self.deadframe = deadframe
        self.bhinterp_stack = []

    def get_jitcode(self, no):
        return self.bhinterp_stack[no].jitcode

    def get_frame(self, no):
        return self.bhinterp_stack[no]

    def enter_frame(self, pc, jitcode):
        if pc != -1:
            self.bhinterp_stack[-1].position = pc
        self.bhinterp_stack.append(self.bhinterpbuilder.acquire_interp())
        self.bhinterp_stack[-1].setposition(jitcode, 0)

    def put_box_int(self, frame_no, frontend_position, jitframe_pos):
        val = self.cpu.get_int_value(self.deadframe, jitframe_pos)
        self.bhinterp_stack[frame_no].registers_i[frontend_position] = val

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

    def enter_frame(self, pc, jitcode):
        if pc != -1:
            self.metainterp.framestack[-1].pc = pc
        self.metainterp.newframe(jitcode)

    def leave_frame(self):
        self.metainterp.popframe()

    def put_box_int(self, frame_no, position, jitframe_pos):
        frame = self.metainterp.framestack[frame_no]
        frame.registers_i[position] = BoxInt(self.read_int(jitframe_pos))

    def put_box_ref(self, frame_no, position, jitframe_pos):
        frame = self.metainterp.framestack[frame_no]
        xxx
        frame.registers_r[position] = self.read_ref(jitframe_pos)

    def put_box_float(self, frame_no, position, jitframe_pos):
        frame = self.metainterp.framestack[frame_no]
        xxx
        frame.registers_f[position] = self.read_float(jitframe_pos)

    def finish(self):
        pass

def rebuild_from_resumedata(metainterp, deadframe, faildescr):
    BoxResumeReader(metainterp, deadframe).rebuild(faildescr)

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
