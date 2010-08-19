class DummyClass(object):
    def __init__(self, *args, **kwargs):
        raise NotImplementedError("not-implemented ctypes function")
_Pointer = Union = Structure = Array = DummyClass

class CFuncPtr(object):
    def __init__(self, *args, **kwargs):
        pass

class Meta(object):
    def __init__(self, *args, **kwargs):
        self.__name__ = 'MockObject'
    def __mul__(self, v):
        return 10
    __rmul__ = __mul__
    _type_ = ''
    from_param = None

class _SimpleCData(object):
    __metaclass__ = Meta

def dummyfunc(*args, **kwargs):
    raise NotImplementedError("not-implemented ctypes function")
byref = addressof = alignment = resize = dummyfunc
_memmove_addr = _memset_addr = _cast_addr = dummyfunc
_string_at = dummyfunc

def sizeof(tp):
    return 0
