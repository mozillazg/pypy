import sys
from pypy.interpreter.baseobjspace import W_Root, ObjSpace, Wrappable, Arguments
from pypy.interpreter.error import OperationError, wrap_oserror, operationerrfmt
from pypy.interpreter.gateway import interp2app, NoneNotWrapped
from pypy.interpreter.typedef import TypeDef, GetSetProperty

from pypy.rlib.libffi import CDLL, types
from pypy.rlib.rdynload import DLOpenError

class W_FFIType(Wrappable):
    def __init__(self, name, ffitype):
        self.name = name
        self.ffitype = ffitype

    def str(self, space):
        return space.wrap('<ffi type %s>' % self.name)
    str.unwrap_spec = ['self', ObjSpace]


W_FFIType.typedef = TypeDef(
    'FFIType',
    __str__ = interp2app(W_FFIType.str),
    )


class W_types(Wrappable):
    pass

def build_ffi_types():
    tdict = {}
    for key, value in types.__dict__.iteritems():
        if key.startswith('__'):
            continue
        tdict[key] = W_FFIType(key, value)
    return tdict
    
W_types.typedef = TypeDef(
    'types',
    **build_ffi_types())

# ========================================================================

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

# ========================================================================
