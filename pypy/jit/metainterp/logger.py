import os
from pypy.rlib import rlog
from pypy.jit.metainterp.resoperation import rop
from pypy.jit.metainterp.history import Const, ConstInt, Box, \
     BoxInt, ConstAddr, ConstFloat, BoxFloat, AbstractFailDescr

class Logger(object):

    def __init__(self, ts, guard_number=False):
        self.ts = ts
        self.guard_number=guard_number

    def log_loop(self, inputargs, operations, number=-1, type="unoptimized"):
        if not rlog.has_log():
            return
        rlog.debug_log("jit-log-loop-{",
                       "# Loop%(number)d (%(type)s), %(length)d ops",
                       number = number,
                       type   = type,
                       length = len(operations))
        self._log_operations(inputargs, operations, {})
        rlog.debug_log("jit-log-loop-}",
                       "# End")

    def log_bridge(self, inputargs, operations, number=-1):
        if not rlog.has_log():
            return
        rlog.debug_log("jit-log-bridge-{",
                       "# Bridge out of Guard%(guard)d, %(length)d ops",
                       guard  = number,
                       length = len(operations))
        self._log_operations(inputargs, operations, {})
        rlog.debug_log("jit-log-bridge-}",
                       "# End")

    def repr_of_descr(self, descr):
        return descr.repr_of_descr()

    def repr_of_arg(self, memo, arg):
        try:
            mv = memo[arg]
        except KeyError:
            mv = len(memo)
            memo[arg] = mv
        if isinstance(arg, ConstInt):
            return str(arg.value)
        elif isinstance(arg, BoxInt):
            return 'i' + str(mv)
        elif isinstance(arg, self.ts.ConstRef):
            return 'ConstPtr(ptr' + str(mv) + ')'
        elif isinstance(arg, self.ts.BoxRef):
            return 'p' + str(mv)
        elif isinstance(arg, ConstFloat):
            return str(arg.value)
        elif isinstance(arg, BoxFloat):
            return 'f' + str(mv)
        elif isinstance(arg, self.ts.ConstAddr):
            return 'ConstAddr(adr' + str(mv) + ')'
        else:
            return '?'

    def _log_operations(self, inputargs, operations, memo):
        if inputargs is not None:
            args = ", ".join([self.repr_of_arg(memo, arg) for arg in inputargs])
            rlog.debug_log("jit-log-head",
                           "[%(inputargs)s]",
                           inputargs = args)
        for i in range(len(operations)):
            op = operations[i]
            if op.opnum == rop.DEBUG_MERGE_POINT:
                loc = op.args[0]._get_str()
                rlog.debug_log("jit-log-mgpt",
                               "debug_merge_point(%(loc)r)",
                               loc = loc)
                continue
            args = ", ".join([self.repr_of_arg(memo, arg) for arg in op.args])
            if op.result is not None:
                res = self.repr_of_arg(memo, op.result) + " = "
            else:
                res = ""
            is_guard = op.is_guard()
            if op.descr is not None:
                descr = op.descr
                if is_guard and self.guard_number:
                    assert isinstance(descr, AbstractFailDescr)
                    r = "<Guard%d>" % descr.get_index()
                else:
                    r = self.repr_of_descr(descr)
                args += ', descr=' +  r
            if is_guard and op.fail_args is not None:
                fail_args = ' [' + ", ".join([self.repr_of_arg(memo, arg)
                                              for arg in op.fail_args]) + ']'
            else:
                fail_args = ''
            rlog.debug_log("jit-log-insn",
                           "%(res)s%(opname)s(%(args)s)%(fail_args)s",
                           res       = res,
                           opname    = op.getopname(),
                           args      = args,
                           fail_args = fail_args)
