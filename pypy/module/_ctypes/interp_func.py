
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

    def _guess_argtypes(self, space, args_w):
        res = []
        for w_arg in args_w:
            if space.is_true(space.isinstance(w_arg, space.w_int)):
                res.append('i')
            elif space.is_true(space.isinstance(w_arg, space.w_float)):
                res.append('d')
            else:
                raise NotImplementedError("Arg: %s" % str(w_arg))
        return res

    def push_arg(self, space, argtype, w_arg):
        if argtype == 'i':
            self.handle.push_arg(space.int_w(w_arg))
        elif argtype == 'd':
            self.handle.push_arg(space.float_w(w_arg))
        elif argtype == 'f':
            self.handle.push_arg(space.float_w(w_arg))
        else:
            raise NotImplementedError("Argtype %s" % argtype)

    def call(self, space, args_w):
        """ Calling routine - note that we cache handle to ll
        lib, in order to speed up calls. In case arguments or restype
        is defined, we invalidate a cache and call new handle
        """
        if args_w:
            if self.has_argtypes:
                if len(args_w) != len(self.argtypes):
                    raise OperationError(space.w_TypeError, space.wrap(
                        "Expected %d args, got %d" % (len(self.argtypes),
                                                      len(args_w))))
                argtypes = self.argtypes
            else:
                argtypes = self._guess_argtypes(space, args_w)
            if self.argtypes != argtypes:
                self.argtypes = argtypes
                self._regen_handle()
            for i in range(len(argtypes)):
                argtype = argtypes[i]
                w_arg = args_w[i]
                self.push_arg(space, argtype, w_arg)
        if self.restype == 'i':
            return space.wrap(self.handle.call(lltype.Signed))
        elif self.restype == 'd':
            return space.wrap(self.handle.call(lltype.Float))
        else:
            raise NotImplementedError("restype = %s" % self.restype)
    call.unwrap_spec = ['self', ObjSpace, 'args_w']

    def getargtypes(space, self):
        return self.w_argtypes

    def setargtypes(space, self, w_value):
        self.argtypes = [space.getattr(w_arg, space.wrap('_type_')) for
                         w_arg in space.unpackiterable(w_value)]
        self.w_argtypes = w_value

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
