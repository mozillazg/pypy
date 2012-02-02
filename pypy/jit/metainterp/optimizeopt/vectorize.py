
from pypy.jit.metainterp.optimizeopt.optimizer import Optimization
from pypy.jit.metainterp.optimizeopt.util import make_dispatcher_method
from pypy.jit.metainterp.resoperation import rop, ResOperation
from pypy.jit.metainterp.history import BoxVector

VECTOR_SIZE = 2
VEC_MAP = {rop.FLOAT_ADD: rop.FLOAT_VECTOR_ADD}

class BaseTrack(object):
    pass

class Read(BaseTrack):
    def __init__(self, arr, index, op):
        self.arr = arr
        self.op = op
        self.index = index

    def match(self, other):
        if not isinstance(other, Read):
            return False
        return self.arr == other.arr

    def emit(self, optimizer):
        box = BoxVector()
        op = ResOperation(rop.GETARRAYITEM_VECTOR_RAW, [self.arr.box,
                                                        self.index.val.box],
                          box, descr=self.op.getdescr())
        optimizer.emit_operation(op)
        return box

class Write(BaseTrack):
    def __init__(self, arr, index, v, op):
        self.arr = arr
        self.index = index
        self.v = v
        self.op = op

    def match(self, other):
        if not isinstance(other, Write):
            return False
        return self.v.match(other.v)

    def emit(self, optimizer):
        arg = self.v.emit(optimizer)
        op = ResOperation(rop.SETARRAYITEM_VECTOR_RAW, [self.arr.box,
                                                        self.index.box, arg],
                          None, descr=self.op.getdescr())
        optimizer.emit_operation(op)

class BinOp(BaseTrack):
    def __init__(self, left, right, op):
        self.op = op
        self.left = left
        self.right = right

    def match(self, other):
        if not isinstance(other, BinOp):
            return False
        if self.op.getopnum() != other.op.getopnum():
            return False
        return self.left.match(other.left) and self.right.match(other.right)

    def emit(self, optimizer):
        left_box = self.left.emit(optimizer)
        right_box = self.right.emit(optimizer)
        res_box = BoxVector()
        op = ResOperation(VEC_MAP[self.op.getopnum()], [left_box, right_box],
                          res_box)
        optimizer.emit_operation(op)
        return res_box

class TrackIndex(object):
    def __init__(self, val, index):
        self.val = val
        self.index = index

    def advance(self):
        return TrackIndex(self.val, self.index + 1)

class OptVectorize(Optimization):
    def __init__(self):
        self.ops_so_far = []
        self.reset()

    def reset(self):
        # deal with reset
        for op in self.ops_so_far:
            self.emit_operation(op)
        self.ops_so_far = []
        self.track = {}
        self.tracked_indexes = {}
        self.full = {}
    
    def new(self):
        return OptVectorize()
    
    def optimize_ASSERT_ALIGNED(self, op):
        index = self.getvalue(op.getarg(1))
        self.tracked_indexes[index] = TrackIndex(index, 0)

    def optimize_GETARRAYITEM_RAW(self, op):
        arr = self.getvalue(op.getarg(0))
        index = self.getvalue(op.getarg(1))
        track = self.tracked_indexes.get(index)
        if track is None:
            self.emit_operation(op)
        else:
            self.ops_so_far.append(op)
            self.track[self.getvalue(op.result)] = Read(arr, track, op)

    def optimize_INT_ADD(self, op):
        # only for += 1
        one = self.getvalue(op.getarg(0))
        two = self.getvalue(op.getarg(1))
        self.emit_operation(op)
        if (one.is_constant() and one.box.getint() == 1 and
            two in self.tracked_indexes):
            index = two
        elif (two.is_constant() and two.box.getint() == 1 and
              one in self.tracked_indexes):
            index = one
        else:
            return
        self.tracked_indexes[self.getvalue(op.result)] = self.tracked_indexes[index].advance()

    def optimize_FLOAT_ADD(self, op):
        left = self.getvalue(op.getarg(0))
        right = self.getvalue(op.getarg(1))
        if left not in self.track or right not in self.track:
            self.emit_operation(op)
        else:
            self.ops_so_far.append(op)
            lt = self.track[left]
            rt = self.track[right]
            self.track[self.getvalue(op.result)] = BinOp(lt, rt, op)

    def optimize_SETARRAYITEM_RAW(self, op):
        index = self.getvalue(op.getarg(1))
        val = self.getvalue(op.getarg(2))
        if index not in self.tracked_indexes or val not in self.track:
            self.emit_operation(op)
            return
        v = self.track[val]
        arr = self.getvalue(op.getarg(0))
        ti = self.tracked_indexes[index]
        if arr not in self.full:
            self.full[arr] = [None] * VECTOR_SIZE
        self.full[arr][ti.index] = Write(arr, index, v, op)

    def emit_vector_ops(self, forbidden_boxes):
        for arg in forbidden_boxes:
            if arg in self.track:
                self.reset()
                return
        if self.full:
            for arr, items in self.full.iteritems():
                for item in items[1:]:
                    if item is None or not items[0].match(item):
                        self.reset()
                        return
                # XXX Right now we blow up on any of the vectorizers not
                # working. We need something more advanced in terms of ops
                # tracking
            for arr, items in self.full.iteritems():
                items[0].emit(self)
            self.ops_so_far = []

    def optimize_default(self, op):
        # list operations that are fine, not that many
        if op.opnum in [rop.JUMP, rop.FINISH, rop.LABEL]:
            self.emit_vector_ops(op.getarglist())
        elif op.is_guard():
            xxx
        else:
            self.reset()
        self.emit_operation(op)

    def propagate_forward(self, op):
        dispatch_opt(self, op)

dispatch_opt = make_dispatcher_method(OptVectorize, 'optimize_',
        default=OptVectorize.optimize_default)

