from pypy.rpython.annlowlevel import cast_base_ptr_to_instance
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.libffi import Func
from pypy.jit.codewriter.effectinfo import EffectInfo
from pypy.jit.metainterp.resoperation import rop, ResOperation
from pypy.jit.metainterp.optimizeutil import _findall
from pypy.jit.metainterp.optimizeopt.optimizer import Optimization

class FuncInfo(object):

    def __init__(self, funcval, cpu):
        self.opargs = []
        argtypes, restype = self._get_signature(funcval)
        self.descr = cpu.calldescrof_dynamic(argtypes, restype)

    def _get_signature(self, funcval):
        """
        given the funcval, return a tuple (argtypes, restype), where the
        actuall types are libffi.types.*

        The implementation is tricky because we have three possible cases:

        - translated: the easiest case, we can just cast back the pointer to
          the original Func instance and read .argtypes and .restype

        - completely untranslated: this is what we get from test_optimizeopt
          tests. funcval contains a FakeLLObject whose _fake_class is Func,
          and we can just get .argtypes and .restype

        - partially translated: this happens when running metainterp tests:
          funcval contains the low-level equivalent of a Func, and thus we
          have to fish inst_argtypes and inst_restype by hand.  Note that
          inst_argtypes is actually a low-level array, but we can use it
          directly since the only thing we do with it is to read its items
        """
        
        llfunc = funcval.box.getref_base()
        if we_are_translated():
            XXX
        elif getattr(llfunc, '_fake_class', None) is Func:
            # untranslated
            return llfunc.argtypes, llfunc.restype
        else:
            # partially translated
            # llfunc contains an opaque pointer to something like the following:
            # <GcStruct pypy.rlib.libffi.Func { super, inst_argtypes, inst_funcptr,
            #                                   inst_funcsym, inst_restype }>
            #
            # Unfortunately, we cannot use the proper lltype.cast_opaque_ptr,
            # because we don't have the exact TYPE to cast to.  Instead, we
            # just fish it manually :-(
            f = llfunc._obj.container
            return f.inst_argtypes, f.inst_restype


class NonConstantFuncVal(Exception):
    pass

class OptFfiCall(Optimization):

    def __init__(self):
        self.func_infos = {}

    def _get_oopspec(self, op):
        effectinfo = op.getdescr().get_extra_info()
        if effectinfo is not None:
            return effectinfo.oopspecindex
        return EffectInfo.OS_NONE

    def optimize_CALL(self, op):
        oopspec = self._get_oopspec(op)
        try:
            if oopspec == EffectInfo.OS_LIBFFI_PREPARE:
                self.do_prepare_call(op)
            elif oopspec == EffectInfo.OS_LIBFFI_PUSH_ARG:
                self.do_push_arg(op)
            elif oopspec == EffectInfo.OS_LIBFFI_CALL:
                op = self.do_call(op)
                self.emit_operation(op)
            else:
                raise NonConstantFuncVal # it's not a libffi call
        except NonConstantFuncVal:
            # normal case
            self.emit_operation(op)

    def _get_funcval(self, op):
        funcval = self.getvalue(op.getarg(1))
        if not funcval.is_constant():
            raise NonConstantFuncVal
        return funcval

    def do_prepare_call(self, op):
        funcval = self._get_funcval(op)
        assert funcval not in self.func_infos # XXX: do something nice etc. etc.
        self.func_infos[funcval] = FuncInfo(funcval, self.optimizer.cpu)

    def do_push_arg(self, op):
        # we store the op in funcs because we might want to emit it later,
        # in case we give up with the optimization
        funcval = self._get_funcval(op)
        self.func_infos[funcval].opargs.append(op)

    def do_call(self, op):
        funcval = self._get_funcval(op)
        info = self.func_infos[funcval]
        funcsymval = self.getvalue(op.getarg(2))
        arglist = [funcsymval.force_box()]
        for push_op in info.opargs:
            argval = self.getvalue(push_op.getarg(2))
            arglist.append(argval.force_box())
        newop = ResOperation(rop.CALL, arglist, op.result, descr=info.descr)
        del self.func_infos[funcval]
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
