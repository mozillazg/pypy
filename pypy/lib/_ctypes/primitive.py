SIMPLE_TYPE_CHARS = "cbBhHiIlLdfuzZqQPXOv"
# type converters
def convert_intlike(val):
    if not isinstance(val, (int, long)):
        raise TypeError("int expected, got %s" % (type(val), ))
    return val

def convert_floatlike(val):
    if not isinstance(val, (float, int, long)):
        raise TypeError("float expected, got %s" % (type(val), ))
    return float(val)

def convert_char(val):
    if not isinstance(val, str) or not len(val) == 1:
        raise TypeError("one character string expected")
    return val

def convert_nothing(val):
    return val


TP_TO_CONVERTER = {
        'c': convert_char,
        'b': convert_intlike,
        'B': convert_intlike,
        'h': convert_intlike,
        'H': convert_intlike,
        'i': convert_intlike,
        'I': convert_intlike,
        'l': convert_intlike,
        'L': convert_intlike,
        'q': convert_intlike,
        'Q': convert_intlike,
        'f': convert_floatlike,
        'd': convert_floatlike,
        'P': convert_nothing, #XXX
        # not part of struct
        'O': convert_nothing,
        'z': convert_nothing, #XXX
}
 

class NULL(object):
    pass
NULL = NULL()

TP_TO_DEFAULT = {
        'c': '\x00',
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
        converter = TP_TO_CONVERTER[tp]
        def __init__(self, value=DEFAULT_VALUE):
            self._value = default
            if value is not DEFAULT_VALUE:
                self.value = value
        dct['__init__'] = __init__
        dct['_converter'] = staticmethod(TP_TO_CONVERTER[tp])
        result = type.__new__(self, name, bases, dct)
        return result

    def __mul__(self, other):
        pass

class _SimpleCData(object):
    __metaclass__ = SimpleType
    _type_ = 'i'
    def from_param(self, *args, **kwargs):
        pass

    def _getvalue(self):
        return self._value

    def _setvalue(self, val):
        self._value = self._converter(val)

    def __repr__(self):
        return "%s(%s)" % (type(self).__name__, self.value)
    value = property(_getvalue, _setvalue)

