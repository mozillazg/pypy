
""" Importer class 
    # Meta hooks are called at the start of Import Processing
    # Meta hooks can override the sys.path, frozen modules , built-in modules
    # to register a Meta Hook simply add importer object to sys.meta_path
    # a path hook is registered by adding an Importer factory to sys.path_hooks
    # sys.path_hooks  is a list of Class of the HOOK.
    # whose __init__ is called when the calleable in the list is obtained.
    # __init__ cant return anything so some __new__ method should return
    This is used to enable the "import module" mechanism for .NET classes"""

import imp
import sys
        
class loader(object):
    def __init__(self):
        self.Names = [] 

    def load_module(self, fullname):
        try:
            return sys.modules[fullname]
        except KeyError:
            pass
        # Now create a new module and append it at the end of the sys.modules list
        mod = imp.new_module(fullname)
        mod.__file__ = "<%s>" % self.__class__.__name__
        mod.__loader__ = self
        mod.__name__ = fullname
        '''#if ispkg:
        if :
            mod.__path__ = []
        exec code in mod.__dict__'''

        # add it to the modules list
        sys.modules[fullname] = mod

        return mod

class importer(object):

    def __init__(self):
        self.loader = loader()

    def find_module(self, fullname, path):
        # path will be None for top-level Module and __path__ for sub-modules
        print fullname
        if path != None:
            __path__ = path
        try:
            return sys.modules[fullname]
        except KeyError:
            pass
       
        # Now since the module was not found .. Call the Loader and load it.
        try:
            return self.loader
        except ImportError:
            print "Import Error exception raised hence you better quit"
            return None

#def load_cli_class(space, namespace, classname):
