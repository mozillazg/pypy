
from pypy.rlib.objectmodel import specialize

class AppBridgeCache(object):
    w_numpypy_core__methods_module = None
    w__var = None
    w__std = None
    w_array_repr = None
    w_array_str = None

    w_numpypy_core__internal_module = None
    w__ctypes = None

    def __init__(self, space):
        self.w_import = space.appexec([], """():
        def f(module):
            import sys
            __import__(module)
            return sys.modules[module]
        return f
        """)

    @specialize.arg(2, 3)
    def call_method(self, space, module, name, *args):
        module_attr = "w_" + module.replace(".", "_") + "_module"
        meth_attr = "w_" + name
        w_meth = getattr(self, meth_attr)
        if w_meth is None:
            if getattr(self, module_attr) is None:
                w_mod = space.call_function(self.w_import, space.wrap(module))
                setattr(self, module_attr, w_mod)
            w_meth = space.getattr(getattr(self, module_attr), space.wrap(name))
            setattr(self, 'w_' + name, w_meth)
        return space.call_function(w_meth, *args)

def set_string_function(space, w_f, w_repr):
    cache = get_appbridge_cache(space)
    if space.is_true(w_repr):
        cache.w_array_repr = w_f
    else:
        cache.w_array_str = w_f

def get_appbridge_cache(space):
    return space.fromcache(AppBridgeCache)
