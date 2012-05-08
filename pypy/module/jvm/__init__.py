from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    """
    A simple JVM module that exposes JVM classes to the interpreted program.
    """

    appleveldefs = {
        'app_level_hello': 'app_level.hello'
    }

    interpleveldefs = {
        'interp_level_hello': 'interp_level.hello'
    }
