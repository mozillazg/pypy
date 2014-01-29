
from rpython.jit.metainterp.resoperation import rop
from rpython.jit.metainterp.history import BoxInt, BoxPtr, BoxFloat, ConstInt,\
     INT, REF, FLOAT
from rpython.jit.metainterp import history
from rpython.jit.resume.reader import AbstractResumeReader
from rpython.jit.resume.rescode import TAGBOX, TAGCONST, TAGSMALLINT,\
     TAGVIRTUAL, CLEAR_POSITION


class DirectResumeReader(AbstractResumeReader):
    """ Directly read values from the jitframe and put them in the blackhole
    interpreter
    """

    def __init__(self, metainterp_sd, binterpbuilder, cpu, deadframe):
        self.bhinterpbuilder = binterpbuilder
        self.cpu = cpu
        self.deadframe = deadframe
        self.virtuals_cache = {}
        AbstractResumeReader.__init__(self, metainterp_sd)

    def finish(self):
        nextbh = None
        curbh = None
        for i, frame in enumerate(self.framestack):
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

    def store_int_value(self, curbh, i, encoded_pos):
        if encoded_pos == CLEAR_POSITION:
            return
        val = self.getint(encoded_pos)
        curbh.registers_i[i] = val

    def getint(self, encoded_pos):
        tag, index = self.decode(encoded_pos)
        if tag == TAGBOX:
            return self.cpu.get_int_value(self.deadframe, index)
        elif tag == TAGSMALLINT:
            return index
        else:
            xxx

    def store_ref_value(self, curbh, i, encoded_pos):
        if encoded_pos == CLEAR_POSITION:
            return
        curbh.registers_r[i] = self.getref(encoded_pos)

    def getref(self, encoded_pos):
        tag, index = self.decode(encoded_pos)
        if tag == TAGBOX:
            return self.cpu.get_ref_value(self.deadframe, index)
        elif tag == TAGCONST:
            return self.consts[index].getref_base()
        elif tag == TAGVIRTUAL:
            return self.allocate_virtual(index)
        else:
            xxx

    def allocate_virtual(self, index):
        try:
            return self.virtuals_cache[index]
        except KeyError:
            pass
        val = self.virtuals[index].allocate_direct(self, self.cpu)
        self.virtuals_cache[index] = val
        self.virtuals[index].populate_fields(val, self)
        return val

    def strsetitem(self, str, index, char, mode):
        if mode == 's':
            self.cpu.bh_strsetitem(str, index, char)
        else:
            self.cpu.bh_unicodesetitem(str, index, char)

    def setfield_gc(self, struct, encoded_field_pos, fielddescr):
        if fielddescr.is_field_signed():
            intval = self.getint(encoded_field_pos)
            self.cpu.bh_setfield_gc_i(struct, intval, fielddescr)
        elif fielddescr.is_pointer_field():
            refval = self.getref(encoded_field_pos)
            self.cpu.bh_setfield_gc_r(struct, refval, fielddescr)
        elif fielddescr.is_float_field():
            xxx

    def store_float_value(self, curbh, i, jitframe_pos):
        xxx
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
        AbstractResumeReader.__init__(self, metainterp.staticdata)

    def get_box_value(self, frame_pos, pos_in_frame, encoded_pos, TP):
        if encoded_pos == CLEAR_POSITION:
            return None
        if encoded_pos in self.cache:
            return self.cache[encoded_pos]
        tag, pos = self.decode(encoded_pos)
        if tag == TAGBOX:
            if TP == INT:
                val = self.metainterp.cpu.get_int_value(self.deadframe, pos)
                box = BoxInt(val)
            elif TP == REF:
                val = self.metainterp.cpu.get_ref_value(self.deadframe, pos)
                box = BoxPtr(val)
            else:
                xxx
            if pos_in_frame != -1:
                self.metainterp.history.record(rop.RESUME_PUT,
                                               [box, ConstInt(frame_pos),
                                                ConstInt(pos_in_frame)],
                                                None, None)
            self.result.append(box)
            self.locs.append(pos)
            self.cache[encoded_pos] = box
            return box
        elif tag == TAGSMALLINT:
            return ConstInt(pos)
        elif tag == TAGCONST:
            return self.consts[pos]
        else:
            assert tag == TAGVIRTUAL
            virtual = self.virtuals[pos]
            virtual_box = virtual.allocate_box(self.metainterp)
            self.cache[encoded_pos] = virtual_box
            virtual.populate_fields_boxes(virtual_box, self)
            if pos_in_frame != -1:
                self.metainterp.history.record(rop.RESUME_PUT,
                                               [virtual_box,
                                                ConstInt(frame_pos),
                                                ConstInt(pos_in_frame)],
                                                None, None)
            return virtual_box

    def getkind(self, fielddescr):
        if fielddescr.is_pointer_field():
            return REF
        elif fielddescr.is_float_field():
            return FLOAT
        else:
            assert fielddescr.is_field_signed()
            return INT
        
    def setfield_gc(self, box, encoded_field_pos, fielddescr):
        field_box = self.get_box_value(-1, -1, encoded_field_pos,
                                       self.getkind(fielddescr))
        self.metainterp.execute_and_record(rop.SETFIELD_GC, fielddescr,
                                           box, field_box)

    def strsetitem(self, box, ibox, vbox, mode):
        if mode == 's':
            resop = rop.STRSETITEM
        else:
            resop = rop.UNICODESETITEM
        self.metainterp.execute_and_record(resop, None, box, ibox, vbox)

    def store_int_box(self, frame_pos, pos, miframe, i, jitframe_pos):
        box = self.get_box_value(frame_pos, pos, jitframe_pos, INT)
        if box is None:
            return
        miframe.registers_i[i] = box

    def store_ref_box(self, frame_pos, pos, miframe, i, jitframe_pos):
        box = self.get_box_value(frame_pos, pos, jitframe_pos, REF)
        if box is None:
            return
        miframe.registers_r[i] = box

    def store_float_box(self, frame_pos, pos, miframe, i, jitframe_pos):
        xxx
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

    def get_loc(self, p):
        tag, pos = self.decode(p)
        if tag == TAGBOX:
            return pos
        return -1

    def finish(self):
        self.result = []
        self.cache = {}
        self.locs = []
        for frame_pos, frame in enumerate(self.framestack):
            jitcode = frame.jitcode
            miframe = self.metainterp.newframe(jitcode)
            miframe.pc = frame.pc
            pos = 0
            for i in range(jitcode.num_regs_i()):
                self.store_int_box(frame_pos, pos, miframe, i,
                                   frame.registers[pos])
                pos += 1
            for i in range(jitcode.num_regs_r()):
                self.store_ref_box(frame_pos, pos, miframe, i,
                                   frame.registers[pos])
                pos += 1
            for i in range(jitcode.num_regs_f()):
                self.store_float_box(frame_pos, pos, miframe, i,
                                     frame.registers[pos])
                pos += 1
        self.cache = None
        state = self.result, self.locs
        self.result = None
        self.locs = None
        return state

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
    last_bhinterp = DirectResumeReader(metainterp_sd, interpbuilder, cpu,
                                       deadframe).rebuild(faildescr)

    return last_bhinterp

class ResumeRecorder(object):
    """ Created by metainterp to record the resume as we record operations
    """
    def __init__(self, metainterp):
        self.metainterp = metainterp
        self.cachestack = []

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
