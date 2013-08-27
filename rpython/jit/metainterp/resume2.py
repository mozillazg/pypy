
""" The new resume that records bytecode. The idea is that bytecode is
incremental and minimal for the case the guard is never incoked. However,
if the guard fails it can be compressed into a starting point.

opcodes:

CAPTURE_POINT <pc> [list-of-alive-boxes]
ENTER_FRAME <func no> <pc> [list-of-alive-boxes]
LEAVE_FRAME

"""

from rpython.rlib import rstack

ENTER_FRAME = chr(0)
LEAVE_FRAME = chr(1)
CAPTURE_POINT = chr(2)

BC_NAMES = ['ENTER_FRAME', 'LEAVE_FRAME', 'CAPTURE_POINT']

MODEL_FRONTEND = 0
MODEL_FAILARGS = 1
MODEL_BACKEND = 2

class Bytecode(object):
    """ an object representing a single bytecode. We keep it on faildescrs,
    however it would be more efficient to keep it on a loop token.

    XXX fix that

    model can be one of the above, it means the numbers in numberings
    are relative to:

    frontend - means the index is an index into list of allboxes
    failargs - means it's index in the list of failargs
    backend - a backend specific number

    """
    def __init__(self, bc_repr, model):
        self.bc_repr = bc_repr
        self.model = model

class ResumeBytecodeBuilder(object):
    def __init__(self, metainterp_sd, model=MODEL_FRONTEND):
        self.bc = []
        self.boxes = {}
        self.metainterp_sd = metainterp_sd
        self.model = model

    def enumerate_box(self, box):
        if box in self.boxes:
            return self.boxes[box]
        else:
            no = len(self.boxes)
            self.boxes[box] = no
            return no

    def write(self, c):
        self.bc.append(c)

    def write_short(self, s):
        assert 0 <= s <= (2**16 - 1)
        self.write(chr(s >> 8))
        self.write(chr(s & 0xff))

    def write_list(self, l):
        self.write_short(len(l))
        for item in l:
            self.write_short(item)

    def enter_function(self, jitcode, pc, boxlist):
        self.write(ENTER_FRAME)
        self.write_short(jitcode.number)
        self.write_short(pc)
        self.write_list([self.enumerate_box(box) for box in boxlist])

    def leave_function(self):
        self.write(LEAVE_FRAME)

    def start_from_descr(self, descr):
        xxx

    def capture_resumedata(self, descr, resumepc, boxlist):
        self.write(CAPTURE_POINT)
        self.write_short(resumepc)
        self.write_list([self.enumerate_box(box) for box in boxlist])
        descr.rd_bytecode_position = len(self.bc)

    def finish(self, metainterp, start):
        from rpython.jit.metainterp.history import AbstractFailDescr

        assert start == 0
        finished_bc = ''.join(self.bc)
        for op in metainterp.history.operations:
            if op.is_guard():
                descr = op.getdescr()
                assert isinstance(descr, AbstractFailDescr)
                descr.rd_bytecode = Bytecode(finished_bc, self.model)
        #print_bc(finished_bc, self.metainterp_sd.alljitcodes)

class AbstractBytecodeInterpreter(object):
    def __init__(self, bc, alljitcodes):
        self.bc = bc.bc_repr
        self.alljitcodes = alljitcodes
        self.init()

    def init(self):
        pass

    def read_short(self):
        res = (ord(self.bc[self.pos]) << 8) + ord(self.bc[self.pos + 1])
        self.pos += 2
        return res

    def read_list(self):
        length = self.read_short()
        l = []
        for i in range(length):
            l.append(self.read_short())
        return l

    def interpret(self):
        self.pos = 0
        self.interpret_until(len(self.bc))

    def interpret_until(self, stop):
        self.stop = stop
        while self.pos < stop:
            opcode = self.bc[self.pos]
            self.pos += 1
            if opcode == ENTER_FRAME:
                jitcode = self.alljitcodes[self.read_short()]
                pc = self.read_short()
                boxlist = self.read_list()
                self.ENTER_FRAME(jitcode, pc, boxlist)
            elif opcode == LEAVE_FRAME:
                self.LEAVE_FRAME()
            elif opcode == CAPTURE_POINT:
                pc = self.read_short()
                boxlist = self.read_list()
                self.CAPTURE_POINT(pc, boxlist)

class BytecodePrinter(AbstractBytecodeInterpreter):
    def ENTER_FRAME(self, jitcode, pc, boxnos):
        print "ENTER_FRAME %s %d %s" % (jitcode.name, pc, boxnos)

    def CAPTURE_POINT(self, pc, boxlist):
        print "CAPTURE_POINT %d %s" % (pc, boxlist)

    def LEAVE_FRAME(self):
        print "LEAVE_FRAME"

class DirectResumeBuilder(AbstractBytecodeInterpreter):
    def init(self):
        self.pos = 0
        self.framestack = []

    def ENTER_FRAME(self, jitcode, pc, boxlist):
        self.framestack.append((jitcode, pc, boxlist))

    def CAPTURE_POINT(self, pc, boxlist):
        if self.pos == self.stop:
            self.framestack.append((None, pc, boxlist))

    def LEAVE_FRAME(self):
        self.framestack.pop()

class OptimizerResumeInterpreter(AbstractBytecodeInterpreter):
    """ This resume interpreter reads the resume and writes the new one
    in resume_bc_writer
    """

    def __init__(self, bc, jitcode, resume_bc_writer):
        AbstractBytecodeInterpreter.__init__(self, bc, jitcode)
        self.resume_bc_writer = resume_bc_writer

    def init(self):
        self.pos = 0
        self.framestack = []
        self.cur_len = 0
        self.cur_boxlist = None

    def get_current_boxes(self, allboxes):
        xxx
        newboxes = [None] * (self.cur_len + len(self.cur_boxlist))
        i = 0
        j = 0
        while i < len(self.framestack):
            boxlist = self.framestack[i]
            newboxes[j:j + len(boxlist)] = boxlist
            i += 1
            j += len(boxlist)
        newboxes[j:] = self.cur_boxlist
        return [allboxes[i] for i in newboxes]

    def ENTER_FRAME(self, jitcode, pc, boxlist):
        self.framestack.append(boxlist)
        self.cur_len += len(boxlist)

    def CAPTURE_POINT(self, pc, boxlist):
        self.cur_boxlist = boxlist

    def LEAVE_FRAME(self):
        el = self.framestack.pop()
        self.cur_len -= len(el)

def print_bc(bc, jitcodes):
    BytecodePrinter(bc, jitcodes).interpret()

class InfoFiller(object):
    def __init__(self, cpu, deadframe, bhinterp, boxlist):
        self.cpu = cpu
        self.boxlist = boxlist
        self.deadframe = deadframe
        self.bhinterp = bhinterp

    def callback_i(self, index, register_index):
        backend_index = self.boxlist[index]
        intval = self.cpu.get_int_value(self.deadframe, backend_index)
        self.bhinterp.setarg_i(register_index, intval)

    def callback_r(self, index, register_index):
        xxx

    def callback_f(self, index, register_index):
        xxx

def blackhole_from_resumedata(metainterp_sd, jitdriver_sd, descr,
                              deadframe, all_virtuals=None):
    # The initialization is stack-critical code: it must not be interrupted by
    # StackOverflow, otherwise the jit_virtual_refs are left in a dangling state.
    assert all_virtuals is None
    blackholeinterpbuilder = metainterp_sd.blackholeinterpbuilder
    alljitcodes = metainterp_sd.alljitcodes
    rstack._stack_criticalcode_start()
    try:
        pos = descr.rd_bytecode_position
        rb = DirectResumeBuilder(descr.rd_bytecode, alljitcodes)
        rb.interpret_until(pos)
        framestack = rb.framestack
    finally:
        rstack._stack_criticalcode_stop()

    #
    # First get a chain of blackhole interpreters whose length is given
    # by the size of framestack.  The first one we get must be
    # the bottom one, i.e. the last one in the chain, in order to make
    # the comment in BlackholeInterpreter.setposition() valid.
    nextbh = None
    for i in range(len(framestack)):
        curbh = blackholeinterpbuilder.acquire_interp()
        curbh.nextblackholeinterp = nextbh
        nextbh = curbh
    firstbh = nextbh
    #
    # Now fill the blackhole interpreters with resume data.
    curbh = firstbh
    for i in range(len(framestack) - 1, 0, -1):
        jitcode = framestack[i - 1][0]
        pc = framestack[i - 1][1]
        boxlist = framestack[i][2]
        curbh.setposition(jitcode, pc)
        info = curbh.get_current_position_info()
        filler = InfoFiller(metainterp_sd.cpu, deadframe, curbh, boxlist)
        info.enumerate_vars(filler.callback_i, filler.callback_r,
                            filler.callback_f, None)
        curbh = curbh.nextblackholeinterp
    return firstbh
