from pypy.rpython.annlowlevel import cast_base_ptr_to_instance
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.libffi import Func
from pypy.jit.metainterp.resoperation import rop, ResOperation
from pypy.jit.metainterp.optimizeutil import _findall
from pypy.jit.metainterp.optimizeopt.optimizer import Optimization

class FuncDescription(object):

    def __init__(self, cpu, func):
        self.func = func
        self.args = []


class OptFfiCall(Optimization):

    def __init__(self):
        self.funcs = {}

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
        targetval = self.getvalue(op.getarg(0))
        oopspec = self.get_oopspec(targetval)
        if oopspec == 'prepare_call':
            self.do_prepare_call(op)
            return
        elif oopspec == 'push_arg':
            self.do_push_arg(op)
            return
        elif oopspec == 'call':
            op = self.do_call(op)
        self.emit_operation(op)

    def _cast_to_high_level(self, Class, obj):
        if we_are_translated():
            XXX
        else:
            # this is just for the tests in test_optimizeopt.py
            cls = getattr(obj, '_fake_class', obj.__class__)
            assert issubclass(cls, Class)
            return obj

    def _get_func(self, op):
        funcval = self.getvalue(op.getarg(1))
        assert funcval.is_constant() # XXX: do something nice if it's not constant
        llfunc = funcval.box.getref_base()
        func = self._cast_to_high_level(Func, llfunc)
        return func

    def do_prepare_call(self, op):
        func = self._get_func(op)
        assert func not in self.funcs # XXX: do something nice etc. etc.
        self.funcs[func] = FuncDescription(self.optimizer.cpu, func)

    def do_push_arg(self, op):
        # we store the op in funcs because we might want to emit it later,
        # in case we give up with the optimization
        func = self._get_func(op)
        self.funcs[func].args.append(op)

    def do_call(self, op):
        func = self._get_func(op)
        funcsymval = self.getvalue(op.getarg(2))
        arglist = [funcsymval.force_box()]
        for push_op in self.funcs[func].args:
            argval = self.getvalue(push_op.getarg(2))
            arglist.append(argval.force_box())
        # XXX: add the descr
        newop = ResOperation(rop.CALL, arglist, op.result, None)
        del self.funcs[func]
        return newop

    def propagate_forward(self, op):
        opnum = op.getopnum()
        for value, func in optimize_ops:
            if opnum == value:
                func(self, op)
                break
        else:
            self.emit_operation(op)

optimize_ops = _findall(OptFfiCall, 'optimize_')
