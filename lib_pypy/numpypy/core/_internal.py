#A place for code to be called from C-code
#  that implements more complicated stuff.

def _getintp_ctype():
    from _numpypy import dtype
    val = _getintp_ctype.cache
    if val is not None:
        return val
    char = dtype('p').char
    import ctypes
    if (char == 'i'):
        val = ctypes.c_int
    elif char == 'l':
        val = ctypes.c_long
    elif char == 'q':
        val = ctypes.c_longlong
    else:
        val = ctypes.c_long
    _getintp_ctype.cache = val
    return val
_getintp_ctype.cache = None

# Used for .ctypes attribute of ndarray

class _missing_ctypes(object):
    def cast(self, num, obj):
        return num

    def c_void_p(self, num):
        return num

class _ctypes(object):
    def __init__(self, array, ptr=None):
        try:
            import ctypes
            self._ctypes = ctypes
        except ImportError:
            self._ctypes = _missing_ctypes()
        self._arr = array
        self._data = ptr
        if self._arr.ndim == 0:
            self._zerod = True
        else:
            self._zerod = False

    def data_as(self, obj):
        return self._ctypes.cast(self._data, obj)

    def shape_as(self, obj):
        if self._zerod:
            return None
        return (obj*self._arr.ndim)(*self._arr.shape)

    def strides_as(self, obj):
        if self._zerod:
            return None
        return (obj*self._arr.ndim)(*self._arr.strides)

    def get_data(self):
        return self._data

    def get_shape(self):
        if self._zerod:
            return None
        return (_getintp_ctype()*self._arr.ndim)(*self._arr.shape)

    def get_strides(self):
        if self._zerod:
            return None
        return (_getintp_ctype()*self._arr.ndim)(*self._arr.strides)

    def get_as_parameter(self):
        return self._ctypes.c_void_p(self._data)

    data = property(get_data, None, doc="c-types data")
    shape = property(get_shape, None, doc="c-types shape")
    strides = property(get_strides, None, doc="c-types strides")
    _as_parameter_ = property(get_as_parameter, None, doc="_as parameter_")
