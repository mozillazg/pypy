
""" This file implements the entry point to optimizations - the Optimizer.
optimizations are dispatched in order they're passed and for each operation
optimize_XYZ where XYZ is the name of resop is called. The method can choose
to return None (optimized away) or return the operation to emit.
it'll be passed onto the next one.

Each resop can have an extra attribute _forwarded, which points to
a new version of the same resop. It can be a mutable resop (from optmodel)
or a constant.
"""

from pypy.jit.metainterp import jitprof, resume, compile
from pypy.jit.metainterp.executor import execute_nonspec
from pypy.jit.metainterp.resoperation import REF, INT, create_resop_1
from pypy.jit.metainterp.optimizeopt.intutils import IntBound, IntUnbounded, \
                                                     ImmutableIntUnbounded, \
                                                     IntLowerBound, MININT, MAXINT
from pypy.jit.metainterp.optimizeopt.util import make_dispatcher_method
from pypy.jit.metainterp.resoperation import rop, AbstractResOp, opgroups,\
     Const, ConstInt, opname
from pypy.jit.metainterp.typesystem import llhelper
from pypy.rlib.objectmodel import specialize
from pypy.tool.pairtype import extendabletype

LEVEL_UNKNOWN    = '\x00'
LEVEL_NONNULL    = '\x01'
LEVEL_KNOWNCLASS = '\x02'     # might also mean KNOWNARRAYDESCR, for arrays
LEVEL_CONSTANT   = '\x03'

MODE_ARRAY   = '\x00'
MODE_STR     = '\x01'
MODE_UNICODE = '\x02'

class LenBound(object):
    def __init__(self, mode, descr, bound):
        self.mode = mode
        self.descr = descr
        self.bound = bound

    def clone(self):
        return LenBound(self.mode, self.descr, self.bound.clone())

class OptValue(object):
    _attrs_ = ('known_class', 'last_guard', 'level', 'intbound', 'lenbound', 'is_bool_box')

    __metaclass__ = extendabletype
    
    last_guard = None
    level = LEVEL_UNKNOWN
    known_class = None
    intbound = ImmutableIntUnbounded()
    lenbound = None

    def __init__(self, op, level=None, known_class=None, intbound=None):
        self.op = op
        if level is not None:
            self.level = level
        self.known_class = known_class
        if intbound:
            self.intbound = intbound
        else:
            if op is not None and op.type == INT:
                self.intbound = IntBound(MININT, MAXINT)
            else:
                self.intbound = IntUnbounded()

        if isinstance(op, Const):
            self.make_constant(op)
        # invariant: box is a Const if and only if level == LEVEL_CONSTANT

    def make_len_gt(self, mode, descr, val):
        if self.lenbound:
            assert self.lenbound.mode == mode
            assert self.lenbound.descr == descr
            self.lenbound.bound.make_gt(IntBound(val, val))
        else:
            self.lenbound = LenBound(mode, descr, IntLowerBound(val + 1))

    def make_guards(self, box):
        guards = []
        if self.level == LEVEL_CONSTANT:
            op = ResOperation(rop.GUARD_VALUE, [box, self.box], None)
            guards.append(op)
        elif self.level == LEVEL_KNOWNCLASS:
            op = ResOperation(rop.GUARD_NONNULL, [box], None)
            guards.append(op)
            op = ResOperation(rop.GUARD_CLASS, [box, self.known_class], None)
            guards.append(op)
        else:
            if self.level == LEVEL_NONNULL:
                op = ResOperation(rop.GUARD_NONNULL, [box], None)
                guards.append(op)
            self.intbound.make_guards(box, guards)
            if self.lenbound:
                lenbox = BoxInt()
                if self.lenbound.mode == MODE_ARRAY:
                    op = ResOperation(rop.ARRAYLEN_GC, [box], lenbox, self.lenbound.descr)
                elif self.lenbound.mode == MODE_STR:
                    op = ResOperation(rop.STRLEN, [box], lenbox, self.lenbound.descr)
                elif self.lenbound.mode == MODE_UNICODE:
                    op = ResOperation(rop.UNICODELEN, [box], lenbox, self.lenbound.descr)
                else:
                    debug_print("Unknown lenbound mode")
                    assert False
                guards.append(op)
                self.lenbound.bound.make_guards(lenbox, guards)
        return guards

    def import_from(self, other, optimizer):
        if self.level == LEVEL_CONSTANT:
            assert other.level == LEVEL_CONSTANT
            assert other.box.same_constant(self.box)
            return
        assert self.level <= LEVEL_NONNULL
        if other.level == LEVEL_CONSTANT:
            self.make_constant(other.get_key_box())
            optimizer.turned_constant(self)
        elif other.level == LEVEL_KNOWNCLASS:
            self.make_constant_class(other.known_class, None)
        else:
            if other.level == LEVEL_NONNULL:
                self.ensure_nonnull()
            self.intbound.intersect(other.intbound)
            if other.lenbound:
                if self.lenbound:
                    assert other.lenbound.mode == self.lenbound.mode
                    assert other.lenbound.descr == self.lenbound.descr
                    self.lenbound.bound.intersect(other.lenbound.bound)
                else:
                    self.lenbound = other.lenbound.clone()


    def force_box(self, optforce):
        return self.op

    def get_key_box(self):
        return self.op

    def force_at_end_of_preamble(self, already_forced, optforce):
        return self

    def get_args_for_fail(self, modifier):
        pass

    def make_virtual_info(self, modifier, fieldnums):
        #raise NotImplementedError # should not be called on this level
        assert fieldnums is None
        return modifier.make_not_virtual(self)

    def is_constant(self):
        return self.level == LEVEL_CONSTANT

    def is_null(self):
        if self.is_constant():
            op = self.op
            assert isinstance(op, Const)
            return not op.nonnull()
        return False

    def same_value(self, other):
        if not other:
            return False
        if self.is_constant() and other.is_constant():
            return self.box.same_constant(other.box)
        return self is other

    def make_constant(self, constbox):
        """Replace 'self.box' with a Const box."""
        assert isinstance(constbox, Const)
        self.op = constbox
        self.level = LEVEL_CONSTANT

        if isinstance(constbox, ConstInt):
            val = constbox.getint()
            self.intbound = IntBound(val, val)
        else:
            self.intbound = IntUnbounded()

    def get_constant_class(self, cpu):
        xxx
        level = self.level
        if level == LEVEL_KNOWNCLASS:
            return self.known_class
        elif level == LEVEL_CONSTANT:
            return cpu.ts.cls_of_box(self.op)
        else:
            return None

    def make_constant_class(self, classbox, guardop, index):
        assert self.level < LEVEL_KNOWNCLASS
        self.known_class = classbox
        self.level = LEVEL_KNOWNCLASS
        assert self.last_guard is None
        self.last_guard = guardop
        self.last_guard_pos = index

    def make_nonnull(self, guardop, index):
        assert self.level < LEVEL_NONNULL
        self.level = LEVEL_NONNULL
        assert self.last_guard is None
        self.last_guard = guardop
        self.last_guard_pos = index

    def is_nonnull(self):
        level = self.level
        if level == LEVEL_NONNULL or level == LEVEL_KNOWNCLASS:
            return True
        elif level == LEVEL_CONSTANT:
            op = self.op
            assert isinstance(op, Const)
            return op.nonnull()
        elif self.intbound:
            if self.intbound.known_gt(IntBound(0, 0)) or \
               self.intbound.known_lt(IntBound(0, 0)):
                return True
            else:
                return False
        else:
            return False

    def ensure_nonnull(self):
        if self.level < LEVEL_NONNULL:
            self.level = LEVEL_NONNULL

    def is_virtual(self):
        # Don't check this with 'isinstance(_, VirtualValue)'!
        # Even if it is a VirtualValue, the 'box' can be non-None,
        # meaning it has been forced.
        return False

    def is_forced_virtual(self):
        return False

    def getfield(self, ofs, default):
        raise NotImplementedError

    def setfield(self, ofs, value):
        raise NotImplementedError

    def getlength(self):
        raise NotImplementedError

    def getitem(self, index):
        raise NotImplementedError

    def setitem(self, index, value):
        raise NotImplementedError

    def getinteriorfield(self, index, ofs, default):
        raise NotImplementedError

    def setinteriorfield(self, index, ofs, value):
        raise NotImplementedError

    def __repr__(self):
        if self.level == LEVEL_UNKNOWN:
            return '<Opt %r>' % self.op
        if self.level == LEVEL_NONNULL:
            return '<OptNonNull %r>' % self.op
        if self.level == LEVEL_KNOWNCLASS:
            return '<OptKnownClass (%s) %r>' % (self.known_class, self.op)
        assert self.level == LEVEL_CONSTANT
        return '<OptConst %r>' % self.op

CONST_0      = ConstInt(0)
CONST_1      = ConstInt(1)
#CVAL_ZERO    = ConstantValue(CONST_0)
#CVAL_ZERO_FLOAT = ConstantValue(ConstFloat(longlong.getfloatstorage(0.0)))
#CVAL_NULLREF = ConstantValue(llhelper.CONST_NULL)
CONST_NULL = llhelper.CONST_NULL
#llhelper.CVAL_NULLREF = CVAL_NULLREF
REMOVED = AbstractResOp()


class Optimization(object):
    optimize_default = None

    def __init__(self):
        pass # make rpython happy

    #def propagate_forward(self, op):
    #    raise NotImplementedError

    #def emit_operation(self, op):
    #    self.last_emitted_operation = op
    #    self.next_optimization.propagate_forward(op)

    def optimize_operation(self, op):
        name = 'optimize_' + opname[op.getopnum()]
        next_func = getattr(self, name, self.optimize_default)
        if next_func is not None:
            op = next_func(op)
            if op is None:
                return
            else:
                self.last_emitted_operation = op
        return op

    # FIXME: Move some of these here?
    def getforwarded(self, op):
        return self.optimizer.getforwarded(op)

    def setvalue(self, box, value):
        self.optimizer.setvalue(box, value)

    def make_constant(self, box, constbox):
        return self.optimizer.make_constant(box, constbox)

    def make_constant_int(self, box, intconst):
        return self.optimizer.make_constant_int(box, intconst)

    def replace(self, box, value):
        return self.optimizer.replace(box, value)

    def get_constant_op(self, op):
        return self.optimizer.get_constant_op(op)

    def new_box(self, fieldofs):
        return self.optimizer.new_box(fieldofs)

    def new_const(self, fieldofs):
        return self.optimizer.new_const(fieldofs)

    def new_box_item(self, arraydescr):
        return self.optimizer.new_box_item(arraydescr)

    def new_const_item(self, arraydescr):
        return self.optimizer.new_const_item(arraydescr)

    @specialize.arg(1)
    def pure(self, oldop, opnum, arg0, arg1=None):
        if self.optimizer.optpure:
            self.optimizer.optpure.pure(oldop, opnum, arg0, arg1)

    def has_pure_result(self, op_key):
        if self.optimizer.optpure:
            return self.optimizer.optpure.has_pure_result(op_key)
        return False

    def get_pure_result(self, key):
        if self.optimizer.optpure:
            return self.optimizer.optpure.get_pure_result(key)
        return None

    def setup(self):
        pass

    def turned_constant(self, value):
        pass

    def force_at_end_of_preamble(self):
        pass

    # It is too late to force stuff here, it must be done in force_at_end_of_preamble
    def new(self):
        raise NotImplementedError

    # Called after last operation has been propagated to flush out any posponed ops
    def flush(self):
        pass

    def produce_potential_short_preamble_ops(self, potential_ops):
        pass

    def forget_numberings(self, box):
        self.optimizer.forget_numberings(box)


class Optimizer(Optimization):

    def __init__(self, jitdriver_sd, metainterp_sd, loop, optimizations=None):
        self.jitdriver_sd = jitdriver_sd
        self.metainterp_sd = metainterp_sd
        self.cpu = metainterp_sd.cpu
        self.loop = loop
        self.interned_refs = self.cpu.ts.new_ref_dict()
        self.resumedata_memo = resume.ResumeDataLoopMemo(metainterp_sd)
        self.pendingfields = []
        self.quasi_immutable_deps = None
        self.opaque_pointers = {}
        self._newoperations = []
        self.optimizer = self
        self.optpure = None
        self.optearlyforce = None
        if loop is not None:
            self.call_pure_results = loop.call_pure_results

        self.optimizations = optimizations
        for opt in optimizations:
            opt.optimizer = self
        self.setup()

    def force_at_end_of_preamble(self):
        for o in self.optimizations:
            o.force_at_end_of_preamble()

    def flush(self):
        for o in self.optimizations:
            o.flush()

    def new(self):
        new = Optimizer(self.metainterp_sd, self.loop)
        return self._new(new)

    def _new(self, new):
        optimizations = [o.new() for o in self.optimizations]
        new.set_optimizations(optimizations)
        new.quasi_immutable_deps = self.quasi_immutable_deps
        return new

    def produce_potential_short_preamble_ops(self, sb):
        for opt in self.optimizations:
            opt.produce_potential_short_preamble_ops(sb)

    def turned_constant(self, value):
        for o in self.optimizations:
            o.turned_constant(value)

    def forget_numberings(self, virtualbox):
        self.metainterp_sd.profiler.count(jitprof.Counters.OPT_FORCINGS)
        self.resumedata_memo.forget_numberings(virtualbox)

    def getforwarded(self, op):
        if op.is_constant():
            if op.type == REF:
                if not op.getref_base():
                    return CONST_NULL
                try:
                    return self.interned_refs[op.getref_base()]
                except KeyError:
                    self.interned_refs[op.getref_base()] = op
                    return op
            return op
        value = op._forwarded
        if value is None:
            value = op.make_forwarded_copy()
        else:
            if value._forwarded:
                while value._forwarded:
                    value = value._forwarded
                to_patch = op
                while to_patch._forwarded:
                    next = to_patch._forwarded
                    to_patch._forwarded = value
                    to_patch = next
        #self.ensure_imported(value)
        return value

    def setvalue(self, box, value):
        xxx
        assert not box.is_constant()
        assert not box.has_extra("optimize_value")
        box.set_extra("optimize_value", value)

    def copy_op_if_modified_by_optimization(self, op):
        xxxx
        new_op = op.copy_if_modified_by_optimization(self)
        if new_op is not op:
            self.replace(op, new_op)
        return new_op

    # XXX some RPython magic needed
    def copy_and_change(self, op, *args, **kwds):
        xxx
        new_op = op.copy_and_change(*args, **kwds)
        if new_op is not op:
            self.replace(op, new_op)
        return new_op

    def ensure_imported(self, value):
        pass

    @specialize.argtype(0)
    def get_constant_op(self, op):
        op = self.getforwarded(op)
        if isinstance(op, Const):
            return op

    def get_newoperations(self):
        self.flush()
        return self._newoperations

    def clear_newoperations(self):
        self._newoperations = []

    def make_constant(self, box, constbox):
        self.getvalue(box).make_constant(constbox)

    def make_constant_int(self, box, intvalue):
        self.getvalue(box).make_constant(ConstInt(intvalue))

    def new_ptr_box(self):
        return self.cpu.ts.BoxRef()

    def new_box(self, fieldofs):
        if fieldofs.is_pointer_field():
            return self.new_ptr_box()
        elif fieldofs.is_float_field():
            return BoxFloat()
        else:
            return BoxInt()

    def new_const(self, fieldofs):
        if fieldofs.is_pointer_field():
            return self.cpu.ts.CVAL_NULLREF
        elif fieldofs.is_float_field():
            return CVAL_ZERO_FLOAT
        else:
            return CVAL_ZERO

    def new_box_item(self, arraydescr):
        if arraydescr.is_array_of_pointers():
            return self.new_ptr_box()
        elif arraydescr.is_array_of_floats():
            return BoxFloat()
        else:
            return BoxInt()

    def new_const_item(self, arraydescr):
        if arraydescr.is_array_of_pointers():
            return self.cpu.ts.CVAL_NULLREF
        elif arraydescr.is_array_of_floats():
            return CVAL_ZERO_FLOAT
        else:
            return CVAL_ZERO

    def propagate_all_forward(self, clear=True):
        if clear:
            self.clear_newoperations()
        i = 0
        while i < len(self.loop.operations):
            op = self.loop.operations[i]
            for opt in self.optimizations:
                op = opt.optimize_operation(op)
                if op is None:
                    break
            else:
                self.emit_operation(op)
            i += 1
        self.loop.operations = self.get_newoperations()
        self.loop.quasi_immutable_deps = self.quasi_immutable_deps
        # accumulate counters
        self.resumedata_memo.update_counters(self.metainterp_sd.profiler)

    def send_extra_operation(self, op):
        self.first_optimization.propagate_forward(op)

    def propagate_forward(self, op):
        dispatch_opt(self, op)

    def emit_operation(self, op):
        if op.returns_bool_result():
            self.getvalue(op).is_bool_box = True
        self._emit_operation(op)

    @specialize.argtype(0)
    def _emit_operation(self, op):
        assert op.getopnum() not in opgroups.CALL_PURE
        assert not op._forwarded
        if isinstance(op, Const):
            return
        self.metainterp_sd.profiler.count(jitprof.Counters.OPT_OPS)
        if op.is_guard():
            self.metainterp_sd.profiler.count(jitprof.Counters.OPT_GUARDS)
            op = self.store_final_boxes_in_guard(op)
        elif op.can_raise():
            self.exception_might_have_happened = True
        elif op.getopnum() == rop.FINISH:
            op = self.store_final_boxes_in_guard(op)
        self._newoperations.append(op)

    def store_final_boxes_in_guard(self, op):
        return # XXX we disable it for tests
        assert op.getdescr() is None
        descr = op.invent_descr(self.jitdriver_sd, self.metainterp_sd)
        op.setdescr(descr)
        modifier = resume.ResumeDataVirtualAdder(descr, self.resumedata_memo)
        try:
            newboxes = modifier.finish(self, self.pendingfields)
            if len(newboxes) > self.metainterp_sd.options.failargs_limit:
                raise resume.TagOverflow
        except resume.TagOverflow:
            raise compile.giveup()
        descr.store_final_boxes(op, newboxes)
        #
        if op.getopnum() == rop.GUARD_VALUE:
            if self.getvalue(op.getarg(0)).is_bool_box:
                # Hack: turn guard_value(bool) into guard_true/guard_false.
                # This is done after the operation is emitted to let
                # store_final_boxes_in_guard set the guard_opnum field of the
                # descr to the original rop.GUARD_VALUE.
                constvalue = op.getarg(1).getint()
                if constvalue == 0:
                    newop = create_resop_1(rop.GUARD_FALSE, None,
                                           op.getarg(0))
                elif constvalue == 1: 
                    newop = create_resop_1(rop.GUARD_TRUE, None,
                                           op.getarg(0))
                else:
                    raise AssertionError("uh?")
                newop.set_extra("failargs", op.get_extra("failargs"))
                self.replace(op, newop)
                return newop
            else:
                # a real GUARD_VALUE.  Make it use one counter per value.
                descr.make_a_counter_per_value(op)
        return op

    def optimize_default(self, op):
        self.emit_operation(op)

    def get_pos(self):
        return len(self._newoperations)

    def replace_op(self, value, new_guard_op):
        assert self._newoperations[value.last_guard_pos] is value.last_guard
        self._newoperations[value.last_guard_pos] = new_guard_op

    def constant_fold(self, op):
        argboxes = [self.get_constant_box(op.getarg(i))
                    for i in range(op.numargs())]
        resbox = execute_nonspec(self.cpu, None,
                                 op.getopnum(), argboxes, op.getdescr())
        return resbox.constbox()

    #def optimize_GUARD_NO_OVERFLOW(self, op):
    #    # otherwise the default optimizer will clear fields, which is unwanted
    #    # in this case
    #    self.emit_operation(op)
    # FIXME: Is this still needed?

    def optimize_DEBUG_MERGE_POINT(self, op):
        self.emit_operation(op)

    def optimize_GETARRAYITEM_GC_PURE_i(self, op):
        indexvalue = self.getvalue(op.getarg(1))
        if indexvalue.is_constant():
            arrayvalue = self.getvalue(op.getarg(0))
            arrayvalue.make_len_gt(MODE_ARRAY, op.getdescr(),
                                   indexvalue.op.getint())
        self.optimize_default(op)
    optimize_GETARRAYITEM_GC_PURE_f = optimize_GETARRAYITEM_GC_PURE_i
    optimize_GETARRAYITEM_GC_PURE_p = optimize_GETARRAYITEM_GC_PURE_i    

    def optimize_STRGETITEM(self, op):
        indexvalue = self.getvalue(op.getarg(1))
        if indexvalue.is_constant():
            arrayvalue = self.getvalue(op.getarg(0))
            arrayvalue.make_len_gt(MODE_STR, op.getdescr(), indexvalue.op.getint())
        self.optimize_default(op)

    def optimize_UNICODEGETITEM(self, op):
        indexvalue = self.getvalue(op.getarg(1))
        if indexvalue.is_constant():
            arrayvalue = self.getvalue(op.getarg(0))
            arrayvalue.make_len_gt(MODE_UNICODE, op.getdescr(), indexvalue.op.getint())
        self.optimize_default(op)

    # These are typically removed already by OptRewrite, but it can be
    # dissabled and unrolling emits some SAME_AS ops to setup the
    # optimizier state. These needs to always be optimized out.
    def optimize_SAME_AS_i(self, op):
        self.make_equal_to(op.result, self.getvalue(op.getarg(0)))
    optimize_SAME_AS_f = optimize_SAME_AS_i
    optimize_SAME_AS_r = optimize_SAME_AS_i

    def optimize_MARK_OPAQUE_PTR(self, op):
        value = self.getvalue(op.getarg(0))
        self.optimizer.opaque_pointers[value] = True

dispatch_opt = make_dispatcher_method(Optimizer, 'optimize_',
        default=Optimizer.optimize_default)



