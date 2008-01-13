
import _ffi

from _ctypes.basics import _CData, cdata_from_address, _CDataMeta

class ArrayMeta(_CDataMeta):
    def __new__(self, name, cls, typedict):
        res = type.__new__(self, name, cls, typedict)
        res._ffiletter = 'P'
        if '_type_' in typedict:
            ffiarray = _ffi.Array(typedict['_type_']._ffiletter)
            res._ffiarray = ffiarray
            if typedict['_type_']._type_ == 'c':
                def getvalue(self):
                    res = []
                    i = 0
                    while i < self._length_ and self[i] != '\x00':
                        res.append(self[i])
                        i += 1
                    return "".join(res)
                def setvalue(self, val):
                    # we don't want to have buffers here
                    import ctypes
                    if len(val) > self._length_:
                        raise ValueError("%s too long" % (val,))
                    for i in range(len(val)):
                        self[i] = val[i]
                    if len(val) < self._length_:
                        self[len(val)] = '\x00'
                res.value = property(getvalue, setvalue)

                def getraw(self):
                    return "".join([self[i] for i in range(self._length_)])

                def setraw(self, buffer):
                    for i in range(len(buffer)):
                        self[i] = buffer[i]
                res.raw = property(getraw, setraw)
        else:
            res._ffiarray = None
        return res

    from_address = cdata_from_address

class Array(_CData):
    __metaclass__ = ArrayMeta

    def __init__(self, *args):
        self._array = self._ffiarray(self._length_)
        for i, arg in enumerate(args):
            self[i] = arg

    def _fix_item(self, item):
        if item >= self._length_:
            raise IndexError
        if item < 0:
            return self._length_ + item
        return item

    def _get_slice_params(self, item):
        if item.step is not None:
            raise TypeError("3 arg slices not supported (for no reason)")
        start = item.start or 0
        stop = item.stop or self._length_
        return start, stop
    
    def _slice_setitem(self, item, value):
        start, stop = self._get_slice_params(item)
        for i in range(start, stop):
            self[i] = value[i - start]

    def _slice_getitem(self, item):
        start, stop = self._get_slice_params(item)
        return "".join([self[i] for i in range(start, stop)])
    
    def __setitem__(self, item, value):
        from ctypes import _SimpleCData
        if isinstance(item, slice):
            self._slice_setitem(item, value)
            return
        value = self._type_.from_param(value).value
        item = self._fix_item(item)
        if self._type_._ffiletter == 'c' and len(value) > 1:
            raise TypeError("Expected strings of length 1")
        self._array[item] = value

    def __getitem__(self, item):
        if isinstance(item, slice):
            return self._slice_getitem(item)
        item = self._fix_item(item)
        return self._array[item]

    def __len__(self):
        return self._length_

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
