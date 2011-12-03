# Package initialisation
from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    """
    This module implements marshal at interpreter level.
    """
    applevel_name = 'marshal'

    appleveldefs = {
    }
    
    interpleveldefs = {
        'dump'    : 'interp_marshal.dump',
        'dumps'   : 'interp_marshal.dumps',
        'load'    : 'interp_marshal.load',
        'loads'   : 'interp_marshal.loads',
        'version' : 'space.wrap(interp_marshal.Py_MARSHAL_VERSION)',
    }
