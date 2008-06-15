
from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    applevelname = '_ctypes'

    interpleveldefs = {
        'dlopen'          : 'interp_lib.W_CDLL',
    }

    appleveldefs = {
        '_SimpleCData'    : 'app_stubs._SimpleCData',
    }
