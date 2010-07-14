# Package initialisation
from pypy.interpreter.mixedmodule import MixedModule


class Module(MixedModule):

    appleveldefs = {
    }

    interpleveldefs = {
        'array':        'interp_array.W_WrappedArray',
        'simple_array': 'interp_simple.simple_array',
    }
