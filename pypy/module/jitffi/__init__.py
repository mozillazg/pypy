from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    interpleveldefs = {
        'CDLL' : 'interp_jitffi.W_CDLL',
        'Test' : 'interp_jitffi.W_Test',
    }

    appleveldefs = {}
