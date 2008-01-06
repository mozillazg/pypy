import _ffi

SIMPLE_TYPE_CHARS = "cbBhHiIlLdfuzZqQPXOv"

class NULL(object):
    pass
NULL = NULL()

TP_TO_FFITP = {
        'O': 'P',
        'z': 's',
}


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
        ffistruct = _ffi.Structure([("value", ffitp)])
        def __init__(self, value=DEFAULT_VALUE):
            self._struct = ffistruct()
            if value is not DEFAULT_VALUE:
                self._struct.value = value
        dct['__init__'] = __init__
        result = type.__new__(self, name, bases, dct)
        result._ffistruct = ffistruct
        return result

    def __mul__(self, other):
        pass

class _SimpleCData(object):
    __metaclass__ = SimpleType
    _type_ = 'i'
    def from_param(cls, *args, **kwargs):
        pass
    from_param = classmethod(from_param)

    def _getvalue(self):
        return self._struct.value

    def _setvalue(self, val):
        self._struct.value = value
    value = property(_getvalue, _setvalue)

    def __repr__(self):
        return "%s(%s)" % (type(self).__name__, self.value)

def sizeof(tp):
    return _ffi.sizeof(tp._type_)

def alignment(tp):
    return _ffi.alignment(tp._type_)
