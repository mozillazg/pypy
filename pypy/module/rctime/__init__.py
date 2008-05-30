
from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    applevel_name = 'time'

    interpleveldefs = {
        'accept2dyear': 'interp_time.accept2dyear',
        'timezone': 'interp_time.timezone',
        'daylight': 'interp_time.daylight',
        'tzname': 'interp_time.tzname',
        'altzone': 'interp_time.altzone',
        'time': 'interp_time.time',
        'clock': 'interp_time.clock',
        'ctime': 'interp_time.ctime',
        'asctime': 'interp_time.asctime',
        'gmtime': 'interp_time.gmtime',
        'localtime': 'interp_time.localtime',
        'mktime': 'interp_time.mktime',
        'strftime': 'interp_time.strftime',
        'sleep' : 'interp_time.sleep',
        'tzset' : 'interp_time.tzset',
    }

    def buildloaders(cls):
        from pypy.module.rctime import interp_time
        
        # this machinery is needed to expose constants
        # that have to be initialized one time only
        
        Module.interpleveldefs["accept2dyear"] = 'space.wrap(%r)' %\
            interp_time._init_accept2dyear()

        Module.interpleveldefs['timezone'] = 'space.wrap(0)'
        Module.interpleveldefs['daylight'] = 'space.wrap(0)'
        Module.interpleveldefs['tzname'] = \
            'space.newlist([space.wrap(""), space.wrap("")])'
        Module.interpleveldefs['altzone'] = 'space.wrap(0)'
        
        super(Module, cls).buildloaders()
    buildloaders = classmethod(buildloaders)

    appleveldefs = {
        'struct_time': 'app_time.struct_time',
        '__doc__': 'app_time.__doc__',
        'strptime': 'app_time.strptime',
    }

    def startup(self, space):
        from pypy.module.rctime import interp_time
        interp_time.tzset(space)
