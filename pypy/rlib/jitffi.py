from pypy.interpreter.error import operationerrfmt
from pypy.rlib import rdynload
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.jit.backend.x86.runner import CPU
from pypy.jit.metainterp.history import LoopToken, BasicFailDescr
from pypy.jit.metainterp.history import BoxInt, BoxFloat, BoxPtr
from pypy.jit.metainterp.resoperation import ResOperation, rop
from pypy.jit.metainterp.typesystem import deref

class CDLL(object):
    def __init__(self, name):
        try:
            self.lib = rdynload.dlopen(name)
        except libffi.DLOpenError, e:
            raise operationerrfmt(space.w_OSError, '%s: %s', name,
                                  e.msg or 'unspecified error')
        self.name = name
        self.cpu = CPU(None, None)

    def call(self, func, func_args, res_type='void'):
        # only integers are supported for now
        assert isinstance(func_args, list)

        if res_type == 'int':
            bres = BoxInt()
        elif res_type == 'float':
            bres = BoxFloat()
        elif res_type == 'ref':
            bres = BoxPtr()
        elif res_type == 'void':
            bres = None
        else:
            raise ValueError(res_type)

        try:
            addr = rffi.cast(lltype.Signed, rdynload.dlsym(self.lib, func))
        except KeyError:
            raise operationerrfmt(space.w_ValueError,
                                  "Cannot find symbol %s", func)
        bfuncaddr = BoxInt(addr)

        args_type = [ lltype.Signed for i in func_args ]
        FPTR = lltype.Ptr(lltype.FuncType(args_type, lltype.Signed))
        FUNC = deref(FPTR)
        calldescr = self.cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT)

        bargs = [ BoxInt(x) for x in func_args ]
        inputargs = [bfuncaddr] + bargs

        oplist = [ResOperation(rop.CALL, inputargs, bres, descr=calldescr),
                  ResOperation(rop.FINISH, [bres], None,
                               descr=BasicFailDescr(0))]
        looptoken = LoopToken()
        self.cpu.compile_loop(inputargs, oplist, looptoken)

        i = 0
        for box in inputargs:
            self.cpu.set_future_value_int(i, box.getint())
            i += 1

        res = self.cpu.execute_token(looptoken)
        if res is oplist[-1].descr:
            self.guard_failed = False
        else:
            self.guard_failed = True

        if res_type == 'int':
            r = BoxInt(self.cpu.get_latest_value_int(0)).getint()
        elif res_type == 'float':
            r = BoxFloat(self.cpu.get_latest_value_float(0)).getfloat()
        elif res_type == 'ref':
            r = BoxPtr(self.cpu.get_latest_value_ref(0)).getref()
        elif res_type == 'void':
            r = None
        else:
            raise ValueError(res_type)
        return r

    def get(self, func, args_type, res_type='void'):
        return _Get(self.cpu, self.lib, func, args_type, res_type)

class _Get(object):
    def __init__(self, cpu, lib, func, args_type, res_type='void'):
        assert isinstance(args_type, list)
        if 'void' in args_type and len(args_type) > 1:
            raise ValueError("'void' must be the only parameter")
        self.args_type = args_type
        self.res_type = res_type
        self.cpu = cpu
        self.lib = lib
        # XXX add 'void' handling
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
            self.bres = None
            res = None
        else:
            raise ValueError(self.res_type)

        try:
            addr = rffi.cast(lltype.Signed, rdynload.dlsym(self.lib, func))
        except KeyError:
            raise operationerrfmt(space.w_ValueError,
                                  "Cannot find symbol %s", func)
        self.bfuncaddr = BoxInt(addr)

        args = []
        for arg in self.args_type:
            if arg == 'int':
                args.append(lltype.Signed)
            elif arg == 'float':
                args.append(lltype.Float)
            elif arg == 'ref':
                args.append(lltype.Signed)
            elif arg == 'void':
                args.append(None)
            else:
                raise ValueError(arg)

        FPTR = lltype.Ptr(lltype.FuncType(args, res))
        FUNC = deref(FPTR)
        self.calldescr = self.cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT)

    def __call__(self, *func_args):
        bargs = []
        for tp, value in zip(self.args_type, func_args):
            if tp == 'int':
                bargs.append(BoxInt(value))
            elif tp == 'float':
                bargs.append(BoxFloat(value))
            elif tp == 'ref':
                bargs.append(BoxPtr(value))
            elif tp == 'void':
                assert False #XXX
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
