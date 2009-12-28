
from pypy.interpreter.mixedmodule import MixedModule 

class Module(MixedModule):

    applevel_name = 'numpy'
    appleveldefs = {
        #'array' : 'app_numarray.array',
        }
    
    interpleveldefs = {
        'array'    : 'ndarray.array',
        'zeros'    : 'ndarray.zeros',
        'minimum'  : 'ufunc.minimum',
        }

