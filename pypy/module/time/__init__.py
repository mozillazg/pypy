# Package initialisation
from pypy.interpreter.mixedmodule import MixedModule

import time

class Module(MixedModule):
    """time module"""
    applevel_name = '__builtin_time'

    appleveldefs = {
    }
    
    interpleveldefs = {
    'clock'    : 'interp_time.clock',
    'time'     : 'interp_time.time_',
    'sleep'    : 'interp_time.sleep',
    }

