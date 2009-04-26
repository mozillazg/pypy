from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    interpleveldefs = {
        'invokeMethod'    : 'interp_test.invokeMethod',
    }

    appleveldefs = {
    }

