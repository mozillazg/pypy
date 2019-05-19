from pypy.interpreter.mixedmodule import MixedModule
    
class Module(MixedModule):
    appleveldefs = {
    }
    interpleveldefs = {
        'ref': 'interp__weakref.W_Weakref',
        'getweakrefcount': 'interp__weakref.getweakrefcount',
        'getweakrefs': 'interp__weakref.getweakrefs',
        'ReferenceType': 'interp__weakref.W_Weakref',
        'ProxyType': 'interp__weakref.W_Proxy', 
        'CallableProxyType': 'interp__weakref.W_CallableProxy',
        'proxy': 'interp__weakref.proxy',
        '_remove_dead_weakref': 'interp__weakref._remove_dead_weakref',
    }
