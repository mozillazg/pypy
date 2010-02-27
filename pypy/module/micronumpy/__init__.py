
from pypy.interpreter.mixedmodule import MixedModule 

class Module(MixedModule):

    applevel_name = 'numpy'
    appleveldefs = {}
    
    interpleveldefs = {
        'array'    : 'array.array',
        'ndarray'  : 'array.ndarray',
        'zeros'    : 'array.zeros',
        'minimum'  : 'ufunc.minimum',
        'dot'      : 'ufunc.dot',
        }

