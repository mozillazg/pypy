
import sys
from rpython.jit.metainterp.resoperation import rop
from rpython.jit.metainterp.history import BoxInt, BoxPtr, BoxFloat, ConstInt,\
     Box, INT, REF, FLOAT
from rpython.jit.metainterp import history
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

TAGCONST = 0x0
TAGVIRTUAL = 0x2
TAGBOX = 0x3
TAGSMALLINT = 0x1

TAGOFFSET = 2

class Virtual(object):
    def __init__(self, pos, descr):
        self.pos = pos
        self.fields = {}
        self.descr = descr


class AbstractResumeReader(object):
    """ A resume reader that can follow resume until given point. Consult
    the concrete classes for details
    """
    
    def __init__(self):
        self.framestack = []
        self.consts = [] # XXX cache?
        self.virtuals = {}
        self.virtual_list = []

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

    def encode_box(self, pos):
        return TAGBOX | (pos << TAGOFFSET)

    def encode_virtual(self, box):
        return TAGVIRTUAL | (self.virtuals[box].pos << TAGOFFSET)

    def encode_const(self, const):
        if isinstance(const, ConstInt) and const.getint() < (sys.maxint >> 3):
            return TAGSMALLINT | (const.getint() << TAGOFFSET)
        self.consts.append(const)
        return TAGCONST | ((len(self.consts) - 1) << TAGOFFSET)

    def decode(self, pos):
        return pos & 0x3, pos >> TAGOFFSET

    def resume_put(self, jitframe_pos_box, frame_no, frontend_position):
        if isinstance(jitframe_pos_box, Box):
            jitframe_pos = self.encode_virtual(jitframe_pos_box)
        else:
            jitframe_pos = self.encode_box(jitframe_pos_box.getint())
        self.framestack[frame_no].registers[frontend_position] = jitframe_pos

    def encode(self, box):
        xxx

    def resume_new(self, box, descr):
        # XXX make it a list
        v = Virtual(len(self.virtual_list), descr)
        self.virtuals[box] = v
        self.virtual_list.append(v)

    def resume_setfield_gc(self, box, fieldbox, descr):
        # XXX optimize fields
        self.virtuals[box].fields[descr] = self.encode(fieldbox)

    def resume_clear(self, frame_no, frontend_position):
        self.framestack[frame_no].registers[frontend_position] = -1

    def resume_put_const(self, const, frame_no, frontend_position):
        pos = self.encode_const(const)
        self.framestack[frame_no].registers[frontend_position] = pos

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
            elif op.getopnum() == rop.RESUME_CLEAR:
                self.resume_clear(op.getarg(0).getint(),
                                  op.getarg(1).getint())
            elif not op.is_resume():
                pos += 1
                continue
            else:
                xxx
            pos += 1

    def read_int(self, jitframe_pos):
        return self.metainterp.cpu.get_int_value(self.deadframe, jitframe_pos)

class DirectResumeReader(AbstractResumeReader):
    """ Directly read values from the jitframe and put them in the blackhole
    interpreter
    """
    
    def __init__(self, binterpbuilder, cpu, deadframe):
        self.bhinterpbuilder = binterpbuilder
        self.cpu = cpu
        self.deadframe = deadframe
        AbstractResumeReader.__init__(self)

    def finish(self):
        nextbh = None
        for frame in self.framestack:
            curbh = self.bhinterpbuilder.acquire_interp()
            curbh.nextblackholeinterp = nextbh
            nextbh = curbh
            jitcode = frame.jitcode
            curbh.setposition(jitcode, frame.pc)
            pos = 0
            for i in range(jitcode.num_regs_i()):
                self.store_int_value(curbh, i, frame.registers[pos])
                pos += 1
            for i in range(jitcode.num_regs_r()):
                self.store_ref_value(curbh, i, frame.registers[pos])
                pos += 1
            for i in range(jitcode.num_regs_f()):
                self.store_float_value(curbh, i, frame.registers[pos])
                pos += 1
        return curbh

    def store_int_value(self, curbh, i, jitframe_pos):
        if jitframe_pos >= 0:
            curbh.registers_i[i] = self.cpu.get_int_value(
                self.deadframe, jitframe_pos)
        elif jitframe_pos < -1:
            curbh.registers_i[i] = self.consts[-jitframe_pos - 2].getint()

    def store_ref_value(self, curbh, i, jitframe_pos):
        if jitframe_pos >= 0:
            curbh.registers_r[i] = self.cpu.get_ref_value(
                self.deadframe, jitframe_pos)
        elif jitframe_pos < -1:
            curbh.registers_r[i] = self.consts[-jitframe_pos - 2].getref_base()

    def store_float_value(self, curbh, i, jitframe_pos):
        if jitframe_pos >= 0:
            curbh.registers_f[i] = self.cpu.get_float_value(
                self.deadframe, jitframe_pos)
        elif jitframe_pos < -1:
            curbh.registers_f[i] = self.consts[-jitframe_pos - 2].getfloat()

class BoxResumeReader(AbstractResumeReader):
    """ Create boxes corresponding to the resume and store them in
    the metainterp
    """
    
    def __init__(self, metainterp, deadframe):
        self.metainterp = metainterp
        self.deadframe = deadframe
        AbstractResumeReader.__init__(self)

    def get_box_value(self, encoded_pos, TP):
        if encoded_pos == -1:
            return None
        if encoded_pos in self.cache:
            return self.cache[encoded_pos]
        tag, pos = self.decode(encoded_pos)
        if tag == TAGBOX:
            if TP == INT:
                val = self.metainterp.cpu.get_int_value(self.deadframe, pos)
                res = BoxInt(val)
            else:
                xxx
            self.cache[encoded_pos] = res
            return res
        elif tag == TAGSMALLINT:
            return ConstInt(pos)
        elif tag == TAGCONST:
            return self.consts[pos]
        else:
            assert tag == TAGVIRTUAL
            virtual = self.virtual_list[pos]
            virtual_box = self.allocate_struct(virtual)
            for fielddescr, encoded_field_pos in virtual.fields.iteritems():
                self.setfield(virtual, fielddescr, encoded_field_pos)
            self.cache[encoded_pos] = virtual_box
            return virtual_box

    def allocate_struct(self, virtual):
        return self.metainterp.execute_and_record(rop.NEW, virtual.descr)

    def setfield(self, virtual, fielddescr, encoded_field_pos):
        xxx

    def store_int_box(self, res, pos, miframe, i, jitframe_pos):
        box = self.get_box_value(jitframe_pos, INT)
        if box is None:
            return
        miframe.registers_i[i] = box
        res[-1][pos] = box

    def store_ref_box(self, res, pos, miframe, i, jitframe_pos):
        box = self.get_box_value(jitframe_pos, REF)
        if box is None:
            return
        miframe.registers_r[i] = box
        res[-1][pos] = box
        return
        xxx
        if jitframe_pos in self.cache:
            box = self.cache[jitframe_pos]
        elif jitframe_pos == -1:
            return
        elif jitframe_pos >= 0:
            box = BoxPtr(self.metainterp.cpu.get_ref_value(self.deadframe,
                                                           jitframe_pos))
        elif jitframe_pos <= -2:
            box = self.consts[-jitframe_pos - 2]
        miframe.registers_r[i] = box
        self.cache[jitframe_pos] = box
        res[-1][pos] = box

    def store_float_box(self, res, pos, miframe, i, jitframe_pos):
        box = self.get_box_value(jitframe_pos)
        if box is None:
            return
        xxx
        if jitframe_pos in self.cache:
            box = self.cache[jitframe_pos]
        elif jitframe_pos == -1:
            return
        elif jitframe_pos >= 0:
            box = BoxFloat(self.metainterp.cpu.get_float_value(self.deadframe,
                                                             jitframe_pos))
        elif jitframe_pos <= -2:
            box = self.consts[-jitframe_pos - 2]
        miframe.registers_f[i] = box
        self.cache[jitframe_pos] = box
        res[-1][pos] = box

    def finish(self):
        res = []
        self.cache = {}
        for frame in self.framestack:
            jitcode = frame.jitcode
            res.append([None] * jitcode.num_regs())
            miframe = self.metainterp.newframe(jitcode, record_resume=False)
            miframe.pc = frame.pc
            pos = 0
            for i in range(jitcode.num_regs_i()):
                self.store_int_box(res, pos, miframe, i, frame.registers[pos])
                pos += 1
            for i in range(jitcode.num_regs_r()):
                self.store_ref_box(res, pos, miframe, i, frame.registers[pos])
                pos += 1
            for i in range(jitcode.num_regs_f()):
                self.store_float_box(res, pos, miframe, i, frame.registers[pos])
                pos += 1
        self.cache = None
        return res, [f.registers for f in self.framestack]
            
def rebuild_from_resumedata(metainterp, deadframe, faildescr):
    """ Reconstruct metainterp frames from the resumedata
    """
    return BoxResumeReader(metainterp, deadframe).rebuild(faildescr)

def blackhole_from_resumedata(interpbuilder, metainterp_sd, faildescr,
                              deadframe, all_virtuals=None):
    """ Reconstruct the blackhole interpreter from the resume data
    """
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

class ResumeRecorder(object):
    """ Created by metainterp to record the resume as we record operations
    """
    def __init__(self, metainterp, is_bridge=False):
        self.metainterp = metainterp
        self.cachestack = []
        if is_bridge:
            for frame in metainterp.framestack:
                self.cachestack.append([None] * frame.jitcode.num_regs())

    def enter_frame(self, pc, jitcode):
        self.metainterp.history.record(rop.ENTER_FRAME, [ConstInt(pc)], None,
                                       descr=jitcode)
        self.cachestack.append([None] * jitcode.num_regs())

    def leave_frame(self):
        self.metainterp.history.record(rop.LEAVE_FRAME, [], None)
        self.cachestack.pop()

    def resume_point(self, resumedescr, resumepc):
        framestack = self.metainterp.framestack
        for i, frame in enumerate(framestack):
            in_a_call = not i == len(framestack) - 1
            self._emit_resume_data(resumepc, frame, i, in_a_call)

    def process_box(self, index_in_frontend, frame_pos, box):
        cache = self.cachestack[frame_pos]
        self.marked[index_in_frontend] = box
        if cache[index_in_frontend] is box:
            return
        cache[index_in_frontend] = box
        self.metainterp.history.record(rop.RESUME_PUT,
                                       [box, ConstInt(frame_pos),
                                        ConstInt(index_in_frontend)], None)

    def _emit_resume_data(self, resume_pc, frame, frame_pos, in_a_call):
        self.marked = [None] * len(self.cachestack[frame_pos])
        if in_a_call:
            # If we are not the topmost frame, frame._result_argcode contains
            # the type of the result of the call instruction in the bytecode.
            # We use it to clear the box that will hold the result: this box
            # is not defined yet.
            argcode = frame._result_argcode
            index = ord(frame.bytecode[frame.pc - 1])
            if   argcode == 'i': frame.registers_i[index] = history.CONST_FALSE
            elif argcode == 'r': frame.registers_r[index] = history.CONST_NULL
            elif argcode == 'f': frame.registers_f[index] = history.CONST_FZERO
            frame._result_argcode = '?'     # done
        #
        if not in_a_call and resume_pc != -1:
            info = frame.get_current_position_info(resume_pc)
        else:
            info = frame.get_current_position_info()
        start_i = 0
        start_r = start_i + frame.jitcode.num_regs_i()
        start_f = start_r + frame.jitcode.num_regs_r()
        # fill it now
        for i in range(info.get_register_count_i()):
            index = info.get_register_index_i(i)
            self.process_box(index, frame_pos, frame.registers_i[index])
        for i in range(info.get_register_count_r()):
            index = info.get_register_index_r(i)
            self.process_box(index + start_r, frame_pos,
                             frame.registers_r[index])
        for i in range(info.get_register_count_f()):
            index = info.get_register_index_f(i)
            self.process_box(index + start_f, frame_pos,
                             frame.registers_f[index])

        mi_history = self.metainterp.history
        cache = self.cachestack[frame_pos]
        for i in range(len(self.marked)):
            if self.marked[i] is None and cache[i] is not None:
                cache[i] = None
                mi_history.record(rop.RESUME_CLEAR, [ConstInt(frame_pos),
                                                  ConstInt(i)], None)
        if resume_pc == -1:
            resume_pc = self.metainterp.framestack[-1].pc
        mi_history.record(rop.RESUME_SET_PC, [ConstInt(resume_pc)], None)
        self.marked = None
