from pypy.interpreter.mixedmodule import MixedModule
import pypy.translator.jvm.jvm_interop as jvm_interop

jvm_interop.add_registry_entries()

class Module(MixedModule):
    """
    A simple JVM module that exposes JVM classes to the interpreted program.
    """

    appleveldefs = {
        'java': 'app_level.java'
    }

    interpleveldefs = {
        'new': 'interp_level.new',
        'get_methods': 'interp_level.get_methods',
        'get_fields': 'interp_level.get_fields',
        'get_constructors': 'interp_level.get_constructors',
        'call_method': 'interp_level.call_method',
        'get_field': 'interp_level.get_field',
        'set_field': 'interp_level.set_field',
        'box': 'interp_level.box',
        'unbox': 'interp_level.unbox',
        'superclass': 'interp_level.superclass'
    }
