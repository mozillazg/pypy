from pypy.interpreter.module import Module 
from pypy.tool.cache import Cache
from pypy.interpreter import gateway 
from pypy.interpreter.error import OperationError 

import inspect

class ExtModule(Module): 
    def __init__(self, space, w_name): 
        """ NOT_RPYTHON """ 
        Module.__init__(self, space, w_name) 
        self.lazy = True 
        # build a constant dictionary out of
        # applevel/interplevel definitions 
        self.__class__.buildloaders() 

    def ARGL_getattr(self, w_attr): 
        space = self.space
        if not self.lazy: 
            raise OperationError(space.w_AttributeError, w_attr) 
        name = space.str_w(w_attr)
        return self.get(name) 

    def get(self, name): 
        try:
            return Module.get(self, name)
        except OperationError, e: 
            space = self.space
            if not self.lazy or not e.match(space, self.space.w_KeyError): 
                raise 
            # not rpython
            try: 
                loader = self.loaders[name]
            except KeyError: 
                raise OperationError(space.w_AttributeError, space.wrap(name))
            else: 
                w_value = loader(space) 
                space.setitem(self.w_dict, space.wrap(name), w_value) 
                return w_value 

    def buildloaders(cls): 
        """ NOT_RPYTHON """ 
        if not hasattr(cls, 'loaders'): 
            cls.loaders = loaders = {}
            pkgroot = cls.__module__
            print cls.interpleveldefs
            for name, spec in cls.interpleveldefs.items(): 
                if spec.startswith('('): 
                    loader = getinterpevalloader(spec)
                else: 
                    loader = getinterpfileloader(pkgroot, spec) 
                loaders[name] = loader 
            for name, spec in cls.appleveldefs.items(): 
                loaders[name] = getappfileloader(pkgroot, spec) 
    buildloaders = classmethod(buildloaders) 

def getinterpevalloader(spec): 
    def ievalloader(space): 
        """ NOT_RPYTHON """ 
        d = {'space' : space}
        return eval(spec, d, d)
    return ievalloader 

def getinterpfileloader(pkgroot, spec):
    modname, attrname = spec.split('.')
    impbase = pkgroot + '.' + modname 
    def ifileloader(space): 
        """ NOT_RPYTHON """ 
        mod = __import__(impbase, None, None, [attrname])
        attr = getattr(mod, attrname)
        iattr = gateway.interp2app(attr, attrname)
        return space.wrap(iattr) 
    return ifileloader 

applevelcache = Cache()
def getappfileloader(pkgroot, spec): 
    # hum, it's a bit more involved, because we usually 
    # want the import at applevel
    modname, attrname = spec.split('.')
    impbase = pkgroot + '.' + modname 
    mod = __import__(impbase, None, None, ['attrname'])
    app = applevelcache.getorbuild(mod, buildapplevelfrommodule, None)
    def afileloader(space): 
        """ NOT_RPYTHON """ 
        return app.wget(space, attrname)
    return afileloader 

def buildapplevelfrommodule(mod, _): 
    source = inspect.getsource(mod) 
    return gateway.applevel(source) 
