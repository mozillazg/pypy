from pypy.jit.metainterp.optimizeopt.optimizer import Optimization
from pypy.jit.metainterp.optimizeopt.util import make_dispatcher_method
from pypy.jit.metainterp.resoperation import rop
from pypy.jit.metainterp.history import TargetToken, JitCellToken

class OptSimplify(Optimization):
    def __init__(self, unroll):
        self.last_label_descr = None
        self.unroll = unroll

    def _new_optimize_call(tp):
        def optimize_call(self, op):
            xxx
            self.emit_operation(op.copy_and_change(getattr(rop, 'CALL_' + tp)))
    optimize_CALL_PURE_i = _new_optimize_call('i')
    optimize_CALL_PURE_f = _new_optimize_call('f')
    optimize_CALL_PURE_v = _new_optimize_call('v')
    optimize_CALL_PURE_r = _new_optimize_call('r')
    optimize_CALL_LOOPINVARIANT_i = _new_optimize_call('i')
    optimize_CALL_LOOPINVARIANT_f = _new_optimize_call('f')
    optimize_CALL_LOOPINVARIANT_v = _new_optimize_call('v')
    optimize_CALL_LOOPINVARIANT_r = _new_optimize_call('r')
    
    def optimize_VIRTUAL_REF_FINISH(self, op):
        pass

    def optimize_VIRTUAL_REF(self, op):
        op = ResOperation(rop.SAME_AS, [op.getarg(0)], op.result)
        self.emit_operation(op)

    def optimize_QUASIIMMUT_FIELD(self, op):
        # xxx ideally we could also kill the following GUARD_NOT_INVALIDATED
        #     but it's a bit hard to implement robustly if heap.py is also run
        pass

    def optimize_RECORD_KNOWN_CLASS(self, op):
        pass

    def optimize_LABEL(self, op):
        if not self.unroll:
            descr = op.getdescr()
            if isinstance(descr, JitCellToken):
                xxx
                return self.optimize_JUMP(op.copy_and_change(rop.JUMP))
            self.last_label_descr = op.getdescr()
        self.emit_operation(op)
        
    def optimize_JUMP(self, op):
        if not self.unroll:
            descr = op.getdescr()
            newdescr = None
            assert isinstance(descr, JitCellToken)
            if not descr.target_tokens:
                assert self.last_label_descr is not None
                target_token = self.last_label_descr
                assert isinstance(target_token, TargetToken)
                assert target_token.targeting_jitcell_token is descr
                newdescr = self.last_label_descr
            else:
                assert len(descr.target_tokens) == 1
                newdescr = descr.target_tokens[0]
            if newdescr is not descr or op.opnum != rop.JUMP:
                op = self.optimizer.copy_and_change(op, op.opnum,
                                                    descr=newdescr)
        self.emit_operation(op)

#dispatch_opt = make_dispatcher_method(OptSimplify, 'optimize_',
#        default=OptSimplify.emit_operation)
#OptSimplify.propagate_forward = dispatch_opt
