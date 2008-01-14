
import _rawffi

class _CDataMeta(type):
    def from_param(self, value):
        if isinstance(value, self):
            return value
        try:
            as_parameter = value._as_parameter_
        except AttributeError:
            raise TypeError("expected %s instance instead of %s" % (
                self.__name__, type(value).__name__))
        else:
            return self.from_param(as_parameter)

    def _CData_input(self, value):
        """Used when data enters into ctypes from user code.  'value' is
        some user-specified Python object, which is converted into an
        _array of length 1 containing the same value according to the
        type 'self'.
        """
        return self.from_param(value)._array

    def _CData_output(self, resarray):
        """Used when data exits ctypes and goes into user code.
        'resarray' is an _array of length 1 containing the value,
        and this returns a general Python object that corresponds.
        """
        res = self.__new__(self)
        res._array = resarray
        return res.__ctypes_from_outparam__()

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
    return _rawffi.sizeof(TP_TO_FFITP.get(ffitp, ffitp))

def alignment(tp):
    ffitp = tp._type_
    return _rawffi.alignment(TP_TO_FFITP.get(ffitp, ffitp))

def byref(cdata):
    from ctypes import pointer
    return pointer(cdata)

def cdata_from_address(self, address):
    instance = self.__new__(self)
    lgt = getattr(self, '_length_', 1)
    instance._array = self._ffiarray.fromaddress(address, lgt)
    return instance

def addressof(tp):
    # XXX we should have a method on each..
    return tp._array.buffer
