# Package initialisation
from pypy.interpreter.mixedmodule import MixedModule


class Module(MixedModule):

    appleveldefs = {
    }

    interpleveldefs = {
        'array':        'interp_array.W_WrappedArray',
        '_new_array':   'interp_array.new_array',
        'simple_array': 'interp_simple.simple_array',
    }
