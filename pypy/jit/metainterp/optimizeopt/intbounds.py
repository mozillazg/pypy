import sys
from pypy.jit.metainterp.optimizeopt.optimizer import Optimization, CONST_1,\
     CONST_0, MODE_ARRAY, MODE_STR, MODE_UNICODE
from pypy.jit.metainterp.optimizeopt.intutils import (IntBound, IntLowerBound,
    IntUpperBound, MININT, MAXINT)
from pypy.jit.metainterp.optimizeopt.util import make_dispatcher_method
from pypy.jit.metainterp.resoperation import rop, ConstInt, INT
from pypy.jit.metainterp.optimize import InvalidLoop


class OptIntBounds(Optimization):
    """Keeps track of the bounds placed on integers by guards and remove
       redundant guards"""

    def new(self):
        return OptIntBounds()

    def process_inputargs(self, args):
        for arg in args:
            if arg.type == INT:
                self.getforwarded(arg).setintbound(IntBound(MININT, MAXINT))
    
    def optimize_operation(self, op):
        if op.type == INT:
            self.getforwarded(op).setintbound(IntBound(MININT, MAXINT))
        return Optimization.optimize_operation(self, op)

    def propagate_bounds_backward(self, op):
        # FIXME: This takes care of the instruction where box is the reuslt
        #        but the bounds produced by all instructions where box is
        #        an argument might also be tighten
        v = self.getforwarded(op)
        b = v.getintbound()
        if b.has_lower and b.has_upper and b.lower == b.upper:
            self.make_constant(v, ConstInt(b.lower))
        dispatch_bounds_ops(self, op)

    def postprocess_GUARD_TRUE(self, op):
        self.propagate_bounds_backward(op.getarg(0))

    postprocess_GUARD_FALSE = postprocess_GUARD_TRUE
    postprocess_GUARD_VALUE = postprocess_GUARD_TRUE

    def optimize_INT_XOR(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        if v1 is v2:
            self.make_constant_int(op, 0)
            return
        self.emit_operation(op)
        if v1.getintbound().known_ge(IntBound(0, 0)) and \
           v2.getintbound().known_ge(IntBound(0, 0)):
            r = self.getvalue(op)
            r.getintbound().make_ge(IntLowerBound(0))

    def optimize_INT_AND(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        self.emit_operation(op)

        r = self.getvalue(op)
        if v2.is_constant():
            val = v2.op.getint()
            if val >= 0:
                r.getintbound().intersect(IntBound(0,val))
        elif v1.is_constant():
            val = v1.op.getint()
            if val >= 0:
                r.getintbound().intersect(IntBound(0,val))

    def postprocess_INT_SUB(self, op):
        v1 = self.getforwarded(op.getarg(0))
        v2 = self.getforwarded(op.getarg(1))
        r = self.getforwarded(op)
        b = v1.getintbound().sub_bound(v2.getintbound())
        if b.bounded():
            r.getintbound().intersect(b)

    def postprocess_INT_ADD(self, op):
        v1 = self.getforwarded(op.getarg(0))
        v2 = self.getforwarded(op.getarg(1))
        r = self.getforwarded(op)
        b = v1.getintbound().add_bound(v2.getintbound())
        if b.bounded():
            r.getintbound().intersect(b)

    def optimize_INT_MUL(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        self.emit_operation(op)
        r = self.getvalue(op)
        b = v1.getintbound().mul_bound(v2.getintbound())
        if b.bounded():
            r.getintbound().intersect(b)

    def optimize_INT_FLOORDIV(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        self.emit_operation(op)
        r = self.getvalue(op)
        r.getintbound().intersect(v1.getintbound().div_bound(v2.getintbound()))

    def optimize_INT_MOD(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        known_nonneg = (v1.getintbound().known_ge(IntBound(0, 0)) and 
                        v2.getintbound().known_ge(IntBound(0, 0)))
        if known_nonneg and v2.is_constant():
            val = v2.op.getint()
            if (val & (val-1)) == 0:
                # nonneg % power-of-two ==> nonneg & (power-of-two - 1)
                arg1 = op.getarg(0)
                arg2 = ConstInt(val-1)
                op = self.optimizer.copy_and_change(op, rop.INT_AND, arg0=arg1,
                                                    arg1=arg2)
        self.emit_operation(op)
        if v2.is_constant():
            val = v2.op.getint()
            r = self.getvalue(op)
            if val < 0:
                if val == -sys.maxint-1:
                    return     # give up
                val = -val
            if known_nonneg:
                r.getintbound().make_ge(IntBound(0, 0))
            else:
                r.getintbound().make_gt(IntBound(-val, -val))
            r.getintbound().make_lt(IntBound(val, val))

    def optimize_INT_LSHIFT(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        self.emit_operation(op)
        r = self.getvalue(op)
        b = v1.getintbound().lshift_bound(v2.getintbound())
        r.getintbound().intersect(b)
        # intbound.lshift_bound checks for an overflow and if the
        # lshift can be proven not to overflow sets b.has_upper and
        # b.has_lower
        if b.has_lower and b.has_upper:
            # Synthesize the reverse op for optimize_default to reuse
            xxx
            self.pure(rop.INT_RSHIFT, [op, op.getarg(1)], op.getarg(0))

    def optimize_INT_RSHIFT(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        b = v1.getintbound().rshift_bound(v2.getintbound())
        if b.has_lower and b.has_upper and b.lower == b.upper:
            # constant result (likely 0, for rshifts that kill all bits)
            self.make_constant_int(op, b.lower)
        else:
            self.emit_operation(op)
            r = self.getvalue(op)
            r.getintbound().intersect(b)

    def optimize_GUARD_NO_OVERFLOW(self, op):
        lastop = self.last_emitted_operation
        if lastop is not None:
            opnum = lastop.getopnum()
            args = lastop.getarglist()
            result = lastop
            # If the INT_xxx_OVF was replaced with INT_xxx, then we can kill
            # the GUARD_NO_OVERFLOW.
            if (opnum == rop.INT_ADD or
                opnum == rop.INT_SUB or
                opnum == rop.INT_MUL):
                return
            # Else, synthesize the non overflowing op for optimize_default to
            # reuse, as well as the reverse op
            elif opnum == rop.INT_ADD_OVF:
                self.pure(result, rop.INT_ADD, args[0], args[1])
                self.pure(args[0], rop.INT_SUB, result, args[1])
                self.pure(args[1], rop.INT_SUB, result, args[0])
            elif opnum == rop.INT_SUB_OVF:
                self.pure(result, rop.INT_SUB, args[0], args[1])
                self.pure(args[0], rop.INT_ADD, result, args[1])
                self.pure(args[1], rop.INT_SUB, args[0], result)
            elif opnum == rop.INT_MUL_OVF:
                self.pure(result, rop.INT_MUL, args[0], args[1])
        self.emit_operation(op)

    def optimize_GUARD_OVERFLOW(self, op):
        # If INT_xxx_OVF was replaced by INT_xxx, *but* we still see
        # GUARD_OVERFLOW, then the loop is invalid.
        lastop = self.last_emitted_operation
        if lastop is None:
            raise InvalidLoop('An INT_xxx_OVF was proven not to overflow but' +
                              'guarded with GUARD_OVERFLOW')
        opnum = lastop.getopnum()
        if opnum not in (rop.INT_ADD_OVF, rop.INT_SUB_OVF, rop.INT_MUL_OVF):
            raise InvalidLoop('An INT_xxx_OVF was proven not to overflow but' +
                              'guarded with GUARD_OVERFLOW')
                             
        self.emit_operation(op)

    def optimize_INT_ADD_OVF(self, op):
        op = self.getforwarded(op)
        v1 = self.getforwarded(op.getarg(0))
        v2 = self.getforwarded(op.getarg(1))
        resbound = v1.getintbound().add_bound(v2.getintbound())
        if resbound.bounded():
            # Transform into INT_ADD.  The following guard will be killed
            # by optimize_GUARD_NO_OVERFLOW; if we see instead an
            # optimize_GUARD_OVERFLOW, then InvalidLoop.
            op = op.make_forwarded_copy(rop.INT_ADD)
            op.getintbound().intersect(resbound)
        return op

    def optimize_INT_SUB_OVF(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        resbound = v1.getintbound().sub_bound(v2.getintbound())
        if resbound.bounded():
            op = self.optimizer.copy_and_change(op, rop.INT_SUB)
        self.emit_operation(op) # emit the op
        r = self.getvalue(op)
        r.getintbound().intersect(resbound)

    def optimize_INT_MUL_OVF(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        resbound = v1.getintbound().mul_bound(v2.getintbound())
        if resbound.bounded():
            op = self.optimizer.copy_and_change(op, rop.INT_MUL)
        self.emit_operation(op)
        r = self.getvalue(op)
        r.getintbound().intersect(resbound)

    def optimize_INT_LT(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        if v1.getintbound().known_lt(v2.getintbound()):
            self.make_constant_int(op, 1)
        elif v1.getintbound().known_ge(v2.getintbound()) or v1 is v2:
            self.make_constant_int(op, 0)
        else:
            self.emit_operation(op)

    def optimize_INT_GT(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        if v1.getintbound().known_gt(v2.getintbound()):
            self.make_constant_int(op, 1)
        elif v1.getintbound().known_le(v2.getintbound()) or v1 is v2:
            self.make_constant_int(op, 0)
        else:
            self.emit_operation(op)

    def optimize_INT_LE(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        if v1.getintbound().known_le(v2.getintbound()) or v1 is v2:
            self.make_constant_int(op, 1)
        elif v1.getintbound().known_gt(v2.getintbound()):
            self.make_constant_int(op, 0)
        else:
            self.emit_operation(op)

    def optimize_INT_GE(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        if v1.getintbound().known_ge(v2.getintbound()) or v1 is v2:
            self.make_constant_int(op, 1)
        elif v1.getintbound().known_lt(v2.getintbound()):
            self.make_constant_int(op, 0)
        else:
            self.emit_operation(op)

    def optimize_INT_EQ(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        if v1.getintbound().known_gt(v2.getintbound()):
            self.make_constant_int(op, 0)
        elif v1.getintbound().known_lt(v2.getintbound()):
            self.make_constant_int(op, 0)
        elif v1 is v2:
            self.make_constant_int(op, 1)
        else:
            self.emit_operation(op)

    def optimize_INT_NE(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        if v1.getintbound().known_gt(v2.getintbound()):
            self.make_constant_int(op, 1)
        elif v1.getintbound().known_lt(v2.getintbound()):
            self.make_constant_int(op, 1)
        elif v1 is v2:
            self.make_constant_int(op, 0)
        else:
            self.emit_operation(op)

    def optimize_ARRAYLEN_GC(self, op):
        self.emit_operation(op)
        array  = self.getvalue(op.getarg(0))
        result = self.getvalue(op)
        array.make_len_gt(MODE_ARRAY, op.getdescr(), -1)
        array.lenbound.bound.intersect(result.getintbound())
        result.setintbound(array.lenbound.bound)

    def optimize_STRLEN(self, op):
        self.emit_operation(op)
        array  = self.getvalue(op.getarg(0))
        result = self.getvalue(op)
        array.make_len_gt(MODE_STR, op.getdescr(), -1)
        array.lenbound.bound.intersect(result.getintbound())
        result.setintbound(array.lenbound.bound)

    def optimize_UNICODELEN(self, op):
        self.emit_operation(op)
        array  = self.getvalue(op.getarg(0))
        result = self.getvalue(op)
        array.make_len_gt(MODE_UNICODE, op.getdescr(), -1)
        array.lenbound.bound.intersect(result.getintbound())
        result.setintbound(array.lenbound.bound)

    def optimize_STRGETITEM(self, op):
        self.emit_operation(op)
        v1 = self.getvalue(op)
        v1.getintbound().make_ge(IntLowerBound(0))
        v1.getintbound().make_lt(IntUpperBound(256))

    def optimize_UNICODEGETITEM(self, op):
        self.emit_operation(op)
        v1 = self.getvalue(op)
        v1.getintbound().make_ge(IntLowerBound(0))

    def make_int_lt(self, box1, box2):
        v1 = self.getvalue(box1)
        v2 = self.getvalue(box2)
        if v1.getintbound().make_lt(v2.getintbound()):
            self.propagate_bounds_backward(box1)
        if v2.getintbound().make_gt(v1.getintbound()):
            self.propagate_bounds_backward(box2)

    def make_int_le(self, box1, box2):
        v1 = self.getvalue(box1)
        v2 = self.getvalue(box2)
        if v1.getintbound().make_le(v2.getintbound()):
            self.propagate_bounds_backward(box1)
        if v2.getintbound().make_ge(v1.getintbound()):
            self.propagate_bounds_backward(box2)

    def make_int_gt(self, box1, box2):
        self.make_int_lt(box2, box1)

    def make_int_ge(self, box1, box2):
        self.make_int_le(box2, box1)

    def propagate_bounds_INT_LT(self, op):
        r = self.getvalue(op)
        if r.is_constant():
            if r.op.same_constant(CONST_1):
                self.make_int_lt(op.getarg(0), op.getarg(1))
            else:
                self.make_int_ge(op.getarg(0), op.getarg(1))

    def propagate_bounds_INT_GT(self, op):
        r = self.getvalue(op)
        if r.is_constant():
            if r.op.same_constant(CONST_1):
                self.make_int_gt(op.getarg(0), op.getarg(1))
            else:
                self.make_int_le(op.getarg(0), op.getarg(1))

    def propagate_bounds_INT_LE(self, op):
        r = self.getvalue(op)
        if r.is_constant():
            if r.op.same_constant(CONST_1):
                self.make_int_le(op.getarg(0), op.getarg(1))
            else:
                self.make_int_gt(op.getarg(0), op.getarg(1))

    def propagate_bounds_INT_GE(self, op):
        r = self.getvalue(op)
        if r.is_constant():
            if r.op.same_constant(CONST_1):
                self.make_int_ge(op.getarg(0), op.getarg(1))
            else:
                self.make_int_lt(op.getarg(0), op.getarg(1))

    def propagate_bounds_INT_EQ(self, op):
        r = self.getvalue(op)
        if r.is_constant():
            if r.op.same_constant(CONST_1):
                v1 = self.getvalue(op.getarg(0))
                v2 = self.getvalue(op.getarg(1))
                if v1.getintbound().intersect(v2.getintbound()):
                    self.propagate_bounds_backward(op.getarg(0))
                if v2.getintbound().intersect(v1.getintbound()):
                    self.propagate_bounds_backward(op.getarg(1))

    def propagate_bounds_INT_NE(self, op):
        r = self.getvalue(op)
        if r.is_constant():
            if r.op.same_constant(CONST_0):
                v1 = self.getvalue(op.getarg(0))
                v2 = self.getvalue(op.getarg(1))
                if v1.getintbound().intersect(v2.getintbound()):
                    self.propagate_bounds_backward(op.getarg(0))
                if v2.getintbound().intersect(v1.getintbound()):
                    self.propagate_bounds_backward(op.getarg(1))

    def propagate_bounds_INT_IS_TRUE(self, op):
        r = self.getforwarded(op)
        if r.is_constant():
            if r.same_constant(CONST_1):
                v1 = self.getforwarded(op.getarg(0))
                if v1.getintbound().known_ge(IntBound(0, 0)):
                    v1.getintbound().make_gt(IntBound(0, 0))
                    self.propagate_bounds_backward(op.getarg(0))

    def propagate_bounds_INT_IS_ZERO(self, op):
        r = self.getforwarded(op)
        if r.is_constant():
            if r.same_constant(CONST_1):
                v1 = self.getforwarded(op.getarg(0))
                # Clever hack, we can't use self.make_constant_int yet because
                # the args aren't in the values dictionary yet so it runs into
                # an assert, this is a clever way of expressing the same thing.
                v1.getintbound().make_ge(IntBound(0, 0))
                v1.getintbound().make_lt(IntBound(1, 1))
                self.propagate_bounds_backward(op.getarg(0))

    def propagate_bounds_INT_ADD(self, op):
        v1 = self.getforwarded(op.getarg(0))
        v2 = self.getforwarded(op.getarg(1))
        r = self.getforwarded(op)
        b = r.getintbound().sub_bound(v2.getintbound())
        if v1.getintbound().intersect(b):
            self.propagate_bounds_backward(op.getarg(0))
        b = r.getintbound().sub_bound(v1.getintbound())
        if v2.getintbound().intersect(b):
            self.propagate_bounds_backward(op.getarg(1))

    def propagate_bounds_INT_SUB(self, op):
        v1 = self.getforwarded(op.getarg(0))
        v2 = self.getforwarded(op.getarg(1))
        r = self.getforwarded(op)
        b = r.getintbound().add_bound(v2.getintbound())
        if v1.getintbound().intersect(b):
            self.propagate_bounds_backward(op.getarg(0))
        b = r.getintbound().sub_bound(v1.getintbound()).mul(-1)
        if v2.getintbound().intersect(b):
            self.propagate_bounds_backward(op.getarg(1))

    def propagate_bounds_INT_MUL(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        r = self.getvalue(op)
        b = r.getintbound().div_bound(v2.getintbound())
        if v1.getintbound().intersect(b):
            self.propagate_bounds_backward(op.getarg(0))
        b = r.getintbound().div_bound(v1.getintbound())
        if v2.getintbound().intersect(b):
            self.propagate_bounds_backward(op.getarg(1))

    def propagate_bounds_INT_LSHIFT(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        r = self.getvalue(op)
        b = r.getintbound().rshift_bound(v2.getintbound())
        if v1.getintbound().intersect(b):
            self.propagate_bounds_backward(op.getarg(0))

    propagate_bounds_INT_ADD_OVF  = propagate_bounds_INT_ADD
    propagate_bounds_INT_SUB_OVF  = propagate_bounds_INT_SUB
    propagate_bounds_INT_MUL_OVF  = propagate_bounds_INT_MUL


dispatch_bounds_ops = make_dispatcher_method(OptIntBounds, 'propagate_bounds_')
