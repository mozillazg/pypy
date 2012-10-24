from pypy.jit.metainterp.optimizeopt.optimizer import Optimization
from pypy.jit.metainterp.resoperation import rop

def check_early_force(opt, opnum, num, arg):
    value = opt.getvalue(arg, create=False)
    if value is not None:
        value.force_box(opt)

class OptEarlyForce(Optimization):
    def propagate_forward(self, op):
        self.emit_operation(op)
        return
        opnum = op.getopnum()
        if (opnum != rop.SETFIELD_GC and 
            opnum != rop.SETARRAYITEM_GC and
            opnum != rop.QUASIIMMUT_FIELD and
            opnum != rop.SAME_AS_i and
            opnum != rop.SAME_AS_r and
            opnum != rop.SAME_AS_f and
            opnum != rop.MARK_OPAQUE_PTR):

            op.foreach_arg(check_early_force, self)
        self.emit_operation(op)

    def new(self):
        return OptEarlyForce()
    
    def setup(self):
        self.optimizer.optearlyforce = self

    
