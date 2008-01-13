import _ffi

SIMPLE_TYPE_CHARS = "cbBhHiIlLdfuzZqQPXOv"

from _ctypes.basics import _CData, CArgObject, TP_TO_FFITP

class NULL(object):
    pass
NULL = NULL()

TP_TO_DEFAULT = {
        'c': 0,
        'b': 0,
        'B': 0,
        'h': 0,
        'H': 0,
        'i': 0,
        'I': 0,
        'l': 0,
        'L': 0,
        'q': 0,
        'Q': 0,
        'f': 0.0,
        'd': 0.0,
        'P': None,
        # not part of struct
        'O': NULL,
        'z': None,
}
 
DEFAULT_VALUE = object()

class SimpleType(type):
    def __new__(self, name, bases, dct):
        tp = dct['_type_']
        if (not isinstance(tp, str) or
            not len(tp) == 1 or
            tp not in SIMPLE_TYPE_CHARS):
            raise ValueError('%s is not a type character' % (tp))
        default = TP_TO_DEFAULT[tp]
        ffitp = TP_TO_FFITP.get(tp, tp)
        ffiarray = _ffi.Array(ffitp)
        def __init__(self, value=DEFAULT_VALUE, address=DEFAULT_VALUE):
            if address is not DEFAULT_VALUE:
                self._array = ffiarray.fromaddress(address, 1)
            else:
                self._array = ffiarray(1)
                if value is not DEFAULT_VALUE:
                    self._array[0] = value
        dct['__init__'] = __init__
        result = type.__new__(self, name, bases, dct)
        result._ffiletter = tp
        result._ffiarray = ffiarray
        return result

    def from_address(self, address):
        return self(address=address)        

    def __mul__(self, other):
        pass

    def from_param(self, value):
        return self(value)._as_ffi()

class _SimpleCData(_CData):
    __metaclass__ = SimpleType
    _type_ = 'i'

    def _getvalue(self):
        return self._array[0]

    def _setvalue(self, val):
        self._array[0] = value
    value = property(_getvalue, _setvalue)

    def _as_ffi(self):        
        return CArgObject(self._type_, self.value, type(self))

    def __repr__(self):
        return "%s(%s)" % (type(self).__name__, self.value)
