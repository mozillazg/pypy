import py

from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    applevel_name = '__builtin__random'

    appleveldefs = {}

    interpleveldefs = {
        'Random'          : 'interp_random.W_Random',
        }
