# NOT_RPYTHON
import cppyy


class CppyyClass(type):
     pass

class CppyyObject(object):
    def __init__(self, *args):
        print '__init__ called', args
        self._cppinstance = self._cppyyclass.construct(*args)
        
    def destruct(self):
        self._cppinstance.destruct()


def make_static_function(cpptype, name):
    def method(*args):
        return cpptype.invoke(name, *args)
    method.__name__ = name
    return staticmethod(method)

def make_method(name, rettype):
    if rettype is None:                          # return builtin type
        def method(self, *args):
            return self._cppinstance.invoke(name, *args)
        method.__name__ = name
        return method
    else:                                        # return instance
        def method(self, *args):
            result = self._cppinstance.invoke(name, *args)
            if not result is None:
                bound_result = object.__new__(get_cppclass(rettype))
                bound_result._cppinstance = result
            return bound_result
        method.__name__ = name
        return method


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
            d[f] = make_method(f, cppol.get_returntype())

    pycpptype = CppyyClass(name, (CppyyObject,), d)

    return pycpptype

#    raise TypeError("no such C++ class %s" % name)


class _gbl(object):
    """Global C++ namespace, i.e. ::."""

    def __getattr__(self, attr):
        try:
            cppclass = get_cppclass(attr)
            self.__dict__[attr] = cppclass
            return cppclass
        except TypeError, e:
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
