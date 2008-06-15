
from pypy.interpreter.baseobjspace import W_Root, ObjSpace, Wrappable, \
     Arguments
from pypy.interpreter.error import OperationError, wrap_oserror
from pypy.interpreter.gateway import interp2app, NoneNotWrapped
from pypy.interpreter.typedef import TypeDef, GetSetProperty

from pypy.module._rawffi.interp_rawffi import TYPEMAP
from pypy.rpython.lltypesystem import lltype, rffi

class W_FuncPtr(Wrappable):
    def __init__(self, lib, name):
        self.lib = lib
        self.name = name
        # we create initial handle with no args, returning int
        self.handle = self._gethandle([], 'i')

    def _gethandle(self, args, res):
        args = [TYPEMAP[i] for i in args]
        res = TYPEMAP[res]
        return self.lib.getpointer(self.name, args, res)

    def call(self, space, args):
        """ Calling routine - note that we cache handle to ll
        lib, in order to speed up calls. In case arguments or restype
        is defined, we invalidate a cache and call new handle
        """
        return space.wrap(self.handle.call(lltype.Signed))
    call.unwrap_spec = ['self', ObjSpace, Arguments]

W_FuncPtr.typedef = TypeDef(
    '_FuncPtr',
    __call__ = interp2app(W_FuncPtr.call),
)
