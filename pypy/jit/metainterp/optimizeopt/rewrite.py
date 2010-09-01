from optimizer import Optimization, CONST_1, CONST_0
from pypy.jit.metainterp.resoperation import opboolinvers, opboolreflex
from pypy.jit.metainterp.history import ConstInt

class Rewrite(Optimization):
    """Rewrite operations into equvivialent, already executed operations
       or constants.
    """
    
    def propagate_forward(self, op):
        args = self.optimizer.make_args_key(op)
        if self.find_rewritable_bool(op, args):
            return
        self.emit_operation(op)
        
    def try_boolinvers(self, op, targs):
        oldop = self.optimizer.pure_operations.get(targs, None)
        if oldop is not None and oldop.descr is op.descr:
            value = self.getvalue(oldop.result)
            if value.is_constant():
                if value.box.same_constant(CONST_1):
                    self.make_constant(op.result, CONST_0)
                    return True
                elif value.box.same_constant(CONST_0):
                    self.make_constant(op.result, CONST_1)
                    return True

        return False


    def find_rewritable_bool(self, op, args):
        try:
            oldopnum = opboolinvers[op.opnum]
            targs = [args[0], args[1], ConstInt(oldopnum)]
            if self.try_boolinvers(op, targs):
                return True
        except KeyError:
            pass

        try:
            oldopnum = opboolreflex[op.opnum]
            targs = [args[1], args[0], ConstInt(oldopnum)]
            oldop = self.optimizer.pure_operations.get(targs, None)
            if oldop is not None and oldop.descr is op.descr:
                self.make_equal_to(op.result, self.getvalue(oldop.result))
                return True
        except KeyError:
            pass

        try:
            oldopnum = opboolinvers[opboolreflex[op.opnum]]
            targs = [args[1], args[0], ConstInt(oldopnum)]
            if self.try_boolinvers(op, targs):
                return True
        except KeyError:
            pass

        return False

        


        
