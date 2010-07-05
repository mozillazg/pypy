from pypy.rlib import rdynload
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.jit.backend.x86.runner import CPU
from pypy.jit.metainterp.history import LoopToken, BasicFailDescr
from pypy.jit.metainterp.history import BoxInt, BoxFloat, BoxPtr, NULLBOX
from pypy.jit.metainterp.resoperation import ResOperation, rop
from pypy.jit.metainterp.typesystem import deref

class CDLL(object):
    def __init__(self, name, load=True):
        if load:
            self.lib = _LibHandler(name)
        else:
            self.lib = None

        self.name = name
        self.cpu = CPU(None, None)

    def get(self, func, args_type, res_type='v'):
        return _Get(self.cpu, self.lib, func, args_type, res_type)

class _LibHandler(object):
    def __init__(self, name):
        try:
            self.handler = rdynload.dlopen(rffi.str2charp(name))
        except rdynload.DLOpenError, e:
            raise OSError('%s: %s', name, e.msg or 'unspecified error')

class _Get(object):
    def __init__(self, cpu, lib, func, args_type, res_type='v'):
        assert isinstance(args_type, list)
        self.args_type = args_type
        self.res_type = res_type
        self.cpu = cpu
        self.lib = lib.handler
        self.setup_stack()

        if self.res_type == 'i':
            self.bres = BoxInt()
            res = lltype.Signed
        elif self.res_type == 'f':
            self.bres = BoxFloat()
            res = lltype.Float
        elif self.res_type == 'p':
            self.bres = BoxPtr()
            res = lltype.Signed
        elif self.res_type == 'v':
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
            if arg == 'i':
                args.append(lltype.Signed)
            elif arg == 'f':
                args.append(lltype.Float)
            elif arg == 'p':
                args.append(lltype.Signed)
            else:
                raise ValueError(arg)

        FPTR = lltype.Ptr(lltype.FuncType(args, res))
        FUNC = deref(FPTR)
        self.calldescr = self.cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT)

    def call(self):
        inputargs = [self.bfuncaddr] + self.bargs

        oplist = [ResOperation(rop.CALL, inputargs, self.bres,
                               descr=self.calldescr),
                  ResOperation(rop.FINISH, [self.bres], None,
                               descr=BasicFailDescr(0))]
        looptoken = LoopToken()
        self.cpu.compile_loop(inputargs, oplist, looptoken)
        self.cpu.set_future_value_int(0, self.bfuncaddr.getint())

        res = self.cpu.execute_token(looptoken)
        if res is oplist[-1].descr:
            self.guard_failed = False
        else:
            self.guard_failed = True

        self.setup_stack() # clean up the stack

        if self.res_type == 'i':
            r = BoxInt(self.cpu.get_latest_value_int(0)).getint()
        elif self.res_type == 'f':
            r = BoxFloat(self.cpu.get_latest_value_float(0)).getfloat()
        elif self.res_type == 'p':
            r = BoxPtr(self.cpu.get_latest_value_ref(0)).getref()
        elif self.res_type == 'v':
            r = None
        else:
            raise ValueError(self.res_type)
        return r

    def setup_stack(self):
        self.bargs = []
        self.esp = 1 # 0 is a func addr

    def push_int(self, value):
        self.cpu.set_future_value_int(self.esp, value)
        self.bargs.append(BoxInt(value))
        self.esp += 1

    def push_float(self, value):
        self.cpu.set_future_value_float(self.esp, value)
        self.bargs.append(BoxFloat(value))
        self.esp += 1

    def push_ref(self, value):
        self.cpu.set_future_value_ref(self.esp, value)
        self.bargs.append(BoxPtr(value))
        self.esp += 1
