from pypy.jit.metainterp.optimizeopt.optimizer import Optimization, REMOVED
from pypy.jit.metainterp.resoperation import rop, create_resop_2,\
     create_resop_1, example_for_opnum
from pypy.jit.metainterp.optimizeopt.util import make_dispatcher_method,\
     ArgsDict
from pypy.rlib.objectmodel import specialize

class OptPure(Optimization):
    def __init__(self):
        self.posponedop = None
        self.pure_operations = ArgsDict()
        self.emitted_pure_operations = []

    def optimize_default(self, op):
        orig_op = op
        op = self.getforwarded(op)
        canfold = op.is_always_pure()
        if op.is_ovf():
            self.posponedop = op
            return
        if self.posponedop:
            nextop = op
            op = self.posponedop
            self.posponedop = None
            canfold = nextop.getopnum() == rop.GUARD_NO_OVERFLOW
        else:
            nextop = None

        if canfold:
            for i in range(op.numargs()):
                if self.get_constant_op(op.getarg(i)) is None:
                    break
            else:
                # all constant arguments: constant-fold away
                resbox = self.optimizer.constant_fold(op)
                # note that INT_xxx_OVF is not done from here, and the
                # overflows in the INT_xxx operations are ignored
                self.optimizer.make_constant(op, resbox)
                return

            # did we do the exact same operation already?
            oldop = self.pure_operations.get(orig_op)
            if oldop is not None:
                self.optimizer.replace(op, oldop)
                return
            else:
                self.pure_operations.set(orig_op, op)
                self.remember_emitting_pure(op)

        # otherwise, the operation remains
        if nextop:
            return nextop
        return op

    def _new_optimize_call_pure(opnum):
        def optimize_CALL_PURE(self, op):
            oldop = self.pure_operations.get(op)
            if oldop is not None and oldop.getdescr() is op.getdescr():
                assert oldop.getopnum() == op.getopnum()
                # this removes a CALL_PURE that has the same (non-constant)
                # arguments as a previous CALL_PURE.
                self.replace(op, oldop)
                self.last_emitted_operation = REMOVED
                return
            else:
                new_op = self.optimizer.getforwarded(op)
                self.pure_operations.set(new_op, op)
                self.remember_emitting_pure(op)

            # replace CALL_PURE with just CALL
            xxx
            self.emit_operation(self.optimizer.copy_and_change(op, opnum))
        return optimize_CALL_PURE
    optimize_CALL_PURE_i = _new_optimize_call_pure(rop.CALL_i)
    optimize_CALL_PURE_f = _new_optimize_call_pure(rop.CALL_f)
    optimize_CALL_PURE_r = _new_optimize_call_pure(rop.CALL_r)
    optimize_CALL_PURE_v = _new_optimize_call_pure(rop.CALL_v)

    def optimize_GUARD_NO_EXCEPTION(self, op):
        if self.last_emitted_operation is REMOVED:
            # it was a CALL_PURE that was killed; so we also kill the
            # following GUARD_NO_EXCEPTION
            return
        return op

    def flush(self):
        assert self.posponedop is None

    def new(self):
        assert self.posponedop is None
        return OptPure()

    def setup(self):
        self.optimizer.optpure = self

    @specialize.arg(2)
    def pure(self, oldop, opnum, arg0, arg1=None):
        arg0 = arg0.get_key_op(self.optimizer)
        if arg1 is not None:
            arg1 = arg1.get_key_op(self.optimizer)
        result = example_for_opnum(opnum)
        if arg1 is None:
            op = create_resop_1(opnum, result, arg0)
        else:
            op = create_resop_2(opnum, result, arg0, arg1)
        self.pure_operations.set(op, oldop)

    def has_pure_result(self, op_key):
        op = self.pure_operations.get(op_key)
        if op is None:
            return False
        return op.getdescr() is op_key.getdescr()

    def get_pure_result(self, key):
        return self.pure_operations.get(key)

    def remember_emitting_pure(self, op):
        self.emitted_pure_operations.append(op)

    def produce_potential_short_preamble_ops(self, sb):
        for op in self.emitted_pure_operations:
            if op.getopnum() == rop.GETARRAYITEM_GC_PURE_i or \
               op.getopnum() == rop.GETARRAYITEM_GC_PURE_r or \
               op.getopnum() == rop.GETARRAYITEM_GC_PURE_f or \
               op.getopnum() == rop.STRGETITEM or \
               op.getopnum() == rop.UNICODEGETITEM:
                if not self.getvalue(op.getarg(1)).is_constant():
                    continue
            sb.add_potential(op)

#dispatch_opt = make_dispatcher_method(OptPure, 'optimize_',
#                                      default=OptPure.optimize_default)
