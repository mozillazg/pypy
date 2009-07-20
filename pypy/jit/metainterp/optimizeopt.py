from pypy.jit.metainterp.history import Const, Box, BoxInt, BoxPtr, BoxObj
from pypy.jit.metainterp.history import AbstractValue
from pypy.jit.metainterp.resoperation import rop
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

class VirtualBox(AbstractValue):
    def __init__(self):
        self.fields = av_newdict()     # ofs -> Box

    def nonnull(self):
        return True


class __extend__(SpecNode):
    def setup_virtual_node(self, optimizer, box, newinputargs):
        newinputargs.append(box)
    def teardown_virtual_node(self, box, newexitargs):
        newexitargs.append(box)

class __extend__(VirtualInstanceSpecNode):
    def setup_virtual_node(self, optimizer, box, newinputargs):
        vbox = optimizer.make_virtual(box, self.known_class)
        for ofs, subspecnode in self.fields:
            subbox = optimizer.make_box(ofs)
            vbox.fields[ofs] = subbox
            subspecnode.setup_virtual_node(optimizer, subbox, newinputargs)
    def teardown_virtual_node(self, box, newexitargs):
        assert isinstance(box, VirtualBox)
        for ofs, subspecnode in self.fields:
            # XXX if ofs not in box.fields:...
            subspecnode.teardown_virtual_node(box.fields[ofs], newexitargs)


class Optimizer(object):

    def __init__(self, cpu, loop):
        self.cpu = cpu
        self.loop = loop
        # Boxes used a keys to _equals have been proven to be equal to
        # something else: another Box, a Const, or a VirtualBox.  Boxes
        # and VirtualBoxes can also be listed in _known_classes if we
        # know their class (or just know that they are non-null, in which
        # case we use None).  Boxes *must not* be keys in both dicts.
        self._equals = {}          # mapping Box -> Box/Const/VirtualBox
        self._known_classes = {}   # mapping Box -> ConstClass/None

    def deref(self, box):
        """Maps a Box/Const to the corresponding Box/Const/VirtualBox
        by following the dict _equals.
        """
        box = self._equals.get(box, box)
        assert box not in self._equals
        return box

    def _make_equal(self, box, box2):
        assert isinstance(box, Box)
        assert box not in self._equals
        assert box not in self._known_classes
        self._equals[box] = box2

    def make_constant(self, box):
        """Mark the given Box as actually representing a Const value."""
        self._make_equal(box, box.constbox())

    def make_virtual(self, box, clsbox):
        """Mark the given Box as actually representing a VirtualBox value."""
        vbox = VirtualBox()
        self._make_equal(box, vbox)
        self.make_constant_class(vbox, clsbox)
        return vbox

    def has_constant_class(self, box):
        return (isinstance(box, Const) or
                self._known_classes.get(box, None) is not None)

    def make_constant_class(self, box, clsbox):
        assert isinstance(clsbox, Const)
        assert box not in self._equals
        self._known_classes[box] = clsbox

    def make_nonnull(self, box):
        assert box not in self._equals
        self._known_classes.setdefault(box, None)

    def make_box(self, fieldofs):
        if fieldofs.is_pointer_field():
            if not self.cpu.is_oo:
                return BoxPtr()
            else:
                return BoxObj()
        else:
            return BoxInt()

    def known_nonnull(self, box):
        if isinstance(box, Box):
            return box in self._known_classes
        else:
            return box.nonnull()   # Consts or VirtualBoxes

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
            op2 = op.clone()
            op2.args = [self.deref(box) for box in op.args]
            opnum = op2.opnum
            for value, func in optimize_ops:
                if opnum == value:
                    func(self, op2)
                    break
            else:
                self.optimize_default(op2)
        self.loop.operations = self.newoperations

    def emit_operation(self, op):
        for x in op.args:
            assert not isinstance(x, VirtualBox)
        self.newoperations.append(op)

    def optimize_default(self, op):
        if op.is_always_pure():
            for box in op.args:
                if not isinstance(box, Const):
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
            specnodes[i].teardown_virtual_node(op.args[i], exitargs)
        op.args = exitargs
        self.emit_operation(op)

    def optimize_GUARD_VALUE(self, op):
        assert isinstance(op.args[1], Const)
        assert op.args[0].get_() == op.args[1].get_()
        if not isinstance(op.args[0], Const):
            self.emit_operation(op)
            self.make_constant(op.args[0])

    def optimize_GUARD_TRUE(self, op):
        assert op.args[0].getint()
        if not isinstance(op.args[0], Const):
            self.emit_operation(op)
            self.make_constant(op.args[0])

    def optimize_GUARD_FALSE(self, op):
        assert not op.args[0].getint()
        if not isinstance(op.args[0], Const):
            self.emit_operation(op)
            self.make_constant(op.args[0])

    def optimize_GUARD_CLASS(self, op):
        instbox = op.args[0]
        clsbox = op.args[1]
        # XXX should probably assert that the class is right
        if not self.has_constant_class(instbox):
            self.emit_operation(op)
            self.make_constant_class(instbox, clsbox)

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
        if (isinstance(op.args[0], VirtualBox) or
            isinstance(op.args[1], VirtualBox)):
            self.make_constant(op.result)
        elif self.known_nonnull(op.args[1]):
            op.opnum = rop.OONONNULL
            del op.args[1]
            self.optimize_OONONNULL(op)
        elif self.known_nonnull(op.args[0]):
            op.opnum = rop.OONONNULL
            del op.args[0]
            self.optimize_OONONNULL(op)
        else:
            self.optimize_default(op)

    def optimize_OOIS(self, op):
        if (isinstance(op.args[0], VirtualBox) or
            isinstance(op.args[1], VirtualBox)):
            self.make_constant(op.result)
        elif self.known_nonnull(op.args[1]):
            op.opnum = rop.OOISNULL
            del op.args[1]
            self.optimize_OOISNULL(op)
        elif self.known_nonnull(op.args[0]):
            op.opnum = rop.OOISNULL
            del op.args[0]
            self.optimize_OOISNULL(op)
        else:
            self.optimize_default(op)

    def optimize_GETFIELD_GC(self, op):
        instbox = op.args[0]
        if isinstance(instbox, VirtualBox):
            # optimizefindnode should ensure that 'op.descr in instbox.fields'
            self._make_equal(op.result, instbox.fields[op.descr])
        else:
            self.make_nonnull(instbox)
            self.optimize_default(op)

    optimize_GETFIELD_PURE_GC = optimize_GETFIELD_GC

    def optimize_SETFIELD_GC(self, op):
        instbox = op.args[0]
        if isinstance(instbox, VirtualBox):
            instbox.fields[op.descr] = op.args[1]
        else:
            self.make_nonnull(instbox)
            self.optimize_default(op)

    def optimize_NEW_WITH_VTABLE(self, op):
        self.make_virtual(op.result, op.args[0])


optimize_ops = _findall(Optimizer, 'optimize_')
