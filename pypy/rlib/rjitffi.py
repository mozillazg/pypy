from pypy.rlib import rdynload
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.jit.backend.x86.runner import CPU
from pypy.jit.metainterp.history import LoopToken, BasicFailDescr
from pypy.jit.metainterp.history import BoxInt, BoxFloat, BoxPtr, NULLBOX
from pypy.jit.metainterp.resoperation import ResOperation, rop
from pypy.jit.metainterp.typesystem import deref

class CDLL(object):
    def __init__(self, name):
        try:
            self.lib = rdynload.dlopen(name)
        except rdynload.DLOpenError, e:
            raise OSError('%s: %s', name, e.msg or 'unspecified error')

        self.name = name
        self.cpu = CPU(None, None)

    def get(self, func, args_type, res_type='void'):
        return _Get(self.cpu, self.lib, func, args_type, res_type)

class _Get(object):
    def __init__(self, cpu, lib, func, args_type, res_type='void'):
        assert isinstance(args_type, list)
        self.args_type = args_type
        self.res_type = res_type
        self.cpu = cpu
        self.lib = lib.handler

        if self.res_type == 'int':
            self.bres = BoxInt()
            res = lltype.Signed
        elif self.res_type == 'float':
            self.bres = BoxFloat()
            res = lltype.Float
        elif self.res_type == 'ref':
            self.bres = BoxPtr()
            res = lltype.Signed
        elif self.res_type == 'void':
            self.bres = NULLBOX
            res = lltype.Void
        else:
            raise ValueError(self.res_type)

        try:
            addr = rffi.cast(lltype.Signed, rdynload.dlsym(self.lib, func))
        except KeyError:
            raise ValueError("Cannot find symbol %s", func)
        self.bfuncaddr = BoxInt(addr)

        args = []
        for arg in self.args_type:
            if arg == 'int':
                args.append(lltype.Signed)
            elif arg == 'float':
                args.append(lltype.Float)
            elif arg == 'ref':
                args.append(lltype.Signed)
            else:
                raise ValueError(arg)

        FPTR = lltype.Ptr(lltype.FuncType(args, res))
        FUNC = deref(FPTR)
        self.calldescr = self.cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT)

    def call(self, func_args=None):
        if func_args is None:
            func_args = []

        bargs = []
        for tp, value in zip(self.args_type, func_args):
            if tp == 'int':
                bargs.append(BoxInt(value))
            elif tp == 'float':
                bargs.append(BoxFloat(value))
            elif tp == 'ref':
                bargs.append(BoxPtr(value))
        inputargs = [self.bfuncaddr] + bargs

        oplist = [ResOperation(rop.CALL, inputargs, self.bres,
                               descr=self.calldescr),
                  ResOperation(rop.FINISH, [self.bres], None,
                               descr=BasicFailDescr(0))]
        looptoken = LoopToken()
        self.cpu.compile_loop(inputargs, oplist, looptoken)

        for i, box in enumerate(inputargs):
            if i == 0: # func address
                self.cpu.set_future_value_int(i, box.getint())
            elif self.args_type[i-1] == 'int':
                self.cpu.set_future_value_int(i, box.getint())
            elif self.args_type[i-1] == 'float':
                self.cpu.set_future_value_float(i, box.getfloat())
            elif self.args_type[i-1] == 'ref':
                self.cpu.set_future_value_ref(i, box.getref())

        res = self.cpu.execute_token(looptoken)
        if res is oplist[-1].descr:
            self.guard_failed = False
        else:
            self.guard_failed = True

        if self.res_type == 'int':
            r = BoxInt(self.cpu.get_latest_value_int(0)).getint()
        elif self.res_type == 'float':
            r = BoxFloat(self.cpu.get_latest_value_float(0)).getfloat()
        elif self.res_type == 'ref':
            r = BoxPtr(self.cpu.get_latest_value_ref(0)).getref()
        elif self.res_type == 'void':
            r = None
        else:
            raise ValueError(self.res_type)
        return r
