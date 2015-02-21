
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

    def is_virtual(self):
        return False

    def force_box(self, optforce):
        if self.box is None:
            # XXX add myself to the short preamble
            self.box = self.keybox
            optforce.optimizer.reuse_pure_result(self.box)
        return self.box

    def get_key_box(self):
        return self.keybox


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
            old_ops = old_optimizer._newoperations
            for op in old_ops:
                if op.is_always_pure():
                    pure_value = OptPureValue(self, op.result)
                    new_optpure.pure(op.getopnum(), op.getarglist(),
                                     op.result, pure_value)
                    self.optimizer.pure_reverse(op)
        for box in self.optimizer.loop.operations[0].getarglist():
            try:
                # XXX do the same thing for pure opt value
                other = old_optimizer.values[box]
                self.optimizer.getvalue(box).import_from(other,
                                                         self.optimizer)
            except KeyError:
                pass
        
    #         for opargs, value in old_optpure.pure_operations.items():
    #             if not value.is_virtual():
    #                 pure_value = OptPureValue(self, value.box)
    #                 new_optpure.pure_operations[opargs] = pure_value

    # def produce_potential_short_preamble_ops(self, sb):
    #     ops = sb.optimizer._newoperations
    #     for i, op in enumerate(ops):
    #         if op.is_always_pure():
    #             sb.add_potential(op)
    #         if op.is_ovf() and ops[i + 1].getopnum() == rop.GUARD_NO_OVERFLOW:
    #             sb.add_potential(op)
    #     for i in self.call_pure_positions:
    #         op = ops[i]
    #         assert op.getopnum() == rop.CALL
    #         op = op.copy_and_change(rop.CALL_PURE)
    #         sb.add_potential(op)
