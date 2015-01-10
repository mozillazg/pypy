
from rpython.jit.metainterp.optimizeopt.optimizer import Optimizer, OptValue


def optimize_unroll(metainterp_sd, jitdriver_sd, loop, optimizations,
                    inline_short_preamble=True, unroller=None):
    if unroller is None:
        unroller = Unroller()
    unroller.set_optimizer(Optimizer(metainterp_sd, jitdriver_sd,
                                     loop, optimizations))
    unroller.propagate(inline_short_preamble)
    return unroller


class OptPureValue(OptValue):
    _attrs_ = ('unroller', 'keybox')
    box = None

    def __init__(self, unroller, keybox):
        self.unroller = unroller
        self.keybox = keybox

    def force_box(self, ignored):
        if self.box is None:
            self.box = self.keybox
            self.unroller.reuse_pure_result(self.box)
        return self.box


class Unroller(object):
    optimizer = None

    def set_optimizer(self, optimizer):
        old_optimizer = self.optimizer
        self.optimizer = optimizer
        if old_optimizer is not None:
            self.import_state_from_optimizer(old_optimizer)

    def propagate(self, inline_short_preamble):
        self.optimizer.propagate_all_forward()

    def import_state_from_optimizer(self, old_optimizer):
        old_optpure = old_optimizer.optpure
        if old_optpure:
            # import all pure operations from the old optimizer
            new_optpure = self.optimizer.optpure
            for opargs, value in old_optpure.pure_operations.items():
                if not value.is_virtual():
                    pure_value = OptPureValue(self, value.box)
                    new_optpure.pure_operations[opargs] = pure_value

    def reuse_pure_result(self, box):
        label1_op = self.optimizer.loop.operations[0]
        label1_args = label1_op.getarglist()
        label2_op = self.optimizer.loop.operations[-1]
        label2_args = label2_op.getarglist()
        assert len(label1_args) == len(self.optimizer.loop.inputargs)
        assert len(label2_args) == len(self.optimizer.loop.inputargs)
        self.optimizer.loop.inputargs.append(box)
        label1_args.append(box)
        label2_args.append(box)
