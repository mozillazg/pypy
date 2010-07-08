from pypy.rlib import rdynload
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.jit.backend.x86.runner import CPU
from pypy.jit.metainterp.history import LoopToken, BasicFailDescr
from pypy.jit.metainterp.history import BoxInt, BoxFloat, BoxPtr, NULLBOX
from pypy.jit.metainterp.resoperation import ResOperation, rop
from pypy.jit.metainterp.typesystem import deref

cache = {} # XXX global!

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
        name_ptr = rffi.str2charp(name)
        try:
            self.handler = rdynload.dlopen(name_ptr)
        except rdynload.DLOpenError, e:
            raise OSError('%s: %s', name, e.msg or 'unspecified error')
        finally:
            rffi.free_charp(name_ptr)

class _Get(object):
    def __init__(self, cpu, lib, func, args_type, res_type='v'):
        assert isinstance(args_type, list)
        self.args_type = args_type
        self.res_type = res_type
        self.cpu = cpu
        lib = lib.handler
        bargs = []

        try:
            self.funcaddr = rffi.cast(lltype.Signed, rdynload.dlsym(lib, func))
        except KeyError:
            raise ValueError("Cannot find symbol %s", func)
        bargs.append(BoxInt())

        # grab from the cache if possible
        try:
            self.looptoken = cache[self.res_type][tuple(self.args_type)]
        except KeyError:
            args = []
            for arg in self.args_type:
                if arg == 'i':
                    bargs.append(BoxInt())
                    args.append(lltype.Signed)
                elif arg == 'f':
                    bargs.append(BoxFloat())
                    args.append(lltype.Float)
                elif arg == 'p':
                    bargs.append(BoxPtr())
                    args.append(lltype.Signed)
                else:
                    raise ValueError(arg)

            if self.res_type == 'i':
                res = lltype.Signed
                bres = BoxInt()
            elif self.res_type == 'f':
                res = lltype.Float
                bres = BoxFloat()
            elif self.res_type == 'p':
                res = lltype.Signed
                bres = BoxPtr()
            elif self.res_type == 'v':
                res = lltype.Void
                bres = NULLBOX
            else:
                raise ValueError(self.res_type)

            FPTR = lltype.Ptr(lltype.FuncType(args, res))
            FUNC = deref(FPTR)
            calldescr = self.cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT)

            self.looptoken = LoopToken()
            oplist = [ResOperation(rop.CALL, bargs, bres, descr=calldescr),
                      ResOperation(rop.FINISH, [bres], None,
                                   descr=BasicFailDescr(0))]
            self.cpu.compile_loop(bargs, oplist, self.looptoken)

            # add to the cache
            cache[self.res_type] = { tuple(self.args_type) : self.looptoken }
        self.setup_stack()

    def call(self, push_result):
        res = self.cpu.execute_token(self.looptoken)

        if self.res_type == 'i':
            r = push_result(self.cpu.get_latest_value_int(0))
        elif self.res_type == 'f':
            r = push_result(self.cpu.get_latest_value_float(0))
        elif self.res_type == 'p':
            r = push_result(self.cpu.get_latest_value_ref(0))
        elif self.res_type == 'v':
            r = None
        else:
            raise ValueError(self.res_type)
        
        self.setup_stack() # clean up the stack
        return r

    def setup_stack(self):
        self.esp = 0
        self.push_funcaddr(self.funcaddr)

    def push_funcaddr(self, value):
        self.cpu.set_future_value_int(self.esp, value)
        self.esp += 1

    def push_int(self, value):
        self.cpu.set_future_value_int(self.esp, value)
        self.esp += 1

    def push_float(self, value):
        self.cpu.set_future_value_float(self.esp, value)
        self.esp += 1

    def push_ref(self, value):
        self.cpu.set_future_value_ref(self.esp, value)
        self.esp += 1
