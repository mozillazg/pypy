class UnionType(type):
    pass

class Union(object):
    __metaclass__ = UnionType

class Structure(type):
    pass

class Array(type):
    pass

class PointerType(type):
    pass

class _Pointer(object):
    __metaclass__ = PointerType


class ArgumentError(Exception):
    pass


def dummyfunc(*args, **kwargs):
    return None

byref = dummyfunc
addressof = dummyfunc
alignment = dummyfunc
resize = dummyfunc
_memmove_addr = dummyfunc
_memset_addr = dummyfunc
_string_at_addr = dummyfunc
_cast_addr = dummyfunc

