from pypy.interpreter.baseobjspace import ObjSpace, W_Root, Wrappable
from pypy.interpreter.error import operationerrfmt
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef
from pypy.rlib import libffi
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.jit.backend.x86.runner import CPU
from pypy.jit.metainterp.history import LoopToken, BasicFailDescr, BoxInt
from pypy.jit.metainterp.resoperation import ResOperation, rop
from pypy.jit.metainterp.typesystem import deref

class W_CDLL(Wrappable):
    def __init__(self, space, name):
        try:
            self.cdll = libffi.CDLL(name)
        except libffi.DLOpenError, e:
            raise operationerrfmt(space.w_OSError, '%s: %s', name,
                                  e.msg or 'unspecified error')
        self.name = name
        self.space = space
        self.cpu = CPU(None, None)

    def call(self, space, func, a, b):  # XXX temporary fixed number of func args (ints)
                                        # result_type argument?
        try:
            addr = rffi.cast(lltype.Signed, self.cdll.getaddressindll(func))
        except KeyError:
            raise operationerrfmt(space.w_ValueError,
                                  "Cannot find symbol %s", func)

        bfuncaddr = BoxInt(addr)
        barg0 = BoxInt(a)
        barg1 = BoxInt(b)
        bres = BoxInt()

        FPTR = lltype.Ptr(lltype.FuncType([lltype.Signed, lltype.Signed],
                          lltype.Signed))
        FUNC = deref(FPTR)
        calldescr = self.cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT)

        oplist = [ResOperation(rop.CALL, [bfuncaddr, barg0, barg1], bres,
                               descr=calldescr),
                  ResOperation(rop.FINISH, [bres], None,
                               descr=BasicFailDescr(0))]
        inputargs = [bfuncaddr, barg0, barg1]
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
        return space.wrap(BoxInt(self.cpu.get_latest_value_int(0)).getint())
    call.unwrap_spec = ['self', ObjSpace, str, int, int]

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
