from pypy.rlib import rdynload
from pypy.jit.backend.x86.runner import CPU
from pypy.rlib import rjitffi
from pypy.interpreter.baseobjspace import ObjSpace, W_Root, Wrappable
from pypy.interpreter.error import wrap_oserror
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef

class W_Lib(Wrappable):
    def __init__(self, space, name):
        try:
            self.handler = rdynload.dlopen(name)
        except rdynload.DLOpenError, e:
            raise OSError('%s: %s', name, e.msg or 'unspecified error')

        self.space = space

def descr_new_lib(space, w_type, name):
    try:
        return space.wrap(W_Lib(space, name))
    except OSError, e:
        raise wrap_oserror(space, e)
descr_new_lib.unwrap_spec = [ObjSpace, W_Root, str]

W_Lib.typedef = TypeDef(
        'Lib',
        __new__ = interp2app(descr_new_lib)
)

class W_Get(Wrappable, rjitffi._Get):
    def __init__(self, space, cpu, lib, func, args_type, res_type='void'):
        self.space = space
        rjitffi._Get.__init__(self, cpu, lib, func, args_type, res_type)

    def call_w(self, w_args):
        args_w = [ self.space.int_w(w_x) for w_x in self.space.listview(w_args) ] # XXX only int!
        return self.space.wrap(self.call(args_w))


def descr_new_get(space, w_type, cpu, lib, func, args_type, res_type):
    try:
        return space.wrap(W_Get(space, w_type, cpu, lib, func, args_type, res_type))
    except OSError, e:
        raise wrap_oserror(space, e)
descr_new_get.unwrap_spec = [ObjSpace, W_Root, W_Root, W_Root, str, W_Root, str]

W_Get.typedef = TypeDef(
        'Get',
        #__new__ = interp2app(descr_new_get)
        call = interp2app(W_Get.call_w, unwrap_spec=['self', W_Root])
)

class W_CDLL(Wrappable, rjitffi.CDLL):
    def __init__(self, space, name):
        self.space = space
        self.lib = space.wrap(W_Lib(self.space, name))
        self.name = name
        self.cpu = CPU(None, None)

    def get_w(self, func, w_args_type, res_type='void'):
        args_type_w = [ self.space.str_w(w_x)
                        for w_x in self.space.listview(w_args_type) ]
        return self.space.wrap(W_Get(self.space, self.cpu, self.space.wrap(self.lib), func, args_type_w, res_type))

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
