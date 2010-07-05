from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    """    """

    interpleveldefs = {
        'load_lib': 'interp_cppyy.load_lib',
    }

    appleveldefs = {
    }
