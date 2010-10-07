from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):

    interpleveldefs = {
        'CDLL'               : 'interp_ffi.W_CDLL',
#        'FuncPtr'            : 'interp_ffi.W_FuncPtr',
    }

    appleveldefs = {}
