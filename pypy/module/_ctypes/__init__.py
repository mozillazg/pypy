
from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    applevelname = '_ctypes'

    interpleveldefs = {
        'CDLL'          : 'interp_lib.W_CDLL',
    }

    appleveldefs = {
    }
