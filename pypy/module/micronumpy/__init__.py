
from pypy.interpreter.mixedmodule import MixedModule 

class Module(MixedModule):
    def __init__(self, space, w_name):
        super(Module, self).__init__(space, w_name) 
        from pypy.module.micronumpy import dtype
        dtype.w_int_descr.w_native_type = space.w_int
        dtype.w_float_descr.w_native_type = space.w_float

    applevel_name = 'micronumpy'
    appleveldefs = {}
    
    interpleveldefs = {
        'array'    : 'microarray.array',
        'zeros'    : 'microarray.zeros',
        'ndarray'  : 'array.ndarray',
        #'minimum'  : 'ufunc.minimum',
        #'dot'      : 'ufunc.dot',
        }

