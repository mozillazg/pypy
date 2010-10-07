from pypy.interpreter.mixedmodule import MixedModule
from pypy.module._ffi import interp_ffi

class Module(MixedModule):

    interpleveldefs = {
        'CDLL'               : 'interp_ffi.W_CDLL',
#        'FuncPtr'            : 'interp_ffi.W_FuncPtr',
        'types':             'interp_ffi.W_types',
    }

    appleveldefs = {}
