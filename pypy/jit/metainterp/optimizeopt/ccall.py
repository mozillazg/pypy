
from pypy.jit.metainterp.optimizeutil import _findall
from pypy.rlib.objectmodel import we_are_translated
from optimizer import *

class OptCCall(Optimization):
    def _dissect_virtual_value(self, args_so_far, value):
        pass

    def optimize_CALL(self, op):
        self.emit_operation(op)
        return
        args = []
        v = self.getvalue(op.args[2])
        while v:
            v = self._dissect_virtual_value(args, v)
        import pdb
        pdb.set_trace()
        return self.optimize_default(op)

    def propagate_forward(self, op):
        opnum = op.opnum
        for value, func in optimize_ops:
            if opnum == value:
                func(self, op)
                break
        else:
            self.emit_operation(op)

optimize_ops = _findall(OptCCall, 'optimize_')
