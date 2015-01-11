
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
    _attrs_ = ('keybox',)
    box = None

    def __init__(self, unroller, keybox):
        self.unroller = unroller
        self.keybox = keybox

    def force_box(self, optforce):
        if self.box is None:
            self.box = self.keybox
            optforce.optimizer.reuse_pure_result(self.box)
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
