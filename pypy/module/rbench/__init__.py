# Package initialisation
from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    """geninterpreted benchmarks"""
    applevel_name = 'rbench'   # not in standard translations

    appleveldefs = {
        'pystone': 'app_bench.pystone',
        'richards': 'app_bench.richards',
        }
    
    interpleveldefs = {}
