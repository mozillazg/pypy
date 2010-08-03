from pypy.rlib import rdynload
from pypy.rlib.jit import get_cpu
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.jit.backend.llsupport import descr, symbolic
from pypy.jit.metainterp.history import LoopToken, BasicFailDescr
from pypy.jit.metainterp.history import BoxInt, BoxFloat, NULLBOX
from pypy.jit.metainterp.resoperation import ResOperation, rop
from pypy.jit.metainterp.typesystem import deref

GLOBAL_CPU = get_cpu()

class CDLL(object):
    def __init__(self, name, load=True):
        if load:
            self.lib = _LibHandler(name)
        else:
            self.lib = None

        self.name = name
        self.cpu = GLOBAL_CPU

    def get(self, func, args_type, res_type='v', push_result=None):
        return _Get(self.cpu, self.lib, func, args_type, res_type, push_result)

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
    def __init__(self, cpu, lib, func, args_type, res_type='v',
                 push_result=None, cache=False):
        assert isinstance(args_type, list)
        self.args_type = args_type
        self.res_type = res_type
        self.push_result = push_result
        self.cpu = cpu
        self.bargs = []
        lib = lib.handler

        try:
            self.funcaddr = rffi.cast(lltype.Signed, rdynload.dlsym(lib, func))
        except KeyError:
            raise ValueError("Cannot find symbol %s", func)
        self.bargs.append(BoxInt())
        if not cache:
            self.gen_looptaken()
        self.setup_stack()

    def gen_looptaken(self):
        for arg in self.args_type:
            if arg == 'i':
                self.bargs.append(BoxInt())
            elif arg == 'f':
                self.bargs.append(BoxFloat())
            else:
                raise ValueError(arg)

        if self.res_type == 'i':
            bres = BoxInt()
        elif self.res_type == 'f':
            bres = BoxFloat()
        elif self.res_type == 'v':
            bres = NULLBOX
        else:
            raise ValueError(self.res_type)

        calldescr = self.get_calldescr()
        self.looptoken = LoopToken()
        # make sure it's not resized before ResOperation
        self.bargs = list(self.bargs) 
        oplist = [ResOperation(rop.CALL, self.bargs, bres, descr=calldescr),
                  ResOperation(rop.FINISH, [bres], None,
                               descr=BasicFailDescr(0))]
        self.cpu.compile_loop(self.bargs, oplist, self.looptoken)

    def get_calldescr(self):
        if self.res_type == 'i':
            cls = SignedCallDescr
        elif self.res_type == 'f':
            cls = descr.FloatCallDescr
        elif self.res_type == 'v':
            cls = descr.VoidCallDescr
        else:
            raise NotImplementedError('Unknown type of descr: %s'
                                      % self.res_type)

        arg_classes = ''.join(self.args_type)
        calldescr = cls(arg_classes)
        return calldescr

    def call(self):
        self.cpu.execute_token(self.looptoken)

        if self.res_type == 'i':
            r = self.push_result(self.cpu.get_latest_value_int(0))
        elif self.res_type == 'f':
            r = self.push_result(self.cpu.get_latest_value_float(0))
        elif self.res_type == 'v':
            r = None
        else:
            raise ValueError(self.res_type)
        
        self.setup_stack() # clean up the stack
        return r

    def setup_stack(self):
        self.esp = 0
        self.push_funcaddr(self.funcaddr)

    def push_int(self, value):
        self.cpu.set_future_value_int(self.esp, value)
        self.esp += 1
    push_funcaddr = push_int

    def push_float(self, value):
        self.cpu.set_future_value_float(self.esp, value)
        self.esp += 1

# ____________________________________________________________
# CallDescrs

class SignedCallDescr(descr.BaseIntCallDescr):
    _clsname = 'SignedCallDescr'
    def get_result_size(self, translate_support_code):
        return symbolic.get_size(lltype.Signed, translate_support_code)
