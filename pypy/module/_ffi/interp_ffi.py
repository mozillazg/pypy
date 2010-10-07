import sys
from pypy.interpreter.baseobjspace import W_Root, ObjSpace, Wrappable, Arguments
from pypy.interpreter.error import OperationError, wrap_oserror, operationerrfmt
from pypy.interpreter.gateway import interp2app, NoneNotWrapped
from pypy.interpreter.typedef import TypeDef, GetSetProperty

from pypy.rlib.libffi import CDLL
from pypy.rlib.rdynload import DLOpenError

class W_CDLL(Wrappable):
    def __init__(self, space, name):
        try:
            self.cdll = CDLL(name)
        except DLOpenError, e:
            raise operationerrfmt(space.w_OSError, '%s: %s', name,
                                  e.msg or 'unspecified error')
        self.name = name
        self.space = space



def descr_new_cdll(space, w_type, name):
    return space.wrap(W_CDLL(space, name))
descr_new_cdll.unwrap_spec = [ObjSpace, W_Root, str]

W_CDLL.typedef = TypeDef(
    'CDLL',
    __new__     = interp2app(descr_new_cdll),
    )
