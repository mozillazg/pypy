from pypy.interpreter.mixedmodule import MixedModule 

class Module(MixedModule):
    """A demo built-in module based on rffi."""
    applevel_name = '__builtin_crypt'

    interpleveldefs = {
        'crypt'    : 'interp_crypt.crypt',
    }

    appleveldefs = {
    }
