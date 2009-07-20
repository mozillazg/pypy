from pypy.jit.metainterp.history import Box, BoxInt, BoxPtr, BoxObj
from pypy.jit.metainterp.history import Const, ConstInt, ConstPtr, ConstObj
from pypy.jit.metainterp.resoperation import rop, ResOperation
from pypy.jit.metainterp.specnode import SpecNode
from pypy.jit.metainterp.specnode import VirtualInstanceSpecNode
from pypy.jit.metainterp.optimizeutil import av_newdict, _findall
from pypy.rlib.objectmodel import we_are_translated


def optimize(cpu, loop):
    """Optimize loop.operations to make it match the input of loop.specnodes
    and to remove internal overheadish operations.  Note that loop.specnodes
    must be applicable to the loop; you will probably get an AssertionError
    if not.
    """
    optimizer = Optimizer(cpu, loop)
    optimizer.setup_virtuals()
    optimizer.propagate_forward()

# ____________________________________________________________

LEVEL_UNKNOWN    = 0
LEVEL_NONNULL    = 1
LEVEL_KNOWNCLASS = 2
LEVEL_CONSTANT   = 3


class InstanceValue(object):
    level = LEVEL_UNKNOWN

    def __init__(self, box):
        self.box = box
        if isinstance(box, Const):
            self.level = LEVEL_CONSTANT

    def force_box(self):
        return self.box

    def is_constant(self):
        return self.level == LEVEL_CONSTANT

    def is_null(self):
        return self.is_constant() and not self.box.nonnull()

    def make_constant(self):
        """Mark 'self' as actually representing a Const value."""
        self.box = self.force_box().constbox()
        self.level = LEVEL_CONSTANT

    def has_constant_class(self):
        return self.level >= LEVEL_KNOWNCLASS

    def make_constant_class(self):
        if self.level < LEVEL_KNOWNCLASS:
            self.level = LEVEL_KNOWNCLASS

    def is_nonnull(self):
        level = self.level
        if level == LEVEL_NONNULL or level == LEVEL_KNOWNCLASS:
            return True
        elif level == LEVEL_CONSTANT:
            return self.box.nonnull()
        else:
            return False

    def make_nonnull(self):
        if self.level < LEVEL_NONNULL:
            self.level = LEVEL_NONNULL

    def is_virtual(self):
        return self.box is None


class ConstantValue(InstanceValue):
    level = LEVEL_CONSTANT

    def __init__(self, box):
        self.box = box

CVAL_ZERO    = ConstantValue(ConstInt(0))
CVAL_NULLPTR = ConstantValue(ConstPtr(ConstPtr.value))
CVAL_NULLOBJ = ConstantValue(ConstObj(ConstObj.value))


class VirtualValue(InstanceValue):
    box = None
    level = LEVEL_KNOWNCLASS

    def __init__(self, optimizer):
        self.optimizer = optimizer
        self._fields = av_newdict()

    def getfield(self, ofs):
        return self._fields[ofs]

    def getfield_default(self, ofs, default):
        return self._fields.get(ofs, default)

    def setfield(self, ofs, fieldvalue):
        self._fields[ofs] = fieldvalue

    def force_box(self):
        if self.box is None:
            optimizer = self.optimizer
            import py; py.test.skip("in-progress")
        return self.box


class __extend__(SpecNode):
    def setup_virtual_node(self, optimizer, box, newinputargs):
        newinputargs.append(box)
    def teardown_virtual_node(self, optimizer, value, newexitargs):
        newexitargs.append(value.force_box())

class __extend__(VirtualInstanceSpecNode):
    def setup_virtual_node(self, optimizer, box, newinputargs):
        vvalue = optimizer.make_virtual(box)
        for ofs, subspecnode in self.fields:
            subbox = optimizer.new_box(ofs)
            vvalue.setfield(ofs, optimizer.getvalue(subbox))
            subspecnode.setup_virtual_node(optimizer, subbox, newinputargs)
    def teardown_virtual_node(self, optimizer, value, newexitargs):
        assert value.is_virtual()
        for ofs, subspecnode in self.fields:
            subvalue = value.getfield_default(ofs, optimizer.new_const(ofs))
            subspecnode.teardown_virtual_node(optimizer, subvalue, newexitargs)


class Optimizer(object):

    def __init__(self, cpu, loop):
        self.cpu = cpu
        self.loop = loop
        self.values = {}

    def getvalue(self, box):
        try:
            value = self.values[box]
        except KeyError:
            value = self.values[box] = InstanceValue(box)
        return value

    def is_constant(self, box):
        if isinstance(box, Const):
            return True
        try:
            return self.values[box].is_constant()
        except KeyError:
            return False

    def make_equal_to(self, box, value):
        assert box not in self.values
        self.values[box] = value

    def make_constant(self, box):
        self.make_equal_to(box, ConstantValue(box.constbox()))

    def known_nonnull(self, box):
        return self.getvalue(box).is_nonnull()

    def make_virtual(self, box):
        vvalue = VirtualValue(self)
        self.make_equal_to(box, vvalue)
        return vvalue

    def new_box(self, fieldofs):
        if fieldofs.is_pointer_field():
            if not self.cpu.is_oo:
                return BoxPtr()
            else:
                return BoxObj()
        else:
            return BoxInt()

    def new_const(self, fieldofs):
        if fieldofs.is_pointer_field():
            if not self.cpu.is_oo:
                return CVAL_NULLPTR
            else:
                return CVAL_NULLOBJ
        else:
            return CVAL_ZERO

    # ----------

    def setup_virtuals(self):
        inputargs = self.loop.inputargs
        specnodes = self.loop.specnodes
        assert len(inputargs) == len(specnodes)
        newinputargs = []
        for i in range(len(inputargs)):
            specnodes[i].setup_virtual_node(self, inputargs[i], newinputargs)
        self.loop.inputargs = newinputargs

    # ----------

    def propagate_forward(self):
        self.newoperations = []
        for op in self.loop.operations:
            opnum = op.opnum
            for value, func in optimize_ops:
                if opnum == value:
                    func(self, op)
                    break
            else:
                self.optimize_default(op)
        self.loop.operations = self.newoperations

    def emit_operation(self, op, must_clone=True):
        for i in range(len(op.args)):
            arg = op.args[i]
            if arg in self.values:
                box = self.values[arg].force_box()
                if box is not arg:
                    if must_clone:
                        op = op.clone()
                        must_clone = False
                    op.args[i] = box
        self.newoperations.append(op)

    def optimize_default(self, op):
        if op.is_always_pure():
            for arg in op.args:
                if not self.is_constant(arg):
                    break
            else:
                # all constant arguments: constant-fold away
                self.make_constant(op.result)
                return
        # otherwise, the operation remains
        self.emit_operation(op)

    def optimize_JUMP(self, op):
        orgop = self.loop.operations[-1]
        exitargs = []
        specnodes = orgop.jump_target.specnodes
        assert len(op.args) == len(specnodes)
        for i in range(len(specnodes)):
            value = self.getvalue(op.args[i])
            specnodes[i].teardown_virtual_node(self, value, exitargs)
        op = op.clone()
        op.args = exitargs
        self.emit_operation(op, must_clone=False)

    def optimize_guard(self, op):
        value = self.getvalue(op.args[0])
        if value.is_constant():
            return
        self.emit_operation(op)
        value.make_constant()

    def optimize_GUARD_VALUE(self, op):
        assert isinstance(op.args[1], Const)
        self.optimize_guard(op)

    def optimize_GUARD_TRUE(self, op):
        assert op.args[0].getint()
        self.optimize_guard(op)

    def optimize_GUARD_FALSE(self, op):
        assert not op.args[0].getint()
        self.optimize_guard(op)

    def optimize_GUARD_CLASS(self, op):
        # XXX should probably assert that the class is right
        value = self.getvalue(op.args[0])
        if value.has_constant_class():
            return
        self.emit_operation(op)
        value.make_constant_class()

    def optimize_OONONNULL(self, op):
        if self.known_nonnull(op.args[0]):
            assert op.result.getint() == 1
            self.make_constant(op.result)
        else:
            self.optimize_default(op)

    def optimize_OOISNULL(self, op):
        if self.known_nonnull(op.args[0]):
            assert op.result.getint() == 0
            self.make_constant(op.result)
        else:
            self.optimize_default(op)

    def optimize_OOISNOT(self, op):
        value0 = self.getvalue(op.args[0])
        value1 = self.getvalue(op.args[1])
        if value0.is_virtual() or value1.is_virtual():
            self.make_constant(op.result)
        elif value1.is_null():
            op = ResOperation(rop.OONONNULL, [op.args[0]], op.result)
            self.optimize_OONONNULL(op)
        elif value0.is_null():
            op = ResOperation(rop.OONONNULL, [op.args[1]], op.result)
            self.optimize_OONONNULL(op)
        else:
            self.optimize_default(op)

    def optimize_OOIS(self, op):
        value0 = self.getvalue(op.args[0])
        value1 = self.getvalue(op.args[1])
        if value0.is_virtual() or value1.is_virtual():
            self.make_constant(op.result)
        elif value1.is_null():
            op = ResOperation(rop.OOISNULL, [op.args[0]], op.result)
            self.optimize_OOISNULL(op)
        elif value0.is_null():
            op = ResOperation(rop.OOISNULL, [op.args[1]], op.result)
            self.optimize_OOISNULL(op)
        else:
            self.optimize_default(op)

    def optimize_GETFIELD_GC(self, op):
        value = self.getvalue(op.args[0])
        if value.is_virtual():
            # optimizefindnode should ensure that we don't get a KeyError
            fieldvalue = value.getfield(op.descr)
            self.make_equal_to(op.result, fieldvalue)
        else:
            value.make_nonnull()
            self.optimize_default(op)

    def optimize_GETFIELD_PURE_GC(self, op):
        xxx # optimize_GETFIELD_GC

    def optimize_SETFIELD_GC(self, op):
        value = self.getvalue(op.args[0])
        if value.is_virtual():
            value.setfield(op.descr, self.getvalue(op.args[1]))
        else:
            value.make_nonnull()
            self.optimize_default(op)

    def optimize_NEW_WITH_VTABLE(self, op):
        self.make_virtual(op.result)


optimize_ops = _findall(Optimizer, 'optimize_')
