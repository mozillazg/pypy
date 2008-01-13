
import _ffi
from _ctypes.basics import _CData, _CDataMeta, cdata_from_address

DEFAULT_VALUE = object()

class PointerType(_CDataMeta):
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
            ffiarray = _ffi.Array('P')
            def __init__(self, value=0):
                self._array = ffiarray(1)
                self.contents = value
            obj._ffiarray = ffiarray
        else:
            def __init__(self, value=0):
                raise TypeError("%s has no type" % obj)
        obj.__init__ = __init__
        return obj

    from_address = cdata_from_address

class _Pointer(_CData):
    __metaclass__ = PointerType

    def getvalue(self):
        return self._array

    value = property(getvalue)

    def getcontents(self):
        return self._type_.from_address(self._array[0])

    def setcontents(self, value):
        if isinstance(value, int):
            self._array[0] = value
        else:
            self._array[0] = value._array

    def __getitem__(self, item):
        assert item == 0
        return self._type_.from_address(self._array[0]).__ctypes_from_outparam__()

    def __setitem__(self, item, value):
        if item != 0:
            raise IndexError
        self._type_.from_address(self._array[item]).value = value

    contents = property(getcontents, setcontents)
