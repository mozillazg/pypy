
import sys
from rpython.jit.metainterp.history import ConstInt
from rpython.jit.resume import rescode

class ResumeFrame(object):
    def __init__(self, jitcode):
        self.registers = [-1] * jitcode.num_regs()
        self.jitcode = jitcode
        self.pc = -1


class Virtual(object):
    def __init__(self, pos, descr):
        self.pos = pos
        self.fields = {}
        self.descr = descr


class AbstractResumeReader(object):
    """ A resume reader that can follow resume until given point. Consult
    the concrete classes for details
    """
    
    def __init__(self, staticdata):
        self.framestack = []
        self.staticdata = staticdata
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
        return rescode.TAGBOX | (pos << rescode.TAGOFFSET)

    def encode_virtual(self, box):
        return rescode.TAGVIRTUAL | (self.virtuals[box].pos << rescode.TAGOFFSET)

    def encode_const(self, const):
        XXX
        if isinstance(const, ConstInt) and const.getint() < (sys.maxint >> 3):
            return rescode.TAGSMALLINT | (const.getint() << rescode.TAGOFFSET)
        self.consts.append(const)
        return rescode.TAGCONST | ((len(self.consts) - 1) << TAGOFFSET)

    def decode(self, pos):
        return pos & 0x3, pos >> rescode.TAGOFFSET

    def resume_put(self, encoded_pos, frame_no, frontend_position):
        self.framestack[frame_no].registers[frontend_position] = encoded_pos

    def encode(self, box):
        xxx

    def resume_new(self, box, descr):
        xxx
        # XXX make it a list
        v = Virtual(len(self.virtual_list), descr)
        self.virtuals[box] = v
        self.virtual_list.append(v)

    def resume_setfield_gc(self, box, fieldbox, descr):
        # XXX optimize fields
        xxx
        self.virtuals[box].fields[descr] = self.encode(fieldbox)

    def resume_clear(self, frame_no, frontend_position):
        xxx
        self.framestack[frame_no].registers[frontend_position] = -1

    def resume_set_pc(self, pc):
        self.framestack[-1].pc = pc

    def leave_frame(self):
        self.framestack.pop()

    def _rebuild_until(self, rb, position):
        self.consts = rb.consts
        if rb.parent is not None:
            self._rebuild_until(rb.parent, rb.parent_position)
        self.interpret_until(rb, position)

    def read(self, pos):
        return ord(self.bytecode.opcodes[pos])

    def read_short(self, pos):
        return self.read(pos) + (self.read(pos + 1) << 8)

    def interpret_until(self, bytecode, until, pos=0):
        self.bytecode = bytecode
        while pos < until:
            op = ord(bytecode.opcodes[pos])
            if op == rescode.UNUSED:
                raise Exception("malformed bytecode")
            elif op == rescode.ENTER_FRAME:
                pc = self.read_short(pos + 1) - 1
                jitcode = self.staticdata.alljitcodes[self.read_short(pos + 3)]
                self.enter_frame(pc, jitcode)
                pos += 5
            elif op == rescode.RESUME_PUT:
                encoded = self.read_short(pos + 1)
                frame_pos = self.read(pos + 3)
                pos_in_frame = self.read(pos + 4)
                self.resume_put(encoded, frame_pos, pos_in_frame)
                pos += 5
            elif op == rescode.RESUME_NEW:
                tag, v_pos = self.decode(self.read_short(pos + 1))
                assert tag == rescode.TAGVIRTUAL
                descr = self.staticdata.opcode_descrs[self.read_short(pos + 3)]
                self.resume_new(v_pos, descr)
                pos += 5
            elif op == rescode.RESUME_SETFIELD_GC:
                structpos = self.read_short(pos + 1)
                fieldpos = self.read_short(pos + 3)
                descr = self.staticdata.opcode_descrs[self.read_short(pos + 5)]
                self.resume_setfield_gc(structpos, fieldpos, descr)
                pos += 7
            else:
                xxx
        self.bytecode = None

    def read_int(self, jitframe_pos):
        return self.metainterp.cpu.get_int_value(self.deadframe, jitframe_pos)

class Dumper(AbstractResumeReader):
    def __init__(self, staticdata):
        AbstractResumeReader.__init__(self, staticdata)
        self.l = []

    def enter_frame(self, pc, jitcode):
        self.l.append("enter_frame %d %s" % (pc, jitcode.name))

    def resume_put(self, encoded, frame_pos, pos_in_frame):
        tag, index = self.decode(encoded)
        self.l.append("resume_put (%d, %d) %d %d" % (tag, index, frame_pos,
                                                     pos_in_frame))

    def resume_new(self, v_pos, descr):
        self.l.append("%d = resume_new %d" % (v_pos, descr.global_descr_index))

    def resume_setfield_gc(self, structpos, fieldpos, descr):
        stag, sindex = self.decode(structpos)
        ftag, findex = self.decode(fieldpos)
        self.l.append("resume_setfield_gc (%d, %d) (%d, %d) %d" % (
            stag, sindex, ftag, findex, descr.global_descr_index))

    def finish(self):
        return "\n".join(self.l)
