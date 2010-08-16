from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    interpleveldefs = {
        'dlopen' : 'interp_dll.W_CDLL',
        'Test' : 'interp_test.W_Test',
    }
    appleveldefs = {}

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
