from pypy.interpreter.baseobjspace import ObjSpace, W_Root, Wrappable
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

class W_CDLL(Wrappable):
    def __init__(self, space, name):
        try:
            self.lib = rdynload.dlopen(name)
        except libffi.DLOpenError, e:
            raise operationerrfmt(space.w_OSError, '%s: %s', name,
                                  e.msg or 'unspecified error')
        self.name = name
        self.space = space
        self.cpu = CPU(None, None)

    def call(self, space, func, w_func_args, res_type='void'):
        # only integers are supported for now
        func_args_w = space.listview(w_func_args)
        assert isinstance(func_args_w, list)

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

        args_type = [ lltype.Signed for i in func_args_w ]
        FPTR = lltype.Ptr(lltype.FuncType(args_type, lltype.Signed))
        FUNC = deref(FPTR)
        calldescr = self.cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT)

        bargs = [ BoxInt(x.intval) for x in func_args_w ]
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
        return space.wrap(r)
    call.unwrap_spec = ['self', ObjSpace, str, W_Root, str]

def descr_new_cdll(space, w_type, name):
    try:
        return space.wrap(W_CDLL(space, name))
    except OSError, e:
        raise wrap_oserror(space, e)
descr_new_cdll.unwrap_spec = [ObjSpace, W_Root, str]

W_CDLL.typedef = TypeDef(
    'CDLL',
    __new__     = interp2app(descr_new_cdll),
    call        = interp2app(W_CDLL.call),
    __doc__     = """ C Dynamically loaded library
use CDLL(libname) to create a handle to a C library (the argument is processed
the same way as dlopen processes it)."""
)
