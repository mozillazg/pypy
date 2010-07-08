from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    """    """

    interpleveldefs = {
        '_load_lib': 'interp_cppyy.load_lib',
    }

    appleveldefs = {
        'gbl'                    : 'pythonify.gbl',
        'load_lib'               : 'pythonify.load_lib',
    }
