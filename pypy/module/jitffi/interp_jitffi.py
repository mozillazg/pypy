from pypy.rlib import rdynload
from pypy.rlib import rjitffi
from pypy.interpreter.baseobjspace import ObjSpace, W_Root, Wrappable
from pypy.interpreter.error import OperationError, wrap_oserror
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef

class W_Lib(Wrappable):
    def __init__(self, space, name):
        try:
            self.handler = rdynload.dlopen(name)
        except rdynload.DLOpenError, e:
            raise OSError('%s: %s', name, e.msg or 'unspecified error')

        self.space = space

def W_Lib___new__(space, w_type, name):
    try:
        return space.wrap(W_Lib(space, name))
    except OSError, e:
        raise wrap_oserror(space, e)

W_Lib.typedef = TypeDef(
        'Lib',
        __new__ = interp2app(W_Lib___new__, unwrap_spec=[ObjSpace,W_Root,str])
)

class W_Get(Wrappable, rjitffi._Get):
    def __init__(self, space, cpu, lib, func, args_type, res_type='void'):
        self.space = space
        rjitffi._Get.__init__(self, cpu, lib, func, args_type, res_type)

    def call_w(self, space, w_args=None):
        if space.is_w(w_args, space.w_None):
            return space.wrap(self.call())
        else:
            if self.args_type[0] == 'int':
                args_w = [ space.int_w(w_x) for w_x in space.listview(w_args) ]
            elif self.args_type[0] == 'float':
                args_w = [ space.float_w(w_x) for w_x in space.listview(w_args) ]
            else:
                raise OperationError(
                        space.w_TypeError,
                        space.wrap('Unsupported type of argument: %s'
                                    % self.args_type[0]))

        return space.wrap(self.call(args_w))

def W_Get___new__(space, w_type, cpu, lib, func, args_type, res_type):
    try:
        return space.wrap(W_Get(space, w_type, cpu, lib, func, args_type, res_type))
    except OSError, e:
        raise wrap_oserror(space, e)

W_Get.typedef = TypeDef(
        'Get',
        #__new__ = interp2app(W_Get___new__, unwrap_spec=[ObjSpace, W_Root, W_Root, W_Root, str, W_Root, str]),
        call = interp2app(W_Get.call_w, unwrap_spec=['self', ObjSpace, W_Root])
)

class W_CDLL(Wrappable, rjitffi.CDLL):
    def __init__(self, space, name):
        self.space = space
        rjitffi.CDLL.__init__(self, name)
        # XXX we load a library twice (in super-class and below)
        self.lib_w = W_Lib(self.space, name)

    def get_w(self, space, func, w_args_type, res_type='void'):
        args_type_w = [ space.str_w(w_x)
                        for w_x in space.listview(w_args_type) ]
        return space.wrap(W_Get(space,
                                self.cpu, 
                                space.wrap(self.lib_w),
                                func,
                                args_type_w,
                                res_type))

def W_CDLL___new__(space, w_type, name):
    try:
        return space.wrap(W_CDLL(space, name))
    except OSError, e:
        raise wrap_oserror(space, e)

W_CDLL.typedef = TypeDef(
        'CDLL',
        __new__ = interp2app(W_CDLL___new__,unwrap_spec=[ObjSpace,W_Root,str]),
        get     = interp2app(W_CDLL.get_w, unwrap_spec=['self',
                                                        ObjSpace, str, W_Root, str]),
        __doc__ = """ C Dynamically loaded library
use CDLL(libname) to create a handle to a C library (the argument is processed
the same way as dlopen processes it)."""
)
