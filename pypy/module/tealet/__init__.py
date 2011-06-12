from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    """Tealets.  XXX document me"""

    appleveldefs = {
    }

    interpleveldefs = {
        'Tealet'    : 'interp_tealet.W_Tealet',
        'MainTealet': 'interp_tealet.W_MainTealet',
        'error'     : 'space.fromcache(interp_tealet.Cache).w_error',
    }
