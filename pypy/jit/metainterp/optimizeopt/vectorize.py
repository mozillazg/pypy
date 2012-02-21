
from pypy.jit.metainterp.optimizeopt.optimizer import Optimization
from pypy.jit.metainterp.optimizeopt.util import make_dispatcher_method
from pypy.jit.metainterp.resoperation import rop, ResOperation
from pypy.jit.metainterp.history import BoxVector
from pypy.jit.codewriter.effectinfo import EffectInfo
from pypy.rlib.debug import debug_start, debug_print, debug_stop

VECTOR_SIZE = 2
VEC_MAP = {rop.FLOAT_ADD: rop.FLOAT_VECTOR_ADD,
           rop.FLOAT_SUB: rop.FLOAT_VECTOR_SUB,
           rop.GETINTERIORFIELD_RAW: rop.GETINTERIORFIELD_VECTOR_RAW,
           rop.SETINTERIORFIELD_RAW: rop.SETINTERIORFIELD_VECTOR_RAW,
           rop.GETARRAYITEM_RAW: rop.GETARRAYITEM_VECTOR_RAW,
           rop.SETARRAYITEM_RAW: rop.SETARRAYITEM_VECTOR_RAW,
           }


class BaseTrack(object):
    pass

class Read(BaseTrack):
    def __init__(self, arr, index, op):
        self.arr = arr
        self.op = op
        self.index = index

    def match(self, other, i):
        if not isinstance(other, Read):
            return False
        return self.arr == other.arr and other.index.index == i

    def emit(self, optimizer):
        box = BoxVector()
        op = ResOperation(VEC_MAP[self.op.getopnum()], [self.arr.box,
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

    def match(self, other, i):
        if not isinstance(other, Write):
            return False
        descr = self.op.getdescr()
        i = i * descr.get_field_size() / descr.get_width()
        return self.v.match(other.v, i)

    def emit(self, optimizer):
        arg = self.v.emit(optimizer)
        op = ResOperation(VEC_MAP[self.op.getopnum()], [self.arr.box,
                                                        self.index.box, arg],
                          None, descr=self.op.getdescr())
        optimizer.emit_operation(op)

class BinOp(BaseTrack):
    def __init__(self, left, right, op):
        self.op = op
        self.left = left
        self.right = right

    def match(self, other, i):
        if not isinstance(other, BinOp):
            return False
        if self.op.getopnum() != other.op.getopnum():
            return False
        return (self.left.match(other.left, i) and
                self.right.match(other.right, i))

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

    def advance(self, v):
        return TrackIndex(self.val, self.index + v)

    def match_descr(self, descr):
        if self.index == 0:
            return True
        if descr.is_array_descr:
            return self.index == 1
        if descr.get_width() != 1:
            return False # XXX this can probably be supported
        return self.index == descr.get_field_size()

class OptVectorize(Optimization):
    track = None
    full = None
    
    def __init__(self):
        self.ops_so_far = []
        self.reset()

    def reset(self):
        # deal with reset
        if self.track or self.full:
            debug_start("jit-optimizeopt-vectorize")
            debug_print("aborting vectorizing")
            debug_stop("jit-optimizeopt-vectorize")
        for op in self.ops_so_far:
            self.emit_operation(op)
        self.ops_so_far = []
        self.track = {}
        self.tracked_indexes = {}
        self.full = {}
    
    def new(self):
        return OptVectorize()
    
    def optimize_CALL(self, op):
        oopspec = self.get_oopspec(op)
        if oopspec == EffectInfo.OS_ASSERT_ALIGNED:
            index = self.getvalue(op.getarg(2))
            self.tracked_indexes[index] = TrackIndex(index, 0)
        else:
            self.optimize_default(op)

    def optimize_GETARRAYITEM_RAW(self, op):
        arr = self.getvalue(op.getarg(0))
        index = self.getvalue(op.getarg(1))
        track = self.tracked_indexes.get(index, None)
        if track is None:
            self.emit_operation(op)
        elif not track.match_descr(op.getdescr()):
            self.reset()
            self.emit_operation(op)
        else:
            self.ops_so_far.append(op)
            self.track[self.getvalue(op.result)] = Read(arr, track, op)

    optimize_GETINTERIORFIELD_RAW = optimize_GETARRAYITEM_RAW

    def optimize_INT_ADD(self, op):
        # only for += 1
        one = self.getvalue(op.getarg(0))
        two = self.getvalue(op.getarg(1))
        self.emit_operation(op)
        if (one.is_constant() and two in self.tracked_indexes):
            index = two
            v = one.box.getint()
        elif (two.is_constant() and one in self.tracked_indexes):
            index = one
            v = two.box.getint()
        else:
            return
        self.tracked_indexes[self.getvalue(op.result)] = self.tracked_indexes[index].advance(v)

    def _optimize_binop(self, op):
        left = self.getvalue(op.getarg(0))
        right = self.getvalue(op.getarg(1))
        if left not in self.track or right not in self.track:
            if left in self.track or right in self.track:
                self.reset()
            self.emit_operation(op)
        else:
            self.ops_so_far.append(op)
            lt = self.track[left]
            rt = self.track[right]
            self.track[self.getvalue(op.result)] = BinOp(lt, rt, op)

    optimize_FLOAT_ADD = _optimize_binop
    optimize_FLOAT_SUB = _optimize_binop

    def optimize_SETARRAYITEM_RAW(self, op):
        index = self.getvalue(op.getarg(1))
        val = self.getvalue(op.getarg(2))
        if index not in self.tracked_indexes or val not in self.track:
            # We could detect cases here, but we're playing on the safe
            # side and just resetting everything
            self.reset()
            self.emit_operation(op)
            return
        self.ops_so_far.append(op)
        v = self.track[val]
        arr = self.getvalue(op.getarg(0))
        ti = self.tracked_indexes[index]
        if arr not in self.full:
            self.full[arr] = [None] * VECTOR_SIZE
        i = (ti.index * op.getdescr().get_width() //
             op.getdescr().get_field_size())
        self.full[arr][i] = Write(arr, index, v, op)

    optimize_SETINTERIORFIELD_RAW = optimize_SETARRAYITEM_RAW

    def emit_vector_ops(self, forbidden_boxes):
        for arg in forbidden_boxes:
            if self.getvalue(arg) in self.track:
                self.reset()
                return
        if self.full:
            for arr, items in self.full.iteritems():
                for i in range(1, len(items)):
                    item = items[i]
                    if item is None or not items[0].match(item, i):
                        self.reset()
                        return
                # XXX Right now we blow up on any of the vectorizers not
                # working. We need something more advanced in terms of ops
                # tracking
            for arr, items in self.full.iteritems():
                items[0].emit(self)
            self.ops_so_far = []
        self.reset()
            
    def optimize_default(self, op):
        # list operations that are fine, not that many
        if op.opnum in [rop.JUMP, rop.FINISH, rop.LABEL]:
            self.emit_vector_ops(op.getarglist())
        elif op.is_guard():
            lst = op.getarglist()
            if op.getfailargs() is not None:
                lst = lst + op.getfailargs()
            self.emit_vector_ops(lst)
        elif op.is_always_pure():
            # in theory no side effect ops, but stuff like malloc
            # can go in the way
            # we also need to keep track of stuff that can go into those
            for box in op.getarglist():
                if self.getvalue(box) in self.track:
                    self.reset()
                    break
        else:
            self.reset()
        self.emit_operation(op)

    def propagate_forward(self, op):
        dispatch_opt(self, op)

dispatch_opt = make_dispatcher_method(OptVectorize, 'optimize_',
        default=OptVectorize.optimize_default)

