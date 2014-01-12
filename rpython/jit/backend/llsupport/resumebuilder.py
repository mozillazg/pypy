
from rpython.jit.metainterp.resoperation import rop, ResOperation
from rpython.jit.metainterp.history import ConstInt
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
    def __init__(self, regalloc, frontend_liveness, descr):
        self.newops = []
        self.regalloc = regalloc
        self.current_attachment = {}
        self.frontend_liveness = frontend_liveness
        self.frontend_pos = {}
        self.virtuals = {}

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

