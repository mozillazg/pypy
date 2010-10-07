import sys
from pypy.interpreter.baseobjspace import W_Root, ObjSpace, Wrappable, Arguments
from pypy.interpreter.error import OperationError, wrap_oserror, operationerrfmt
from pypy.interpreter.gateway import interp2app, NoneNotWrapped, unwrap_spec
from pypy.interpreter.typedef import TypeDef, GetSetProperty
#
from pypy.rpython.lltypesystem import lltype, rffi
#
from pypy.rlib import libffi
from pypy.rlib.rdynload import DLOpenError

class W_FFIType(Wrappable):
    def __init__(self, name, ffitype):
        self.name = name
        self.ffitype = ffitype

    @unwrap_spec('self', ObjSpace)
    def str(self, space):
        return space.wrap('<ffi type %s>' % self.name)



W_FFIType.typedef = TypeDef(
    'FFIType',
    __str__ = interp2app(W_FFIType.str),
    )


class W_types(Wrappable):
    pass

def build_ffi_types():
    from pypy.rlib.clibffi import FFI_TYPE_P
    tdict = {}
    for key, value in libffi.types.__dict__.iteritems():
        if key == 'getkind' or key.startswith('__'):
            continue
        assert lltype.typeOf(value) == FFI_TYPE_P
        tdict[key] = W_FFIType(key, value)
    return tdict
    
W_types.typedef = TypeDef(
    'types',
    **build_ffi_types())

# ========================================================================

class W_FuncPtr(Wrappable):
    def __init__(self, func):
        self.func = func

    @unwrap_spec('self', ObjSpace, 'args_w')
    def call(self, space, args_w):
        assert len(args_w) == len(self.func.argtypes) # XXX: raise OperationError
        argchain = libffi.ArgChain()
        for i in range(len(args_w)):
            argtype = self.func.argtypes[i]
            w_arg = args_w[i]
            kind = libffi.types.getkind(argtype)
            if kind == 'i':
                argchain.arg(space.int_w(w_arg))
            elif kind == 'f':
                argchain.arg(space.float_w(w_arg))
            else:
                assert False # XXX
        #
        reskind = libffi.types.getkind(self.func.restype)
        if reskind == 'i':
            intres = self.func.call(argchain, rffi.LONG)
            return space.wrap(intres)
        elif reskind == 'f':
            floatres = self.func.call(argchain, rffi.DOUBLE)
            return space.wrap(floatres)
        else:
            voidres = self.func.call(argchain, lltype.Void)
            assert voidres is None
            return space.w_None

W_FuncPtr.typedef = TypeDef(
    'FuncPtr',
    __call__ = interp2app(W_FuncPtr.call)
    )



# ========================================================================

class W_CDLL(Wrappable):
    def __init__(self, space, name):
        try:
            self.cdll = libffi.CDLL(name)
        except DLOpenError, e:
            raise operationerrfmt(space.w_OSError, '%s: %s', name,
                                  e.msg or 'unspecified error')
        self.name = name
        self.space = space

    def ffitype(self, w_argtype):
        return self.space.interp_w(W_FFIType, w_argtype).ffitype

    @unwrap_spec('self', ObjSpace, str, W_Root, W_Root)
    def getfunc(self, space, name, w_argtypes, w_restype):
        argtypes = [self.ffitype(w_argtype) for w_argtype in space.listview(w_argtypes)]
        restype = self.ffitype(w_restype)
        func = self.cdll.getpointer(name, argtypes, restype)
        return W_FuncPtr(func)


@unwrap_spec(ObjSpace, W_Root, str)
def descr_new_cdll(space, w_type, name):
    return space.wrap(W_CDLL(space, name))


W_CDLL.typedef = TypeDef(
    'CDLL',
    __new__     = interp2app(descr_new_cdll),
    getfunc     = interp2app(W_CDLL.getfunc),
    )

# ========================================================================
