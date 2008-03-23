from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    appleveldefs = {
    }

    interpleveldefs = {
        'getthreshold': 'interp_jit.getthreshold',
        'setthreshold': 'interp_jit.setthreshold',
        'enable':       'interp_jit.enable',
        'disable':      'interp_jit.disable',
        'isenabled':    'interp_jit.isenabled',
    }

    def setup_after_space_initialization(self):
        # force the __extend__ hacks to occur early
        import pypy.module.pypyjit.interp_jit

    def startup(self, space):
        from pypy.module.pypyjit import interp_jit
        interp_jit.startup(space)
