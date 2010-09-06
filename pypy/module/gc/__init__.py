from pypy.interpreter.mixedmodule import MixedModule
    
class Module(MixedModule):
    appleveldefs = {
        'enable': 'app_gc.enable',
        'disable': 'app_gc.disable',
        'isenabled': 'app_gc.isenabled',
    }
    interpleveldefs = {
        'collect': 'interp_gc.collect',
        'enable_finalizers': 'interp_gc.enable_finalizers',
        'disable_finalizers': 'interp_gc.disable_finalizers',
        'garbage' : 'space.newlist([])',
        #'dump_heap_stats': 'interp_gc.dump_heap_stats',
    }

    def __init__(self, space, w_name):
        ts = space.config.translation.type_system
        if ts == 'lltype':
            self.interpleveldefs.update({
                'get_rpy_objects': 'referents.get_rpy_objects',
                'get_rpy_referents': 'referents.get_rpy_referents',
                'get_rpy_memory_usage': 'referents.get_rpy_memory_usage',
                'get_objects': 'referents.get_objects',
                'get_referents': 'referents.get_referents',
                'get_memory_usage': 'referents.get_memory_usage',
                'GcRef': 'referents.W_GcRef',
                })
        MixedModule.__init__(self, space, w_name)
