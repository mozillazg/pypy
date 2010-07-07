from pypy.rlib import rdynload
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.jit.backend.x86.runner import CPU
from pypy.jit.metainterp.history import LoopToken, BasicFailDescr
from pypy.jit.metainterp.history import BoxInt, BoxFloat, BoxPtr, NULLBOX
from pypy.jit.metainterp.resoperation import ResOperation, rop
from pypy.jit.metainterp.typesystem import deref

cache = [] # XXX global!

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
        self.looptoken = None
        lib = lib.handler
        bargs = []
        self.setup_stack()

        try:
            self.funcaddr = rffi.cast(lltype.Signed, rdynload.dlsym(lib, func))
        except KeyError:
            raise ValueError("Cannot find symbol %s", func)
        bargs.append(BoxInt())

        # check if it's not already compiled
        for func in cache:
            if self.args_type == func.args_type and \
               self.res_type == func.res_type:
                self.looptoken = func.looptoken
                break

        if self.looptoken is None:
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
            self.calldescr = self.cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT)

            self.looptoken = LoopToken()
            self.oplist = [ResOperation(rop.CALL, bargs, bres,
                                        descr=self.calldescr),
                           ResOperation(rop.FINISH, [bres], None,
                                        descr=BasicFailDescr(0))]
            self.cpu.compile_loop(bargs, self.oplist, self.looptoken)

            # add to the cache
            cache.append(_Func(self.args_type, self.res_type, self.looptoken))

    def call(self):
        self.push_funcaddr(self.funcaddr)
        res = self.cpu.execute_token(self.looptoken)

        self.setup_stack() # clean up the stack

        if self.res_type == 'i':
            r = self.cpu.get_latest_value_int(0)
        elif self.res_type == 'f':
            r = self.cpu.get_latest_value_float(0)
        elif self.res_type == 'p':
            r = self.cpu.get_latest_value_ref(0)
        elif self.res_type == 'v':
            r = None
        else:
            raise ValueError(self.res_type)
        return r # XXX can't return various types

    def setup_stack(self):
        self.esp = 1 # 0 is funcaddr

    def push_funcaddr(self, value):
        self.cpu.set_future_value_int(0, value)
        #self.esp += 1

    def push_int(self, value):
        self.cpu.set_future_value_int(self.esp, value)
        self.esp += 1

    def push_float(self, value):
        self.cpu.set_future_value_float(self.esp, value)
        self.esp += 1

    def push_ref(self, value):
        self.cpu.set_future_value_ref(self.esp, value)
        self.esp += 1

class _Func(object):
    def __init__(self, args_type, res_type, looptoken):
        self.args_type = args_type
        self.res_type = res_type
        self.looptoken = looptoken
