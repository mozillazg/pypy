
from rpython.jit.metainterp.optimizeopt import optimizer
from rpython.jit.metainterp.optimizeopt.util import make_dispatcher_method
from rpython.jit.metainterp.history import Const

""" All of this directly emit the ops, without calling emit_operation
(they also don't have boxes except a resume_put)
"""

class OptResume(optimizer.Optimization):
    def optimize_RESUME_PUT(self, op):
        arg = op.getarg(0)
        if (isinstance(arg, Const) or arg in self.optimizer.producer or
            arg in self.optimizer.loop.inputargs):
            self.optimizer.resumebuilder.resume_put(op)
        else:
            xxx
            self.optimizer.delayed_resume_put = op
            # otherwise we did not emit the operation just yet

    def optimize_ENTER_FRAME(self, op):
        rb = self.optimizer.resumebuilder
        rb.enter_frame(op.getarg(0).getint(), op.getdescr())
        self.optimizer._newoperations.append(op)

    def optimize_LEAVE_FRAME(self, op):
        self.optimizer.resumebuilder.leave_frame(op)
        self.optimizer._newoperations.append(op)

    def optimize_RESUME_SET_PC(self, op):
        self.optimizer._newoperations.append(op)        

dispatch_opt = make_dispatcher_method(OptResume, 'optimize_',
        default=OptResume.emit_operation)

OptResume.propagate_forward = dispatch_opt
