from optimizer import Optimization, CONST_1, CONST_0
from pypy.jit.metainterp.resoperation import opboolinvers, opboolreflex
from pypy.jit.metainterp.history import ConstInt
from pypy.jit.metainterp.optimizeutil import _findall
from pypy.jit.metainterp.resoperation import rop, ResOperation

class OptRewrite(Optimization):
    """Rewrite operations into equvivialent, already executed operations
       or constants.
    """
    
    def propagate_forward(self, op):
        args = self.optimizer.make_args_key(op)
        if self.find_rewritable_bool(op, args):
            return

        opnum = op.opnum
        for value, func in optimize_ops:
            if opnum == value:
                func(self, op)
                break
        else:
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
            oldopnum = opboolreflex[op.opnum] # FIXME: add INT_ADD, INT_MUL
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

    def optimize_INT_AND(self, op):
        v1 = self.getvalue(op.args[0])
        v2 = self.getvalue(op.args[1])
        if v1.is_null() or v2.is_null():
            self.make_constant_int(op.result, 0)
        else:
            self.emit_operation(op)

    def optimize_INT_OR(self, op):
        v1 = self.getvalue(op.args[0])
        v2 = self.getvalue(op.args[1])
        if v1.is_null():
            self.make_equal_to(op.result, v2)
        elif v2.is_null():
            self.make_equal_to(op.result, v1)
        else:
            self.emit_operation(op)

    def optimize_INT_SUB(self, op):
        v1 = self.getvalue(op.args[0])
        v2 = self.getvalue(op.args[1])
        if v2.is_constant() and v2.box.getint() == 0:
            self.make_equal_to(op.result, v1)
        else:
            self.emit_operation(op)

        # Synthesize the reverse ops for optimize_default to reuse
        self.pure(rop.INT_ADD, [op.result, op.args[1]], op.args[0])
        self.pure(rop.INT_SUB, [op.args[0], op.result], op.args[1])

    def optimize_INT_ADD(self, op):
        v1 = self.getvalue(op.args[0])
        v2 = self.getvalue(op.args[1])

        # If one side of the op is 0 the result is the other side.
        if v1.is_constant() and v1.box.getint() == 0:
            self.make_equal_to(op.result, v2)
        elif v2.is_constant() and v2.box.getint() == 0:
            self.make_equal_to(op.result, v1)
        else:
            self.emit_operation(op)

        # Synthesize the reverse op for optimize_default to reuse
        self.pure(rop.INT_SUB, [op.result, op.args[1]], op.args[0])
        self.pure(rop.INT_SUB, [op.result, op.args[0]], op.args[1])

    def optimize_INT_MUL(self, op):
        v1 = self.getvalue(op.args[0])
        v2 = self.getvalue(op.args[1])

        # If one side of the op is 1 the result is the other side.
        if v1.is_constant() and v1.box.getint() == 1:
            self.make_equal_to(op.result, v2)
        elif v2.is_constant() and v2.box.getint() == 1:
            self.make_equal_to(op.result, v1)
        elif (v1.is_constant() and v1.box.getint() == 0) or \
             (v2.is_constant() and v2.box.getint() == 0):
            self.make_constant_int(op.result, 0)
        else:
            self.emit_operation(op)


optimize_ops = _findall(OptRewrite, 'optimize_')
        


        
