"""

Helpers to build extension modules.

"""

from pypy.interpreter import gateway
from pypy.interpreter.miscutils import InitializedClass, RwDictProxy
from pypy.interpreter.module import Module


class ExtModule(Module):
    """An empty extension module.
    Non-empty extension modules are made by subclassing ExtModule."""

    def __init__(self, space):
        Module.__init__(self, space, space.wrap(self.__name__))
        
        # to build the dictionary of the module we get all the objects
        # accessible as 'self.xxx'. Methods are bound.
        d = {}
        for cls in self.__class__.__mro__:
            for name, value in cls.__dict__.iteritems():
                # ignore names in '_xyz'
                if not name.startswith('_') or name.endswith('_'):
                    if isinstance(value, gateway.Gateway):
                        name = value.name
                        value = value.__get__(self)  # get a Method
                    else:
                        if hasattr(value, '__get__'):
                            continue  # ignore CPython functions
                    if name not in d:
                        d[name] = value
        for key, value in d.iteritems():
            space.setitem(self.w_dict, space.wrap(key), space.wrap(value))

    __metaclass__ = InitializedClass
    def __initclass__(cls):
        gateway.exportall(RwDictProxy(cls))   # xxx() -> app_xxx()
        gateway.importall(RwDictProxy(cls))   # app_xxx() -> xxx()
