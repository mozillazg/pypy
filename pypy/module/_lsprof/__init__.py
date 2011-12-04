
""" _lsprof module
"""

from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    applevel_name = '__builtin__lsprof'

    interpleveldefs = {'Profiler':'interp_lsprof.W_Profiler'}

    appleveldefs = {}
