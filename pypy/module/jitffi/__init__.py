from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    interpleveldefs = {
        'load' : 'interp_jitffi.W_load',
    }

    appleveldefs = {}
