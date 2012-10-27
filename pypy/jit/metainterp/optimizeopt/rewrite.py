from pypy.jit.codewriter.effectinfo import EffectInfo
from pypy.jit.metainterp.optimize import InvalidLoop
from pypy.jit.metainterp.optimizeopt.intutils import IntBound
from pypy.jit.metainterp.optimizeopt.optimizer import Optimization, CONST_1,\
     CONST_0
from pypy.jit.metainterp.resoperation import (opboolinvers, opboolreflex, rop,
                                              ConstInt, make_hashable_int,
                                              create_resop_2, Const)
from pypy.rlib.rarithmetic import highest_bit


class OptRewrite(Optimization):
    """Rewrite operations into equivalent, cheaper operations.
       This includes already executed operations and constants.
    """
    def __init__(self):
        self.loop_invariant_results = {}
        self.loop_invariant_producer = {}

    def new(self):
        return OptRewrite()

    def produce_potential_short_preamble_ops(self, sb):
        for op in self.loop_invariant_producer.values():
            sb.add_potential(op)

    def try_boolinvers(self, op, key_op):
        oldop = self.get_pure_result(key_op)
        if oldop is not None and oldop.getdescr() is op.getdescr():
            value = self.getvalue(oldop)
            if value.is_constant():
                if value.op.same_constant(CONST_1):
                    self.make_constant(op, CONST_0)
                    return True
                elif value.op.same_constant(CONST_0):
                    self.make_constant(op, CONST_1)
                    return True

        return False


    def find_rewritable_bool(self, op):
        oldopnum = opboolinvers[op.getopnum()]
        if oldopnum != -1:
            key_op = op.copy_and_change(oldopnum)
            if self.try_boolinvers(op, key_op):
                return True

        oldopnum = opboolreflex[op.getopnum()] # FIXME: add INT_ADD, INT_MUL
        if oldopnum != -1:
            key_op = op.copy_and_change(oldopnum, arg0=op.getarg(1),
                                        arg1=op.getarg(0))
            oldop = self.get_pure_result(key_op)
            if oldop is not None and oldop.getdescr() is op.getdescr():
                self.optimizer.replace(op, oldop)
                return True

        oldopnum = opboolinvers[opboolreflex[op.getopnum()]]
        if oldopnum != -1:
            key_op = op.copy_and_change(oldopnum, arg0=op.getarg(1),
                                        arg1=op.getarg(0))
            if self.try_boolinvers(op, key_op):
                return True

        return False

    def optimize_INT_AND(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        if v1.is_null() or v2.is_null():
            self.make_constant_int(op, 0)
        else:
            self.emit_operation(op)

    def optimize_INT_OR(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        if v1.is_null():
            self.optimizer.replace(op, op.getarg(1))
        elif v2.is_null():
            self.optimizer.replace(op, op.getarg(0))
        else:
            self.emit_operation(op)

    def optimize_INT_SUB(self, op):
        v2 = self.getforwarded(op.getarg(1))
        if v2.is_constant() and v2.getint() == 0:
            self.optimizer.replace(op, op.getarg(0))
        else:
            # Synthesize the reverse ops for optimize_default to reuse
            self.pure(op.getarg(0), rop.INT_ADD, op.getarg(1), op)
            self.pure(op.getarg(0), rop.INT_ADD, op, op.getarg(1))
            self.pure(op.getarg(1), rop.INT_SUB, op.getarg(0), op)
            return op

    def optimize_INT_ADD(self, op):
        arg1 = op.getarg(0)
        arg2 = op.getarg(1)
        v1 = self.getforwarded(arg1)
        v2 = self.getforwarded(arg2)

        # If one side of the op is 0 the result is the other side.
        if v1.is_constant() and v1.getint() == 0:
            self.optimizer.replace(op, arg2)
        elif v2.is_constant() and v2.getint() == 0:
            self.optimizer.replace(op, arg1)
        else:
            # Synthesize the reverse op for optimize_default to reuse
            self.pure(op.getarg(0), rop.INT_SUB, op, op.getarg(1))
            self.pure(op.getarg(1), rop.INT_SUB, op, op.getarg(0))
            return op

    def optimize_INT_MUL(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))

        # If one side of the op is 1 the result is the other side.
        if v1.is_constant() and v1.op.getint() == 1:
            self.make_equal_to(op, v2)
        elif v2.is_constant() and v2.op.getint() == 1:
            self.make_equal_to(op, v1)
        elif (v1.is_constant() and v1.op.getint() == 0) or \
             (v2.is_constant() and v2.op.getint() == 0):
            self.make_constant_int(op, 0)
        else:
            for lhs, rhs in [(v1, v2), (v2, v1)]:
                if lhs.is_constant():
                    x = lhs.op.getint()
                    # x & (x - 1) == 0 is a quick test for power of 2
                    if x & (x - 1) == 0:
                        new_rhs = ConstInt(highest_bit(lhs.op.getint()))
                        xxx
                        op = op.copy_and_change(rop.INT_LSHIFT, args=[rhs.box, new_rhs])
                        break
            self.emit_operation(op)

    def optimize_UINT_FLOORDIV(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))

        if v2.is_constant() and v2.op.getint() == 1:
            self.make_equal_to(op, v1)
        else:
            self.emit_operation(op)

    def optimize_INT_LSHIFT(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))

        if v2.is_constant() and v2.op.getint() == 0:
            self.make_equal_to(op, v1)
        else:
            self.emit_operation(op)

    def optimize_INT_RSHIFT(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))

        if v2.is_constant() and v2.op.getint() == 0:
            self.make_equal_to(op, v1)
        else:
            self.emit_operation(op)

    def optimize_FLOAT_MUL(self, op):
        arg1 = op.getarg(0)
        arg2 = op.getarg(1)

        # Constant fold f0 * 1.0 and turn f0 * -1.0 into a FLOAT_NEG, these
        # work in all cases, including NaN and inf
        for lhs, rhs in [(arg1, arg2), (arg2, arg1)]:
            v1 = self.getvalue(lhs)

            if v1.is_constant():
                if v1.op.getfloat() == 1.0:
                    self.optimizer.replace(op, rhs)
                    return
                elif v1.op.getfloat() == -1.0:
                    new_op = create_resop_1(rop.FLOAT_NEG, 0.0, rhs)
                    self.optimizer.replace(op, new_op)
                    self.emit_operation(new_op)
                    return
        self.emit_operation(op)
        self.pure(op, rop.FLOAT_MUL, arg2, arg1)

    def optimize_FLOAT_NEG(self, op):
        self.emit_operation(op)
        self.pure(op.getarg(0), rop.FLOAT_NEG, op)

    def optimize_guard(self, op, constbox, emit_operation=True):
        value = self.getforwarded(op.getarg(0))
        if value.is_constant():
            if not value.same_constant(constbox):
                raise InvalidLoop('A GUARD_{VALUE,TRUE,FALSE} was proven to' +
                                  'always fail')
            return
        if emit_operation:
            return self.getforwarded(op)

    def postprocess_guard(self, op, constbox):
        value = self.getforwarded(op.getarg(0))
        self.optimizer.make_constant(value, constbox)
        self.optimizer.turned_constant(op.getarg(0))

    def postprocess_GUARD_VALUE(self, op):
        constbox = op.getarg(1)
        assert isinstance(constbox, Const)
        self.postprocess_guard(op, constbox)

    def postprocess_GUARD_TRUE(self, op):
        self.postprocess_guard(op, CONST_1)

    def postprocess_GUARD_FALSE(self, op):
        self.postprocess_guard(op, CONST_0)

    def optimize_GUARD_ISNULL(self, op):
        value = self.getvalue(op.getarg(0))
        if value.is_null():
            return
        elif value.is_nonnull():
            raise InvalidLoop('A GUARD_ISNULL was proven to always fail')
        self.emit_operation(op)
        value.make_constant(self.optimizer.cpu.ts.CONST_NULL)

    def optimize_GUARD_NONNULL(self, op):
        value = self.getforwarded(op.getarg(0))
        if value.is_nonnull():
            return
        elif value.is_null():
            raise InvalidLoop('A GUARD_NONNULL was proven to always fail')
        value.setknownnonnull(True)
        value.setlastguardpos(self.optimizer.getpos())
        return op

    def optimize_GUARD_VALUE(self, op):
        value = self.getforwarded(op.getarg(0))
        if value.getlastguardpos() != -1:
            xxx
            # there already has been a guard_nonnull or guard_class or
            # guard_nonnull_class on this value, which is rather silly.
            # replace the original guard with a guard_value
            old_guard_op = value.getlastguard()
            if old_guard_op.getopnum() != rop.GUARD_NONNULL:
                # This is only safe if the class of the guard_value matches the
                # class of the guard_*_class, otherwise the intermediate ops might
                # be executed with wrong classes.
                previous_classbox = value.get_constant_class(self.optimizer.cpu)            
                expected_classbox = self.optimizer.cpu.ts.cls_of_box(op.getarg(1))
                assert previous_classbox is not None
                assert expected_classbox is not None
                if not previous_classbox.same_constant(expected_classbox):
                    raise InvalidLoop('A GUARD_VALUE was proven to always fail')
            # replace the previous guard
            new_guard_op = create_resop_2(rop.GUARD_VALUE, None,
                                          old_guard_op.getarg(0),
                                          op.getarg(1))
            new_guard_op.set_extra("failargs",
                                   old_guard_op.get_extra("failargs"))
            descr = old_guard_op.getdescr()
            # hack, we assume there is just one reference to this descr,
            # so we can modify it
            assert isinstance(descr, compile.ResumeGuardDescr)
            descr.guard_opnum = rop.GUARD_VALUE
            descr.make_a_counter_per_value(new_guard_op)
            new_guard_op.setdescr(descr)
            op = new_guard_op
            self.optimizer.replace_op(value, new_guard_op)
            value.last_guard = None
            emit_operation = False
        else:
            emit_operation = True
        constbox = op.getarg(1)
        assert isinstance(constbox, Const)
        return self.optimize_guard(op, constbox, emit_operation=emit_operation)

    def optimize_GUARD_TRUE(self, op):
        return self.optimize_guard(op, CONST_1)

    def optimize_GUARD_FALSE(self, op):
        return self.optimize_guard(op, CONST_0)

    def optimize_RECORD_KNOWN_CLASS(self, op):
        value = self.getvalue(op.getarg(0))
        expectedclassbox = op.getarg(1)
        assert isinstance(expectedclassbox, Const)
        realclassbox = self.optimizer.get_constant_class(value)
        if realclassbox is not None:
            assert realclassbox.same_constant(expectedclassbox)
            return
        value.make_constant_class(expectedclassbox, None,
                                  self.optimizer.get_pos())

    def optimize_GUARD_CLASS(self, op):
        value = self.getforwarded(op.getarg(0))
        expectedclassbox = op.getarg(1)
        assert isinstance(expectedclassbox, Const)
        realclassbox = self.optimizer.get_constant_class(value)
        if realclassbox is not None:
            if realclassbox.same_constant(expectedclassbox):
                return
            raise InvalidLoop('A GUARD_CLASS was proven to always fail')
        if value.getlastguardpos() != -1:
            xxx
            # there already has been a guard_nonnull or guard_class or
            # guard_nonnull_class on this value.
            old_guard_op = value.last_guard
            if old_guard_op.getopnum() == rop.GUARD_NONNULL:
                # it was a guard_nonnull, which we replace with a
                # guard_nonnull_class.
                new_op = create_resop_2(rop.GUARD_NONNULL_CLASS,
                                        None, old_guard_op.getarg(0),
                                        op.getarg(1))
                descr = old_guard_op.getdescr()
                assert isinstance(descr, compile.ResumeGuardDescr)
                descr.guard_opnum = rop.GUARD_NONNULL_CLASS
                new_op.setdescr(descr)
                new_op.set_extra("failargs", old_guard_op.get_extra("failargs"))
                self.optimizer.replace_op(value, new_op)
                op = new_op
                return
            value.last_guard = None
        else:
            value.setlastguardpos(self.optimizer.get_pos())
        return op

    def postprocess_GUARD_CLASS(self, op):
        value = self.getforwarded(op.getarg(0))
        if value.is_constant():
            return
        expectedclassbox = op.getarg(1)
        assert isinstance(expectedclassbox, Const)
        value.setknownclass(expectedclassbox)

    def optimize_GUARD_NONNULL_CLASS(self, op):
        value = self.getvalue(op.getarg(0))
        if value.is_null():
            raise InvalidLoop('A GUARD_NONNULL_CLASS was proven to always ' +
                              'fail')
        self.optimize_GUARD_CLASS(op)

    def _new_optimize_call_loopinvariant(opnum):
        def optimize_CALL_LOOPINVARIANT(self, op):
            arg = op.getarg(0)
            # 'arg' must be a Const, because residual_call in codewriter
            # expects a compile-time constant
            assert isinstance(arg, Const)
            key = make_hashable_int(arg.getint())

            resop = self.loop_invariant_results.get(key, None)
            if resop is not None:
                self.optimizer.replace(op, resop)
                self.last_emitted_operation = REMOVED
                return
            # change the op to be a normal call, from the backend's point of view
            # there is no reason to have a separate operation for this
            self.loop_invariant_producer[key] = op
            op = self.optimizer.copy_and_change(op, opnum)
            self.emit_operation(op)
            self.loop_invariant_results[key] = op
        return optimize_CALL_LOOPINVARIANT
    optimize_CALL_LOOPINVARIANT_i = _new_optimize_call_loopinvariant(rop.CALL_i)
    optimize_CALL_LOOPINVARIANT_r = _new_optimize_call_loopinvariant(rop.CALL_r)
    optimize_CALL_LOOPINVARIANT_f = _new_optimize_call_loopinvariant(rop.CALL_f)
    optimize_CALL_LOOPINVARIANT_v = _new_optimize_call_loopinvariant(rop.CALL_v)

    def _optimize_nullness(self, op, arg, expect_nonnull):
        value = self.getforwarded(arg)
        if value.is_nonnull():
            self.make_constant_int(op, expect_nonnull)
        elif value.is_null():
            self.make_constant_int(op, not expect_nonnull)
        else:
            return op

    def optimize_INT_IS_TRUE(self, op):
        if op.getarg(0).returns_bool_result():
            self.optimizer.replace(op, op.getarg(0))
            return
        return self._optimize_nullness(op, op.getarg(0), True)

    def optimize_INT_IS_ZERO(self, op):
        return self._optimize_nullness(op, op.getarg(0), False)

    def _optimize_oois_ooisnot(self, op, expect_isnot, instance):
        value0 = self.getvalue(op.getarg(0))
        value1 = self.getvalue(op.getarg(1))
        if value0.is_virtual():
            if value1.is_virtual():
                intres = (value0 is value1) ^ expect_isnot
                self.make_constant_int(op, intres)
            else:
                self.make_constant_int(op, expect_isnot)
        elif value1.is_virtual():
            self.make_constant_int(op, expect_isnot)
        elif value1.is_null():
            self._optimize_nullness(op, op.getarg(0), expect_isnot)
        elif value0.is_null():
            self._optimize_nullness(op, op.getarg(1), expect_isnot)
        elif value0 is value1:
            self.make_constant_int(op, not expect_isnot)
        else:
            if instance:
                cls0 = value0.get_constant_class(self.optimizer.cpu)
                if cls0 is not None:
                    cls1 = value1.get_constant_class(self.optimizer.cpu)
                    if cls1 is not None and not cls0.same_constant(cls1):
                        # cannot be the same object, as we know that their
                        # class is different
                        self.make_constant_int(op, expect_isnot)
                        return
            self.emit_operation(op)

    def optimize_PTR_EQ(self, op):
        self._optimize_oois_ooisnot(op, False, False)

    def optimize_PTR_NE(self, op):
        self._optimize_oois_ooisnot(op, True, False)

    def optimize_INSTANCE_PTR_EQ(self, op):
        self._optimize_oois_ooisnot(op, False, True)

    def optimize_INSTANCE_PTR_NE(self, op):
        self._optimize_oois_ooisnot(op, True, True)

##    def optimize_INSTANCEOF(self, op):
##        value = self.getvalue(op.args[0])
##        realclassbox = value.get_constant_class(self.optimizer.cpu)
##        if realclassbox is not None:
##            checkclassbox = self.optimizer.cpu.typedescr2classbox(op.descr)
##            result = self.optimizer.cpu.ts.subclassOf(self.optimizer.cpu,
##                                                      realclassbox,
##                                                      checkclassbox)
##            self.make_constant_int(op, result)
##            return
##        self.emit_operation(op)

    def optimize_CALL_i(self, op):
        # dispatch based on 'oopspecindex' to a method that handles
        # specifically the given oopspec call.  For non-oopspec calls,
        # oopspecindex is just zero.
        effectinfo = op.getdescr().get_extra_info()
        oopspecindex = effectinfo.oopspecindex
        if oopspecindex == EffectInfo.OS_ARRAYCOPY:
            if self._optimize_CALL_ARRAYCOPY(op):
                return
        self.emit_operation(op)
    optimize_CALL_p = optimize_CALL_i
    optimize_CALL_f = optimize_CALL_i
    optimize_CALL_v = optimize_CALL_i

    def _optimize_CALL_ARRAYCOPY(self, op):
        source_value = self.getvalue(op.getarg(1))
        dest_value = self.getvalue(op.getarg(2))
        source_start_box = self.get_constant_box(op.getarg(3))
        dest_start_box = self.get_constant_box(op.getarg(4))
        length = self.get_constant_box(op.getarg(5))
        if (source_value.is_virtual() and source_start_box and dest_start_box
            and length and (dest_value.is_virtual() or length.getint() <= 8)):
            from pypy.jit.metainterp.optimizeopt.virtualize import VArrayValue
            assert isinstance(source_value, VArrayValue)
            source_start = source_start_box.getint()
            dest_start = dest_start_box.getint()
            for index in range(length.getint()):
                val = source_value.getitem(index + source_start)
                if dest_value.is_virtual():
                    dest_value.setitem(index + dest_start, val)
                else:
                    newop = ResOperation(rop.SETARRAYITEM_GC,
                                         [op.getarg(2),
                                          ConstInt(index + dest_start),
                                          val.get_key_box()], None,
                                         descr=source_value.arraydescr)
                    self.emit_operation(newop)
            return True
        if length and length.getint() == 0:
            return True # 0-length arraycopy
        return False

    def optimize_CALL_PURE_i(self, op):
        # Note that we can safely read the contents of boxes here, because
        # we compare the value of unoptimized op (which is correct) with
        # proven constants. In the rare case where proven constants are
        # different, we just emit it (to be precise we emit CALL_x, but
        # it's being done by someone else)
        for i in range(op.numargs()):
            arg = op.getarg(i)
            const = self.get_constant_box(arg)
            if const is None or not const.eq_value(arg):
                break
        else:
            self.make_constant(op, op.constbox())
            self.last_emitted_operation = REMOVED
            return
        self.emit_operation(op)
    optimize_CALL_PURE_f = optimize_CALL_PURE_i
    optimize_CALL_PURE_p = optimize_CALL_PURE_i
    optimize_CALL_PURE_v = optimize_CALL_PURE_i

    def optimize_GUARD_NO_EXCEPTION(self, op):
        if self.last_emitted_operation is REMOVED:
            # it was a CALL_PURE or a CALL_LOOPINVARIANT that was killed;
            # so we also kill the following GUARD_NO_EXCEPTION
            return
        self.emit_operation(op)

    def optimize_INT_FLOORDIV(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))

        if v2.is_constant() and v2.op.getint() == 1:
            self.make_equal_to(op, v1)
            return
        elif v1.is_constant() and v1.op.getint() == 0:
            self.make_constant_int(op, 0)
            return
        if v1.intbound.known_ge(IntBound(0, 0)) and v2.is_constant():
            val = v2.op.getint()
            if val & (val - 1) == 0 and val > 0: # val == 2**shift
                xxx
                op = op.copy_and_change(rop.INT_RSHIFT,
                                        args = [op.getarg(0), ConstInt(highest_bit(val))])
        self.emit_operation(op)

    def optimize_CAST_PTR_TO_INT(self, op):
        xxx
        self.pure(rop.CAST_INT_TO_PTR, [op], op.getarg(0))
        self.emit_operation(op)

    def optimize_CAST_INT_TO_PTR(self, op):
        xxx
        self.pure(rop.CAST_PTR_TO_INT, [op], op.getarg(0))
        self.emit_operation(op)

    def optimize_SAME_AS_i(self, op):
        self.optimizer.replace(op, op.getarg(0))
    optimize_SAME_AS_r = optimize_SAME_AS_i
    optimize_SAME_AS_f = optimize_SAME_AS_i

#dispatch_opt = make_dispatcher_method(OptRewrite, 'optimize_',
#        default=OptRewrite.emit_operation)
#optimize_guards = _findall(OptRewrite, 'optimize_', 'GUARD')
