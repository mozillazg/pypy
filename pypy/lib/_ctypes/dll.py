import _ffi

def dlopen(name, mode):
    # XXX mode is ignored
    if name is None:
        return None # XXX seems to mean the cpython lib
    return _ffi.CDLL(name)
