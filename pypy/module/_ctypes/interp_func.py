
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
        self.restype = 'i'
        self.argtypes = []
        self.has_argtypes = False
        self._regen_handle()

    def _regen_handle(self):
        args = [TYPEMAP[i] for i in self.argtypes]
        res = TYPEMAP[self.restype]
        self.handle = self.lib.getpointer(self.name, args, res)

    def _guess_argtypes(self, args_w):
        # XXX
        return ['d']

    def call(self, space, args):
        """ Calling routine - note that we cache handle to ll
        lib, in order to speed up calls. In case arguments or restype
        is defined, we invalidate a cache and call new handle
        """
        assert not self.has_argtypes
        if args:
            args_w, kwds_w = args.unpack()
            if kwds_w:
                raise OperationError(space.w_ValueError, space.wrap(
                    "Cannot pass keyword arguments to C function"))
            if args_w:
                argtypes = self._guess_argtypes(args_w)
                if self.argtypes != argtypes:
                    self.argtypes = argtypes
                    self._regen_handle()
                for arg in args_w:
                    self.handle.push_arg(space.float_w(arg))
        if self.restype == 'i':
            return space.wrap(self.handle.call(lltype.Signed))
        elif self.restype == 'd':
            return space.wrap(self.handle.call(lltype.Float))
        else:
            raise NotImplementedError("restype = %s" % self.restype)
    call.unwrap_spec = ['self', ObjSpace, Arguments]

    def getargtypes(space, self):
        xxx

    def setargtypes(space, self, w_value):
        xxx

    def getrestype(space, self):
        return self.w_restype

    def setrestype(space, self, w_value):
        # XXX isinstance check here
        restype = space.str_w(space.getattr(w_value, space.wrap('_type_')))
        if len(restype) != 1 or restype[0] not in TYPEMAP:
            raise OperationError(space.w_TypeError, space.wrap(
                "Unknown type %d" % restype))
        self.w_restype = w_value
        self.restype = restype[0]
        self._regen_handle()

W_FuncPtr.typedef = TypeDef(
    '_FuncPtr',
    __call__ = interp2app(W_FuncPtr.call),
    restype = GetSetProperty(W_FuncPtr.getrestype, W_FuncPtr.setrestype),
    argtypes = GetSetProperty(W_FuncPtr.getargtypes, W_FuncPtr.setargtypes),
)
