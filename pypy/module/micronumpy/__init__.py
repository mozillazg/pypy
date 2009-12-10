
from pypy.interpreter.mixedmodule import MixedModule 

class Module(MixedModule):

    applevel_name = 'numpy'
    appleveldefs = {
        'array' : 'app_numarray.array',
        }
    
    interpleveldefs = {
        'zeros'    : 'numarray.zeros',
        'minimum'  : 'ufunc.minimum',
        'IntArray' : 'numarray.IntArray',
        'FloatArray' : 'numarray.FloatArray',
        }

