from pypy.jit.metainterp.resoperation import rop, ResOperation
from pypy.jit.metainterp.optimizeutil import _findall
from pypy.jit.metainterp.optimizeopt.optimizer import Optimization

class OptCCall(Optimization):

    def __init__(self):
        self.func_args = {}

    def get_oopspec(self, funcval):
        # XXX: not RPython at all, just a hack while waiting to have an
        # "official" way to know if and which oopspec we are calling
        funcname = str(funcval.box)
        if '_libffi_prepare_call' in funcname:
            return 'prepare_call'
        elif '_libffi_push_arg' in funcname:
            return 'push_arg'
        elif '_libffi_call' in funcname:
            return 'call'
        return None

    def optimize_CALL(self, op):
        funcval = self.getvalue(op.getarg(0))
        oopspec = self.get_oopspec(funcval)
        if oopspec == 'prepare_call':
            self.do_prepare_call(op)
            return
        elif oopspec == 'push_arg':
            self.do_push_arg(op)
            return
        elif oopspec == 'call':
            op = self.do_call(op)
        self.emit_operation(op)

    def do_prepare_call(self, op):
        funcval = self.getvalue(op.getarg(1))
        assert funcval not in self.func_args
        self.func_args[funcval] = []

    def do_push_arg(self, op):
        # we store the op in func_args because we might want to emit it later,
        # in case we give up with the optimization
        funcval = self.getvalue(op.getarg(1))
        self.func_args[funcval].append(op)

    def do_call(self, op):
        funcval = self.getvalue(op.getarg(1))
        funcsymval = self.getvalue(op.getarg(2))
        arglist = [funcsymval.force_box()]
        for push_op in self.func_args[funcval]:
            argval = self.getvalue(push_op.getarg(2))
            arglist.append(argval.force_box())
        newop = ResOperation(rop.CALL_C, arglist, op.result, None)
        del self.func_args[funcval]
        return newop

    def propagate_forward(self, op):
        opnum = op.getopnum()
        for value, func in optimize_ops:
            if opnum == value:
                func(self, op)
                break
        else:
            self.emit_operation(op)

optimize_ops = _findall(OptCCall, 'optimize_')
