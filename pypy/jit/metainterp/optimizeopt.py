from pypy.jit.metainterp.history import Const, Box
from pypy.jit.metainterp.optimizeutil import av_newdict, _findall
from pypy.rlib.objectmodel import we_are_translated


def optimize(loop):
    """Optimize loop.operations to make it match the input of loop.specnodes
    and to remove internal overheadish operations.  Note that loop.specnodes
    must be applicable to the loop; you will probably get an AssertionError
    if not.
    """
    Optimizer().optimize(loop)

# ____________________________________________________________


class Optimizer(object):

    def __init__(self):
        self._equals = {}          # mapping Box -> Box-or-Const
        self._known_classes = {}   # mapping Box -> ConstClass

    def deref(self, box):
        while box in self._equals:
            # follow the chain: box -> box2 -> box3 -> ...
            box2 = self._equals[box]
            if box2 not in self._equals:
                return box2
            # compress the mapping one step (rare case)
            box3 = self._equals[box2]
            self._equals[box] = box3
            box = box3
        return box

    def make_constant(self, box):
        assert isinstance(box, Box)
        assert box not in self._equals
        self._equals[box] = box.constbox()

    def has_constant_class(self, box):
        return isinstance(box, Const) or box in self._known_classes

    def make_constant_class(self, box, clsbox):
        assert isinstance(box, Box)
        assert isinstance(clsbox, Const)
        self._known_classes[box] = clsbox

    # ----------

    def optimize(self, loop):
        self.newoperations = []
        for op in loop.operations:
            op2 = op.clone()
            op2.args = [self.deref(box) for box in op.args]
            opnum = op2.opnum
            for value, func in optimize_ops:
                if opnum == value:
                    func(self, op2)
                    break
            else:
                self.optimize_default(op2)
        loop.operations = self.newoperations

    def emit_operation(self, op):
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
        if self.has_constant_class(op.args[0]):
            assert op.result.getint() == 1
            self.make_constant(op.result)
        else:
            self.optimize_default(op)

    def optimize_OOISNULL(self, op):
        if self.has_constant_class(op.args[0]):
            assert op.result.getint() == 0
            self.make_constant(op.result)
        else:
            self.optimize_default(op)


optimize_ops = _findall(Optimizer, 'optimize_')
