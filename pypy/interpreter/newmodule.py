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
        self.__class__.buildloaders() 

    def get(self, name): 
        space = self.space
        try: 
            return space.getitem(self.w_dict, space.wrap(name))
        except OperationError, e: 
            if not self.lazy or not e.match(space, space.w_KeyError): 
                raise 
            try: 
                loader = self.loaders[name]
            except KeyError: 
                raise OperationError(space.w_AttributeError, space.wrap(name))
            else: 
                w_value = loader(space) 
                self.space.setitem(self.w_dict, space.wrap(name), w_value) 
                return w_value 

    def getdict(self): 
        if self.lazy: 
            space = self.space
            for name in self.loaders: 
                w_value = self.get(name)  
                space.setitem(self.w_dict, space.wrap(name), w_value) 
            self.lazy = False 
        return self.w_dict 

    def buildloaders(cls): 
        """ NOT_RPYTHON """ 
        if not hasattr(cls, 'loaders'): 
            # build a constant dictionary out of
            # applevel/interplevel definitions 
            cls.loaders = loaders = {}
            pkgroot = cls.__module__
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
