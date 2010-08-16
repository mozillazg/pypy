from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    interpleveldefs = {
        'dlopen' : 'interp_dll.W_CDLL',
        'Test'  : 'interp_test.W_Test',
    }
    appleveldefs = {}
