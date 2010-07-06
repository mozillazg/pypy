# Package initialisation
from pypy.interpreter.mixedmodule import MixedModule


class Module(MixedModule):

    appleveldefs = {
    }

    interpleveldefs = {
        'array':       'interp_array.array',
        #'sized_array': 'interp_array.sized_array',
    }
