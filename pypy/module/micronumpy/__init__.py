
from pypy.interpreter.mixedmodule import MixedModule 

class Module(MixedModule):

    applevel_name = 'numpy'
    appleveldefs = {}
    
    interpleveldefs = {
        'array'    : 'ndarray.array',
        'ndarray'  : 'ndarray.ndarray',
        'zeros'    : 'ndarray.zeros',
        'minimum'  : 'ufunc.minimum',
        }

