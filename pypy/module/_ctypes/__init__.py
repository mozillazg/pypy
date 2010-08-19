from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    interpleveldefs = {
        'dlopen' : 'interp_dll.W_CDLL',
        'Test' : 'interp_test.W_Test',
    }
    appleveldefs = {
        'ArgumentError' : 'app_basics.ArgumentError',
        '_SimpleCData' : 'app_dummy._SimpleCData',
        '_Pointer' : 'app_dummy._Pointer',
        'CFuncPtr' : 'app_dummy.CFuncPtr',
        'Union' : 'app_dummy.Union',
        'Structure' : 'app_dummy.Structure',
        'Array' : 'app_dummy.Array',
        'sizeof' : 'app_dummy.sizeof',
        'byref' : 'app_dummy.byref',
        'addressof' : 'app_dummy.addressof',
        'alignment' : 'app_dummy.alignment',
        'resize' : 'app_dummy.resize',
        '_memmove_addr' : 'app_dummy._memmove_addr',
        '_memset_addr' : 'app_dummy._memset_addr',
        '_cast_addr' : 'app_dummy._cast_addr',
        '_string_at' : 'app_dummy._string_at',
    }

    def buildloaders(cls):
        from pypy.module._ctypes.constants import constants
        for constant, value in constants.iteritems():
            Module.interpleveldefs[constant] = 'space.wrap(%r)' % value

        from pypy.rlib import rjitffi
        for name in ['FUNCFLAG_STDCALL',
                     'FUNCFLAG_CDECL',
                     'FUNCFLAG_PYTHONAPI',
                    ]:
            if hasattr(rjitffi, name):
                Module.interpleveldefs[name] = \
                                    "space.wrap(%r)" % getattr(rjitffi, name)

        super(Module, cls).buildloaders()
    buildloaders = classmethod(buildloaders)
