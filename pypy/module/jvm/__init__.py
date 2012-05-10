from pypy.interpreter.mixedmodule import MixedModule
import pypy.translator.jvm.jvm_interop as jvm_interop

jvm_interop.add_registry_entries()

class Module(MixedModule):
    """
    A simple JVM module that exposes JVM classes to the interpreted program.
    """

    appleveldefs = {
#        'app_level_hello': 'app_level.hello'
    }

    interpleveldefs = {
        'new': 'interp_level.new',
    }
