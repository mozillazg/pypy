from pypy.interpreter.mixedmodule import MixedModule
from pypy.module._demo.interp_demo import W_Zero, W_One
from pypy.objspace.std.model import registerimplementation

registerimplementation(W_Zero)
registerimplementation(W_One)

class Module(MixedModule):
    """A demo built-in module based on ctypes."""

    interpleveldefs = {
        'tp' : 'interp_demo.W_Zero', # W_One would do as well, gateway
        # is getting type of an object anyway (which they share)
    }

    appleveldefs = {
    }

    # Used in tests
    demo_events = []
    def setup_after_space_initialization(self):
        Module.demo_events.append('setup')
    def startup(self, space):
        Module.demo_events.append('startup')
    def shutdown(self, space):
        Module.demo_events.append('shutdown')

