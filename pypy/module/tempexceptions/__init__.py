
from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    applevel_name = 'tempexceptions'

    appleveldefs = {}
    
    interpleveldefs = {
        'BaseException' : 'interp_exceptions.W_BaseException',
        'Exception' : 'interp_exceptions.W_Exception',
        }
