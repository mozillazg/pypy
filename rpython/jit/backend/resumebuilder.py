
from rpython.jit.metainterp.resoperation import rop, ResOperation
from rpython.jit.metainterp.history import ConstInt, Box
from rpython.jit.metainterp.resume2 import ResumeBytecode, AbstractResumeReader

class LivenessAnalyzer(AbstractResumeReader):
    def __init__(self, inputframes=None):
        self.liveness = {}
        self.frame_starts = [0]
        self.framestack = []
        self.deps = {}
        if inputframes is not None:
            for frame in inputframes:
                self.frame_starts.append(self.frame_starts[-1] + len(frame))
                self.framestack.append(frame)

    def enter_frame(self, pc, jitcode):
        self.frame_starts.append(self.frame_starts[-1] + jitcode.num_regs())
        self.framestack.append([None] * jitcode.num_regs())

    def resume_put(self, box, framepos, frontend_pos):
        self.framestack[framepos][frontend_pos] = box

    def resume_new(self, result, descr):
        self.deps[result] = {}

    def resume_setfield_gc(self, arg0, arg1, descr):
        self.deps[arg0][descr] = arg1

    def _track(self, allboxes, box):
        if box in self.deps:
            for dep in self.deps[box].values():
                self._track(allboxes, dep)
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

class ResumeBuilder(object):
    def __init__(self, regalloc, frontend_liveness, descr, inputframes=None,
                 inputlocs=None):
        self.newops = []
        self.regalloc = regalloc
        self.current_attachment = {}
        self.frontend_liveness = frontend_liveness
        self.frontend_pos = {}
        self.virtuals = {}
        if inputlocs is not None:
            i = 0
            for frame_pos, frame in enumerate(inputframes):
                for pos_in_frame, box in enumerate(frame):
                    loc_pos = inputlocs[i].get_jitframe_position()
                    self.current_attachment[box] = loc_pos
                    self.frontend_pos[box] = (ConstInt(frame_pos),
                                              ConstInt(pos_in_frame))
                    i += 1

    def process(self, op):
        if op.getopnum() == rop.RESUME_PUT:
            box = op.getarg(0)
            args = op.getarglist()
            if box in self.virtuals:
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
        if self.current_attachment[v] != pos:
            frame_index, frame_pos = self.frontend_pos[v]
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
        return len(self.newops)

    def finish(self, parent, parent_position, clt):
        return ResumeBytecode(self.newops, parent, parent_position, clt)


def flatten(inputframes):
    count = 0
    for frame in inputframes:
        count += len(frame)
    inputargs = [None] * count
    i = 0
    for frame in inputframes:
        inputargs[i:i + len(frame)] = frame
        i += len(frame)
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
                    if item is not None:
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
