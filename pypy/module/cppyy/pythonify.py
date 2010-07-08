# NOT_RPYTHON
import cppyy


class CppyyClass(type):
     pass

def make_static_function(cpptype, name):
    def method(*args):
        return cpptype.invoke(name,*args)
    method.__name__ = name
    return staticmethod(method)

_existing_classes = {}
def get_cppclass(name):
    # lookup class
    try:
        return _existing_classes[name]
    except KeyError:
        pass

    # if failed, create
    # TODO: handle base classes
    cpptype = cppyy._type_byname(name)
    d = {"_cppyyclass" : cpptype}
    for f in cpptype.get_function_members():
        cppol = cpptype.get_overload(f)
        if cppol.is_static():
            d[f] = make_static_function(cpptype, f)
        else:
            pass

    pycpptype = CppyyClass(name, (object,), d)

    return pycpptype

#    raise TypeError("no such C++ class %s" % name)


class _gbl(object):
    """Global C++ namespace, i.e. ::."""

    def __getattr__(self, attr):
        try:
            cppclass = get_cppclass(attr)
            self.__dict__[attr] = cppclass
            return cppclass
        except TypeError:
            raise AttributeError("'gbl' object has no attribute '%s'" % attr)


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
