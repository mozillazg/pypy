
import _ffi

from _ctypes.basics import _CData

class ArrayMeta(type):
    def __new__(self, name, cls, typedict):
        res = type.__new__(self, name, cls, typedict)
        res._ffiletter = 'P'
        if '_type_' in typedict:
            ffiarray = _ffi.Array(typedict['_type_']._ffiletter)
            res._ffiarray = ffiarray
        else:
            res._ffiarray = None
        return res

class Array(_CData):
    __metaclass__ = ArrayMeta

    def __init__(self, *args):
        self._array = self._ffiarray(self._length_)
        for i, arg in enumerate(args):
            self[i] = arg

    def __setitem__(self, item, value):
        xxx

    def __getitem__(self, item):
        xxx

ARRAY_CACHE = {}

def create_array_type(base, length):
    key = (base, length)
    try:
        return ARRAY_CACHE[key]
    except KeyError:
        name = "%s_Array_%d" % (base.__name__, length)
        tpdict = dict(
            _length_ = length,
            _type_ = base
        )
        cls = ArrayMeta(name, (Array,), tpdict)
        ARRAY_CACHE[key] = cls
        return cls
