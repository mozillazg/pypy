
from pypy.interpreter.mixedmodule import MixedModule 

class Module(MixedModule):
    """An itertools module."""

    interpleveldefs = {
        'count'    : 'interp_itertools.W_Count',
    }

    appleveldefs = {
    }
