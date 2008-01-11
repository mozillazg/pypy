
import _ffi
from _ctypes.basics import _CData
from _ctypes.param import CArgObject

DEFAULT_VALUE = object()

class PointerType(type):
    def __new__(self, name, cls, typedict):
        d = dict(
            size       = _ffi.sizeof('P'),
            align      = _ffi.alignment('P'),
            length     = 1,
            _ffiletter = 'P'
        )
        # XXX check if typedict['_type_'] is any sane
        # XXX remember about paramfunc
        obj = type.__new__(self, name, cls, typedict)
        for k, v in d.iteritems():
            setattr(obj, k, v)
        if '_type_' in typedict:
            ffiarray = _ffi.Array(typedict['_type_']._ffiletter)
            def __init__(self, value=0, address=DEFAULT_VALUE):
                if address is not DEFAULT_VALUE:
                    self._array = ffiarray.fromaddress(address, 1)
                elif value == 0:
                    # null pointer
                    self._array = ffiarray.fromaddress(0, 1)
                else:
                    self._array = ffiarray.fromaddress(value._array.buffer, 1)
            obj._ffiarray = ffiarray
        else:
            def __init__(self, value=0):
                raise TypeError("%s has no type" % obj)
        obj.__init__ = __init__
        return obj

    def from_param(self, param):
        # XXX think deeper about that
        if isinstance(param, CArgObject):
            return param
        else:
            return self(address=param._array.buffer)._as_ffi()

class _Pointer(_CData):
    __metaclass__ = PointerType

    def getvalue(self):
        return self._array

    value = property(getvalue)

    def getcontents(self):
        return self._type_.from_address(self._array.buffer)

    def setcontents(self, value):
        self._array = self._ffiarray.fromaddress(value._array.buffer, 1)

    def _as_ffi(self):
        return CArgObject('P', self._array, type(self))

    def __getitem__(self, item):
        return self._array[item]

    def __setitem__(self, item, value):
        self._array[item] = value

    contents = property(getcontents, setcontents)
