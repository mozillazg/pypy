from pypy.rlib import rjitffi
from pypy.interpreter.baseobjspace import ObjSpace, W_Root, Wrappable
from pypy.interpreter.error import wrap_oserror
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef

class W_CDLL(Wrappable, rjitffi.CDLL):
    def __init__(self, space, name):
        self.space = space
        rjitffi.CDLL.__init__(self, name)

    def get_w(self, func, w_args_type, res_type='void'):
        args_type_w = [ self.space.str_w(w_x)
                        for w_x in self.space.listview(w_args_type) ]
        return self.space.wrap(self.get(func, args_type_w, res_type))

def descr_new_cdll(space, w_type, name):
    try:
        return space.wrap(W_CDLL(space, name))
    except OSError, e:
        raise wrap_oserror(space, e)
descr_new_cdll.unwrap_spec = [ObjSpace, W_Root, str]

W_CDLL.typedef = TypeDef(
        'CDLL',
        __new__ = interp2app(descr_new_cdll),
        get     = interp2app(W_CDLL.get_w, unwrap_spec=['self',
                                                        str, W_Root, str]),
        __doc__ = """ C Dynamically loaded library
use CDLL(libname) to create a handle to a C library (the argument is processed
the same way as dlopen processes it)."""
)
