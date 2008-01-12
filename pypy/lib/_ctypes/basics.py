
import _ffi

class _CData(object):
    """ The most basic object for all ctypes types
    """
    pass

class CArgObject(object):
    def __init__(self, letter, raw_value, _type):
        self.ffiletter = letter
        self.raw_value = raw_value
        self._type = _type

    def __repr__(self):
        return "<cparam '%s' %r>" % (self.ffiletter, self.raw_value)


def sizeof(tp):
    return _ffi.sizeof(tp._type_)

def alignment(tp):
    return _ffi.alignment(tp._type_)

def byref(cdata):
    from ctypes import pointer, _SimpleCData
    if not isinstance(cdata, _SimpleCData):
        raise TypeError("expected CData instance")
    return pointer(cdata)._as_ffi()

