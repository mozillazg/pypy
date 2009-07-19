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
        # set of Boxes; the value is not stored in the dict, but can
        # be accessed as the Box.getint() or get_().
        self._consts = {}

    def is_constant(self, box):
        return isinstance(box, Const) or box in self._consts

    def make_constant(self, box):
        assert isinstance(box, Box)
        self._consts[box] = box.constbox()

    def rename_argument(self, box):
        return self._consts.get(box, box)

    # ----------

    def optimize(self, loop):
        self.newoperations = []
        for op in loop.operations:
            opnum = op.opnum
            for value, func in optimize_ops:
                if opnum == value:
                    func(self, op)
                    break
            else:
                self.optimize_default(op)
        loop.operations = self.newoperations

    def emit_operation(self, op):
        op2 = op.clone()
        op2.args = [self.rename_argument(box) for box in op.args]
        self.newoperations.append(op2)

    def optimize_default(self, op):
        if op.is_always_pure():
            for box in op.args:
                if not self.is_constant(box):
                    break
            else:
                # all constant arguments: constant-fold away
                self.make_constant(op.result)
                return
        # otherwise, the operation remains
        self.emit_operation(op)

    def optimize_GUARD_VALUE(self, op):
        if self.is_constant(op.args[0]):
            assert isinstance(op.args[1], Const)
            assert self.rename_argument(op.args[0]).get_() == op.args[1].get_()
        else:
            self.emit_operation(op)

    def optimize_GUARD_TRUE(self, op):
        if self.is_constant(op.args[0]):
            assert self.rename_argument(op.args[0]).getint()
        else:
            self.emit_operation(op)

    def optimize_GUARD_FALSE(self, op):
        if self.is_constant(op.args[0]):
            assert not self.rename_argument(op.args[0]).getint()
        else:
            self.emit_operation(op)


optimize_ops = _findall(Optimizer, 'optimize_')
