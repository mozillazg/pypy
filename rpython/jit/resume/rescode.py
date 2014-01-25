
from rpython.jit.metainterp.history import ConstInt
from rpython.rlib.objectmodel import Symbolic

(UNUSED, ENTER_FRAME, LEAVE_FRAME, RESUME_PUT,
 RESUME_NEW, RESUME_NEW_WITH_VTABLE, RESUME_SETFIELD_GC,
 RESUME_SET_PC, RESUME_CLEAR) = range(9)

TAGCONST = 0x0
TAGVIRTUAL = 0x2
TAGBOX = 0x3
TAGSMALLINT = 0x1

TAGOFFSET = 2

CLEAR_POSITION = 0xffff

class ResumeBytecode(object):
    def __init__(self, opcodes, consts, loop=None):
        self.opcodes = opcodes
        self.consts = consts
        self.loop = loop

    def dump(self, staticdata, resume_pos):
        from rpython.jit.resume.reader import Dumper

        d = Dumper(staticdata)
        d.interpret_until(self, resume_pos)
        return d.finish()

class ResumeBytecodeBuilder(object):
    def __init__(self):
        self.l = []
        self.consts = []

    def getpos(self):
        return len(self.l)

    def build(self):
        return "".join(self.l)

    def write(self, i):
        assert 0 <= i < 256
        self.l.append(chr(i))

    def write_short(self, i):
        assert 0 <= i < 0x1000
        self.write(i & 0xff)
        self.write(i >> 8)

    def enter_frame(self, pc, jitcode):
        self.write(ENTER_FRAME)
        self.write_short(pc + 1) # can be -1 !
        self.write_short(jitcode.global_index)

    def leave_frame(self):
        self.write(LEAVE_FRAME)

    def encode(self, tag, loc):
        return tag | (loc << 2)

    def encode_const(self, const):
        if (isinstance(const, ConstInt) and
            not isinstance(const.getint(), Symbolic) and
            0 <= const.getint() < 0x4000):
            return TAGSMALLINT | (const.getint() << 2)
        self.consts.append(const)
        return TAGCONST | ((len(self.consts) - 1) << 2)

    def resume_set_pc(self, pc):
        self.write(RESUME_SET_PC)
        self.write_short(pc)

    def resume_put(self, pos, frame_pos, pos_in_frame):
        self.write(RESUME_PUT)
        self.write_short(pos)
        self.write(frame_pos)
        self.write(pos_in_frame)

    def resume_new(self, v_pos, descr):
        self.write(RESUME_NEW)
        self.write_short(self.encode(TAGVIRTUAL, v_pos))
        self.write_short(descr.global_descr_index)

    def resume_new_with_vtable(self, v_pos, const_class):
        self.write(RESUME_NEW_WITH_VTABLE)
        self.write_short(self.encode(TAGVIRTUAL, v_pos))
        self.write_short(self.encode_const(const_class))

    def resume_setfield_gc(self, structpos, fieldpos, descr):
        self.write(RESUME_SETFIELD_GC)
        self.write_short(structpos)
        self.write_short(fieldpos)
        self.write_short(descr.global_descr_index)

    def resume_clear(self, frame_pos, pos_in_frame):
        self.write(RESUME_CLEAR)
        self.write(frame_pos)
        self.write(pos_in_frame)
        
