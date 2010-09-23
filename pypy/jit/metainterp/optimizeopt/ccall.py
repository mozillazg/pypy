from pypy.jit.metainterp.resoperation import rop, ResOperation
from pypy.jit.metainterp.optimizeutil import _findall
from pypy.jit.metainterp.optimizeopt.optimizer import Optimization

class OptCCall(Optimization):

    def __init__(self):
        self.func_args = {}

    def get_oopspec(self, funcbox):
        # XXX: not RPython at all, just a hack while waiting to have an
        # "official" way to know if and which oopspec we are calling
        funcname = str(funcbox)
        if '_libffi_prepare_call' in funcname:
            return 'prepare_call'
        elif '_libffi_push_arg' in funcname:
            return 'push_arg'
        elif '_libffi_call' in funcname:
            return 'call'
        return None

    def optimize_CALL(self, op):
        funcbox = op.args[0]
        oopspec = self.get_oopspec(funcbox)
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
        funcbox = op.args[1]
        assert funcbox not in self.func_args
        self.func_args[funcbox] = []

    def do_push_arg(self, op):
        funcbox = op.args[1]
        self.func_args[funcbox].append(op)

    def do_call(self, op):
        funcbox = op.args[1]
        funcsymbox = op.args[2]
        arglist = [funcsymbox]
        for push_op in self.func_args[funcbox]:
            arglist.append(push_op.args[2])
        newop = ResOperation(rop.CALL_C, arglist, op.result, None)
        del self.func_args[funcbox]
        return newop

    def propagate_forward(self, op):
        opnum = op.opnum
        for value, func in optimize_ops:
            if opnum == value:
                func(self, op)
                break
        else:
            self.emit_operation(op)

optimize_ops = _findall(OptCCall, 'optimize_')
