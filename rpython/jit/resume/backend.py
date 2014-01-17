
from rpython.jit.metainterp.resoperation import rop, ResOperation
from rpython.jit.metainterp.history import ConstInt, Box, Const
from rpython.jit.resume.rescode import ResumeBytecodeBuilder, TAGBOX,\
     ResumeBytecode

            # if op.getopnum() == rop.ENTER_FRAME:
            #     descr = op.getdescr()
            #     assert isinstance(descr, JitCode)
            #     self.enter_frame(op.getarg(0).getint(), descr)
            # elif op.getopnum() == rop.LEAVE_FRAME:
            #     self.leave_frame()
            # elif op.getopnum() == rop.RESUME_PUT:
            #     self.resume_put(op.getarg(0), op.getarg(1).getint(),
            #                      op.getarg(2).getint())
            # elif op.getopnum() == rop.RESUME_NEW:
            #     self.resume_new(op.result, op.getdescr())
            # elif op.getopnum() == rop.RESUME_SETFIELD_GC:
            #     self.resume_setfield_gc(op.getarg(0), op.getarg(1),
            #                             op.getdescr())
            # elif op.getopnum() == rop.RESUME_SET_PC:
            #     self.resume_set_pc(op.getarg(0).getint())
            # elif op.getopnum() == rop.RESUME_CLEAR:
            #     self.resume_clear(op.getarg(0).getint(),
            #                       op.getarg(1).getint())
            # elif not op.is_resume():
            #     pos += 1
            #     continue
            # else:
            #     xxx

class LivenessAnalyzer(object):
    def __init__(self, inputframes=None):
        self.liveness = {}
        self.frame_starts = [0]
        self.framestack = []
        self.deps = {}
        if inputframes is not None:
            for frame in inputframes:
                self.frame_starts.append(self.frame_starts[-1] + len(frame))
                self.framestack.append(frame[:])

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
        self.deps[result] = {}

    def resume_setfield_gc(self, arg0, arg1, descr):
        self.deps[arg0][descr] = arg1

    def resume_set_pc(self, pc):
        pass

    def interpret_until(self, *args):
        pass

    def _track(self, allboxes, box):
        if box in self.deps:
            for dep in self.deps[box].values():
                self._track(allboxes, dep)
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
    def __init__(self, regalloc, frontend_liveness, descr, inputframes=None,
                 inputlocs=None):
        self.regalloc = regalloc
        self.current_attachment = {}
        self.frontend_liveness = frontend_liveness
        self.frontend_pos = {}
        self.virtuals = {}
        self.builder = ResumeBytecodeBuilder()
        if inputlocs is not None:
            i = 0
            all = {}
            for frame_pos, frame in enumerate(inputframes):
                for pos_in_frame, box in enumerate(frame):
                    if box is None or isinstance(box, Const) or box in all:
                        loc_pos = -1
                    else:
                        loc_pos = inputlocs[i].get_jitframe_position()
                        i += 1
                        self.frontend_pos[box] = (ConstInt(frame_pos),
                                                  ConstInt(pos_in_frame))
                        all[box] = None
                    if box not in self.current_attachment:
                        self.current_attachment[box] = loc_pos

    def process(self, op):
        if op.getopnum() == rop.ENTER_FRAME:
            self.builder.enter_frame(op.getarg(0).getint(), op.getdescr())
        elif op.getopnum() == rop.RESUME_PUT:
            frame_pos = op.getarg(1).getint()
            pos_in_frame = op.getarg(2).getint()
            box = op.getarg(0)
            if isinstance(box, Const):
                pos = self.builder.encode_const(box)
                self.builder.resume_put(pos, frame_pos, pos_in_frame)                
                return
            try:
                loc = self.regalloc.loc(box, must_exist=True).get_jitframe_position()
                pos = self.builder.encode(TAGBOX, loc)
                self.builder.resume_put(pos, frame_pos, pos_in_frame) 
            except KeyError:
                xxx
            self.current_attachment[box] = pos
            self.frontend_pos[box] = (frame_pos, pos_in_frame)
        elif op.getopnum() == rop.LEAVE_FRAME:
            self.builder.leave_frame()
        else:
            xxx
        return
        xxxx
        if op.getopnum() == rop.RESUME_PUT:
            box = op.getarg(0)
            args = op.getarglist()
            if isinstance(box, Const):
                XXX
                newop = op.copy_and_change(rop.RESUME_PUT_CONST)
            elif box in self.virtuals:
                newop = op
            else:
                try:
                    loc = self.regalloc.loc(box, must_exist=True)
                    pos = loc.get_jitframe_position()
                except KeyError:
                    # the thing is not *yet* anywhere, which means we'll record
                    # we know about it, but not store the resume_put just yet
                    self.current_attachment[box] = -1
                    self.frontend_pos[box] = (args[1], args[2])
                    return
                self.current_attachment[box] = pos
                self.frontend_pos[box] = (args[1], args[2])
                args[0] = ConstInt(pos)
                newop = op.copy_and_change(rop.RESUME_PUT, args=args)
        elif op.getopnum() == rop.RESUME_NEW:
            self.virtuals[op.result] = None
            newop = op
        else:
            newop = op
        self.newops.append(newop)

    def _mark_visited(self, v, loc):
        pos = loc.get_jitframe_position()
        if (v not in self.frontend_liveness or
            self.frontend_liveness[v] < self.regalloc.rm.position):
            return
        if v not in self.current_attachment:
            return
        pos = self.builder.encode(TAGBOX, pos)
        if self.current_attachment[v] != pos:
            frame_index, frame_pos = self.frontend_pos[v]
            xxx
            self.newops.append(ResOperation(rop.RESUME_PUT, [
                ConstInt(pos), frame_index, frame_pos],
                None))
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

    def finish(self, parent, parent_position, clt):
        return ResumeBytecode(self.builder.build(), parent, parent_position,
                              clt)


def flatten(inputframes):
    count = 0
    all = {}
    for frame in inputframes:
        for x in frame:
            if x is not None and not isinstance(x, Const) and x not in all:
                count += 1
                all[x] = None
    inputargs = [None] * count
    pos = 0
    all = {}
    for frame in inputframes:
        for item in frame:
            if (item is not None and not isinstance(item, Const) and
                item not in all):
                inputargs[pos] = item
                all[item] = None
                pos += 1
    return inputargs


def compute_vars_longevity(inputframes, operations, descr=None):
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
    if descr is None:
        inputargs = inputframes[0]
        liveness_analyzer = LivenessAnalyzer()
    else:
        inputargs = flatten(inputframes)
        liveness_analyzer = LivenessAnalyzer(inputframes)
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
