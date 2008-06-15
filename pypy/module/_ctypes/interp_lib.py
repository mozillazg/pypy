
from pypy.interpreter.baseobjspace import W_Root, ObjSpace, Wrappable, \
     Arguments
from pypy.interpreter.error import OperationError, wrap_oserror
from pypy.interpreter.gateway import interp2app, NoneNotWrapped
from pypy.interpreter.typedef import TypeDef, GetSetProperty

from pypy.rlib.libffi import CDLL

from pypy.module._ctypes.interp_func import W_FuncPtr

class W_CDLL(Wrappable):
    def __init__(self, space, name):
        self.cdll = CDLL(name)
        self.name = name
        self.w_cache = space.newdict()
        self.space = space
        self.cache_w = {}

    def getattr(self, space, name):
        try:
            return self.cache_w[name]
        except KeyError:
            w_val = space.wrap(W_FuncPtr(self.cdll, name))
            self.cache_w[name] = w_val
            return w_val
    getattr.unwrap_spec = ['self', ObjSpace, str]

def descr_new_cdll(space, w_type, name):
    try:
        return space.wrap(W_CDLL(space, name))
    except OSError, e:
        raise wrap_oserror(space, e)
descr_new_cdll.unwrap_spec = [ObjSpace, W_Root, str]

W_CDLL.typedef = TypeDef(
    'CDLL',
    __new__     = interp2app(descr_new_cdll),
    __getattr__ = interp2app(W_CDLL.getattr),
    __doc__     = """ C Dynamically loaded library
use CDLL(libname) to create a handle to a C library (the argument is processed
the same way as dlopen processes it). On such a library you can call:
lib.ptr(func_name, argtype_list, restype)
"""
)
