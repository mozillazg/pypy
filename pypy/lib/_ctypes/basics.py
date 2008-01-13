
import _ffi

class _CDataMeta(type):
    def from_param(self, value):
        if isinstance(value, self):
            return value
        raise TypeError("Wrong type")    

class _CData(object):
    """ The most basic object for all ctypes types
    """
    __metaclass__ = _CDataMeta
    
    def __ctypes_from_outparam__(self):
        return self

#class CArgObject(object):
#    def __init__(self, letter, raw_value, _type):
#        self.ffiletter = letter
#        self._array = raw_value
#        self._type = _type

#    def __repr__(self):
#        return "<cparam '%s' %r>" % (self.ffiletter, self._array[0])


TP_TO_FFITP = {    # XXX this should die; interp_ffi should just accept them
        'O': 'P',
        'z': 's',
}

def sizeof(tp):
    ffitp = tp._type_
    return _ffi.sizeof(TP_TO_FFITP.get(ffitp, ffitp))

def alignment(tp):
    ffitp = tp._type_
    return _ffi.alignment(TP_TO_FFITP.get(ffitp, ffitp))

def byref(cdata):
    from ctypes import pointer, _SimpleCData
    if not isinstance(cdata, _SimpleCData):
        raise TypeError("expected CData instance")
    return pointer(cdata)

def cdata_from_address(self, address):
    instance = self.__new__(self)
    lgt = getattr(self, '_length_', 1)
    instance._array = self._ffiarray.fromaddress(address, lgt)
    return instance

def addressof(tp):
    # XXX we should have a method on each..
    return tp._array.buffer
