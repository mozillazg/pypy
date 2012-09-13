
from pypy.jit.metainterp.resoperation import Const
from pypy.jit.metainterp.resume import Snapshot

class Inliner(object):
    def __init__(self, inputargs, jump_args):
        assert len(inputargs) == len(jump_args)
        self.argmap = {}
        for i in range(len(inputargs)):
            if inputargs[i] in self.argmap:
                assert self.argmap[inputargs[i]] == jump_args[i]
            else:
                self.argmap[inputargs[i]] = jump_args[i]
        self.snapshot_map = {None: None}

    def inline_op(self, op):
        newop = op.copy_if_modified_by_optimization(self, force_copy=True)
        if newop.is_guard():
            args = op.getfailargs()
            if args:
                newop.setfailargs([self.get_value_replacement(a) for a in args])

        self.argmap[op] = newop
        self.inline_descr_inplace(newop.getdescr())
        return newop

    def inline_descr_inplace(self, descr):
        from pypy.jit.metainterp.compile import ResumeGuardDescr
        if isinstance(descr, ResumeGuardDescr):
            descr.rd_snapshot = self.inline_snapshot(descr.rd_snapshot)

    def get_value_replacement(self, arg):
        if arg is None:
            return None
        if isinstance(arg, Const):
            return arg
        return self.argmap[arg]

    def inline_snapshot(self, snapshot):
        if snapshot in self.snapshot_map:
            return self.snapshot_map[snapshot]
        boxes = [self.get_value_replacement(a) for a in snapshot.boxes]
        new_snapshot = Snapshot(self.inline_snapshot(snapshot.prev), boxes)
        self.snapshot_map[snapshot] = new_snapshot
        return new_snapshot

