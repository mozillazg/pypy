
from rpython.jit.metainterp.resoperation import rop
from rpython.jit.metainterp.history import Box, Const, AbstractDescr
from rpython.jit.resume.rescode import ResumeBytecodeBuilder, TAGBOX,\
     ResumeBytecode, TAGVIRTUAL
from rpython.jit.codewriter.jitcode import JitCode

class DescrForStr(AbstractDescr):
    pass

left_descr = DescrForStr()
right_descr = DescrForStr()

class BaseDeps(object):
    pass

class DepsFields(BaseDeps):
    def __init__(self):
        self.fields = {}

    def foreach(self, callback, arg):
        for v in self.fields.itervalues():
            callback(arg, v)

class DepsConcat(BaseDeps):
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def foreach(self, callback, arg):
        callback(arg, self.left)
        callback(arg, self.right)

class DepsArray(BaseDeps):
    def __init__(self, size):
        self.l = [None] * size

    def foreach(self, callback, arg):
        for item in self.l:
            if item is not None:
                callback(arg, item)

class LivenessAnalyzer(object):
    def __init__(self):
        self.liveness = {}
        self.frame_starts = [0]
        self.framestack = []
        self.deps = {}

    def enter_frame(self, pc, jitcode):
        self.frame_starts.append(self.frame_starts[-1] + jitcode.num_regs())
        self.framestack.append([None] * jitcode.num_regs())

    def resume_put(self, box, framepos, frontend_pos):
        if isinstance(box, Const):
            return
        self.framestack[framepos][frontend_pos] = box

    def resume_clear(self, framepos, frontend_pos):
        self.framestack[framepos][frontend_pos] = None

    def resume_new(self, result, descr):
        self.deps[result] = DepsFields()

    def resume_newstr(self, result, length):
        self.deps[result] = DepsArray(length)

    def resume_concatstr(self, result, left, right):
        self.deps[result] = DepsConcat(left, right)

    def resume_new_with_vtable(self, result, klass):
        self.deps[result] = DepsFields()

    def resume_setfield_gc(self, arg0, arg1, descr):
        self.deps[arg0].fields[descr] = arg1

    def resume_strsetitem(self, arg0, index, arg1):
        self.deps[arg0].l[index] = arg1

    def resume_set_pc(self, pc):
        pass

    def interpret_until(self, ops, until, pos=0):
        while pos < until:
            op = ops[pos]
            if not op.is_resume():
                pos += 1
                continue
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
            elif op.getopnum() == rop.RESUME_NEW_WITH_VTABLE:
                self.resume_new_with_vtable(op.result, op.getarg(0))
            elif op.getopnum() == rop.RESUME_SETFIELD_GC:
                self.resume_setfield_gc(op.getarg(0), op.getarg(1),
                                        op.getdescr())
            elif op.getopnum() == rop.RESUME_SET_PC:
                self.resume_set_pc(op.getarg(0).getint())
            elif op.getopnum() == rop.RESUME_CLEAR:
                self.resume_clear(op.getarg(0).getint(),
                                  op.getarg(1).getint())
            elif op.getopnum() == rop.RESUME_NEWSTR:
                self.resume_newstr(op.result, op.getarg(0).getint())
            elif op.getopnum() == rop.RESUME_NEWUNICODE:
                self.resume_newstr(op.result, op.getarg(0).getint())
            elif op.getopnum() == rop.RESUME_CONCATSTR:
                self.resume_concatstr(op.result, op.getarg(0), op.getarg(1))
            elif op.getopnum() == rop.RESUME_CONCATUNICODE:
                self.resume_concatstr(op.result, op.getarg(0), op.getarg(1))
            elif op.getopnum() == rop.RESUME_STRSETITEM:
                self.resume_strsetitem(op.getarg(0), op.getarg(1).getint(),
                                       op.getarg(2))
            elif not op.is_resume():
                pos += 1
                continue
            else:
                raise Exception("strange operation")
            pos += 1

    def _track(self, allboxes, box):
        if box in self.deps:
            self.deps[box].foreach(self._track, allboxes)
        if not isinstance(box, Const) and box is not None:
            allboxes.append(box)

    def all_boxes_from(self, frame):
        allboxes = []
        for item in frame:
            self._track(allboxes, item)
        return allboxes

    def get_live_info(self):
        return self.framestack

    def leave_frame(self):
        self.framestack.pop()

    def rebuild(self, faildescr):
        raise Exception("should not be called")

class ResumeBuilder(object):
    def __init__(self, regalloc, frontend_liveness, descr):
        self.regalloc = regalloc
        self.current_attachment = {}
        self.frontend_liveness = frontend_liveness
        self.frontend_pos = {}
        self.virtuals = {}
        self.builder = ResumeBytecodeBuilder()

    def get_box_pos(self, box):
        if box in self.virtuals:
            return TAGVIRTUAL | (self.virtuals[box] << 2)
        if isinstance(box, Const):
            return self.builder.encode_const(box)
        try:
            loc = self.regalloc.loc(box, must_exist=True).get_jitframe_position()
            pos = self.builder.encode(TAGBOX, loc)
            self.current_attachment[box] = pos
            return pos
        except KeyError:
            raise

    def process(self, op):
        if op.getopnum() == rop.ENTER_FRAME:
            self.builder.enter_frame(op.getarg(0).getint(), op.getdescr())
        elif op.getopnum() == rop.RESUME_PUT:
            frame_pos = op.getarg(1).getint()
            pos_in_frame = op.getarg(2).getint()
            try:
                pos = self.get_box_pos(op.getarg(0))
            except KeyError:
                pos = TAGBOX
                self.current_attachment[op.getarg(0)] = -1
            else:
                self.builder.resume_put(pos, frame_pos, pos_in_frame)
            if pos & TAGBOX:
                self.frontend_pos[op.getarg(0)] = (frame_pos, pos_in_frame)
        elif op.getopnum() == rop.LEAVE_FRAME:
            self.builder.leave_frame()
        elif op.getopnum() == rop.RESUME_NEW:
            v_pos = len(self.virtuals)
            self.virtuals[op.result] = v_pos
            self.builder.resume_new(v_pos, op.getdescr())
        elif op.getopnum() == rop.RESUME_NEW_WITH_VTABLE:
            v_pos = len(self.virtuals)
            self.virtuals[op.result] = v_pos
            self.builder.resume_new_with_vtable(v_pos, op.getarg(0))
        elif op.getopnum() == rop.RESUME_SETFIELD_GC:
            structpos = self.get_box_pos(op.getarg(0))
            fieldpos = self.get_box_pos(op.getarg(1))
            descr = op.getdescr()
            self.builder.resume_setfield_gc(structpos, fieldpos, descr)
        elif op.getopnum() == rop.RESUME_SET_PC:
            self.builder.resume_set_pc(op.getarg(0).getint())
        elif op.getopnum() == rop.RESUME_CLEAR:
            self.builder.resume_clear(op.getarg(0).getint(),
                                      op.getarg(1).getint())
        elif op.getopnum() == rop.RESUME_NEWSTR:
            v_pos = len(self.virtuals)
            self.virtuals[op.result] = v_pos
            self.builder.resume_newstr(v_pos, op.getarg(0).getint())
        elif op.getopnum() == rop.RESUME_NEWUNICODE:
            v_pos = len(self.virtuals)
            self.virtuals[op.result] = v_pos
            self.builder.resume_newunicode(v_pos, op.getarg(0).getint())
        elif op.getopnum() == rop.RESUME_CONCATSTR:
            v_pos = len(self.virtuals)
            self.virtuals[op.result] = v_pos
            leftpos = self.get_box_pos(op.getarg(0))
            rightpos = self.get_box_pos(op.getarg(1))
            self.builder.resume_concatstr(v_pos, leftpos, rightpos)
        elif op.getopnum() == rop.RESUME_CONCATUNICODE:
            v_pos = len(self.virtuals)
            self.virtuals[op.result] = v_pos
            leftpos = self.get_box_pos(op.getarg(0))
            rightpos = self.get_box_pos(op.getarg(1))
            self.builder.resume_concatunicode(v_pos, leftpos, rightpos)
        elif op.getopnum() == rop.RESUME_STRSETITEM:
            v_pos = self.virtuals[op.getarg(0)]
            index = op.getarg(1).getint()
            valpos = self.get_box_pos(op.getarg(2))
            self.builder.resume_strsetitem(v_pos, index, valpos)
        else:
            raise Exception("strange operation")

    def _mark_visited(self, v, loc):
        pos = loc.get_jitframe_position()
        if (v not in self.frontend_liveness or
            self.frontend_liveness[v] < self.regalloc.rm.position):
            return
        if v not in self.current_attachment:
            return
        pos = self.builder.encode(TAGBOX, pos)
        if self.current_attachment[v] != pos:
            frame_index, pos_in_frame = self.frontend_pos[v]
            self.builder.resume_put(pos, frame_index, pos_in_frame)
        self.current_attachment[v] = pos

    def mark_resumable_position(self):
        visited = {}
        for v, loc in self.regalloc.fm.bindings.iteritems():
            self._mark_visited(v, loc)
            visited[v] = None
        for v, loc in self.regalloc.rm.reg_bindings.iteritems():
            if v not in visited:
                self._mark_visited(v, loc)
        for v, loc in self.regalloc.xrm.reg_bindings.iteritems():
            if v not in visited:
                self._mark_visited(v, loc)
        return self.builder.getpos()

    def finish(self, clt):
        return ResumeBytecode(self.builder.build(), self.builder.consts, clt)


def compute_vars_longevity(inputargs, operations, descr=None):
    # compute a dictionary that maps variables to index in
    # operations that is a "last-time-seen"

    # returns a pair longevity/useful. Non-useful variables are ones that
    # never appear in the assembler or it does not matter if they appear on
    # stack or in registers. Main example is loop arguments that go
    # only to guard operations or to jump or to finish
    produced = {}
    last_used = {}
    last_real_usage = {}
    frontend_alive = {}
    liveness_analyzer = LivenessAnalyzer()
    start_pos = 0
    for position, op in enumerate(operations):
        if op.is_guard():
            liveness_analyzer.interpret_until(operations, position, start_pos)
            start_pos = position
            framestack = liveness_analyzer.get_live_info()
            for frame in framestack:
                for item in liveness_analyzer.all_boxes_from(frame):
                    last_used[item] = position
                    frontend_alive[item] = position

    for i in range(len(operations)-1, -1, -1):
        op = operations[i]
        if op.result:
            if op.result not in last_used and op.has_no_side_effect():
                continue
            assert op.result not in produced
            produced[op.result] = i
        opnum = op.getopnum()
        for j in range(op.numargs()):
            arg = op.getarg(j)
            if not isinstance(arg, Box):
                continue
            if arg not in last_used:
                last_used[arg] = i
            else:
                last_used[arg] = max(last_used[arg], i)
            if opnum != rop.JUMP and opnum != rop.LABEL:
                if arg not in last_real_usage:
                    last_real_usage[arg] = i
    #
    longevity = {}
    for arg in produced:
        if arg in last_used:
            assert isinstance(arg, Box)
            assert produced[arg] < last_used[arg]
            longevity[arg] = (produced[arg], last_used[arg])
            del last_used[arg]
    for arg in inputargs:
        assert isinstance(arg, Box)
        if arg not in last_used:
            longevity[arg] = (-1, -1)
        else:
            longevity[arg] = (0, last_used[arg])
            del last_used[arg]
    assert len(last_used) == 0
    return longevity, last_real_usage, frontend_alive
