# NOT_RPYTHON
import cppyy

class _gbl(object):
    """Global C++ namespace, i.e. ::."""

    def __getattr__(self, attr):
        raise AttributeError

class CppyyClass(object):
    def __init__(self, cppclass):
        # fill dictionary
       pass


def get_cppclass(name):
    # lookup class

    # if failed, create

    # create base classes
    pass


_loaded_shared_libs = {}
def load_lib(name):
    try:
        return _loaded_shared_libs[name]
    except KeyError:
        lib = cppyy._load_lib(name)
        _loaded_shared_libs[name] = lib
        return lib
    

# user interface objects
gbl = _gbl()
