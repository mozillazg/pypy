# Package initialisation
from pypy.interpreter.mixedmodule import MixedModule


class Module(MixedModule):

    appleveldefs = {
    }

    interpleveldefs = {
        'array':       'interp_array.array',
        'simple_array': 'interp_simple.simple_array',
    }
