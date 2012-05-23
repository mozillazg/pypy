from pypy.interpreter.mixedmodule import MixedModule
import pypy.translator.jvm.rjvm_support as rjvm_support

rjvm_support.add_registry_entries()

class Module(MixedModule):
    """
    A simple JVM module that exposes JVM classes to the interpreted program.
    """

    appleveldefs = {
        'java': 'app_level.java',
        'javax': 'app_level.javax',
        'package': 'app_level.package',
    }

    interpleveldefs = {
        'new': 'interp_level.new',
        'get_methods': 'interp_level.get_methods',
        'get_static_methods': 'interp_level.get_static_methods',
        'get_fields': 'interp_level.get_fields',
        'get_static_fields': 'interp_level.get_static_fields',
        'get_constructors': 'interp_level.get_constructors',
        'call_method': 'interp_level.call_method',
        'call_static_method': 'interp_level.call_static_method',
        'get_field_value': 'interp_level.get_field_value',
        'get_static_field_value': 'interp_level.get_static_field_value',
        'set_field_value': 'interp_level.set_field_value',
        'set_static_field_value': 'interp_level.set_static_field_value',
        'box': 'interp_level.box',
        'unbox': 'interp_level.unbox',
        'superclass': 'interp_level.superclass'
    }
