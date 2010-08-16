from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    interpleveldefs = {
        '__version__' : 'space.wrap("1.0.3")',
        'dlopen' : 'interp_dll.W_CDLL',
        'Test' : 'interp_test.W_Test',
    }
    appleveldefs = {}
