from pypy.jit.metainterp.optimizeopt.optimizer import Optimization
from pypy.jit.metainterp.resoperation import rop

def check_early_force(opt, opnum, num, arg):
    try:
        value = arg.get_extra("optimizer_value")
    except KeyError:
        return
    value.force_box(opt)

class OptEarlyForce(Optimization):
    def propagate_forward(self, op):
        opnum = op.getopnum()
        if (opnum != rop.SETFIELD_GC and 
            opnum != rop.SETARRAYITEM_GC and
            opnum != rop.QUASIIMMUT_FIELD and
            opnum != rop.SAME_AS_i and
            opnum != rop.SAME_AS_p and
            opnum != rop.SAME_AS_f and
            opnum != rop.MARK_OPAQUE_PTR):

            op.foreach_arg(check_early_force, self)
        self.emit_operation(op)

    def new(self):
        return OptEarlyForce()

    def setup(self):
        self.optimizer.optearlyforce = self

    
