import _ffi

class CFuncPtrType(type):
    pass

class CFuncPtr(object):
    __metaclass__ = CFuncPtrType
    argtypes = None
    _argtypes = None
    restype = None
    _restype = None
    def __init__(self, stuff):
        if isinstance(stuff, tuple):
            print stuff
            name, dll = stuff
            self.name = name
            self.dll = dll
            self._funcptr = None
        else:
            self.name = None
            self.dll = None

    def __call__(self, *args):
        assert self.argtypes is not None #XXX for now
        assert self.restype is not None #XXX for now
        if len(args) != len(self.argtypes):
            raise TypeError("%s takes %s arguments, given %s" % (self.name,
                len(self.argtypes), len(args)))
        return self._getfuncptr()(*args)

    def _getfuncptr(self):
        if self._funcptr is not None:
            if (self.argtypes is self._argtypes
                and self.restype is self._restype):
                return self._funcptr
        argtps = [argtype._type_ for argtype in self.argtypes]
        restp = self.restype._type_
        self._funcptr = funcptr = self.dll._handle.ptr(self.name, argtps, restp)
        self._argtypes = self.argtypes
        self._restype = self.restype
        return funcptr
