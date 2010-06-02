from pypy.interpreter.error import operationerrfmt
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef
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
