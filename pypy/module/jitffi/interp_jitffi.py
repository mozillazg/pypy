from pypy.interpreter.baseobjspace import ObjSpace, W_Root, Wrappable
from pypy.interpreter.error import operationerrfmt
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef
from pypy.rlib import libffi
from pypy.rpython.lltypesystem import rffi, lltype

class W_CDLL(Wrappable):
    def __init__(self, space, name):
        try:
            self.cdll = libffi.CDLL(name)
        except libffi.DLOpenError, e:
            raise operationerrfmt(space.w_OSError, '%s: %s', name,
                                  e.msg or 'unspecified error')
        self.name = name
        self.space = space

    def call(self, space, func, a, b): # XXX temporary fixed number of func args
        try:
            addr = rffi.cast(lltype.Unsigned, self.cdll.getaddressindll(func))
        except KeyError:
            raise operationerrfmt(space.w_ValueError,
                                  "Cannot find symbol %s", func)
        # XXX unfinished yet
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
