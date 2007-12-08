
#     Meta hooks are called at the start of Import Processing
#     Meta hooks can override the sys.path, frozen modules , built-in modules
#     To register a Meta Hook simply add importer object to sys.meta_path

import imp
import sys

class loader(object):
    '''
        This method returns the loaded module or raises an exception, ImportError
        loader is ONLY calld for proper .NET modules (check done in Importer class
    '''
    def __init__(self):
        pass

    def load_module(self, fullname):
        '''
            The load_module() must fulfill the following *before* it runs any code:
            Note that the module object *must* be in sys.modules before the
            loader executes the module code.  

          A  If 'fullname' exists in sys.modules, the loader must use that
             else the loader must create a new module object and add it to sys.modules.

                module = sys.modules.setdefault(fullname, new.module(fullname))

          B  The __file__ attribute must be set.  String say "<frozen>"

          C  The __name__ attribute must be set.  If one uses
              imp.new_module() then the attribute is set automatically.

          D  If it's a package, the __path__ variable must be set.  This must
              be a list, but may be empty if __path__ has no further
              significance to the importer (more on this later).

          E  It should add a __loader__ attribute to the module, set to the loader object. 

        '''
        # If it is a call for a Class then return with the Class reference
        import clr
        if clr.isDotNetType(fullname):
            ''' Task is to breakup System.Collections.ArrayList and call 
                clr.load_cli_class('System.Collections','ArrayList')
            '''
            rindex = fullname.rfind('.')
            if rindex != -1:
                leftStr = fullname[:rindex]
                rightStr= fullname[rindex+1:]
                sys.modules[fullname] = clr.load_cli_class(leftStr, rightStr)

        else:  # if not a call for actual class (say for namespaces) assign an empty module 
            mod = imp.new_module(fullname)
            mod = sys.modules.setdefault(fullname, imp.new_module(fullname))
            mod.__file__ = "<%s>" % self.__class__.__name__
            mod.__loader__ = self
            mod.__name__ = fullname

            # if it is a PACKAGE then we are to initialize the __path__ for the module
            # we won't deal with Packages here

            # add it to the modules list
            sys.modules[fullname] = mod

        return sys.modules[fullname]

class importer(object):
    '''  
         If the importer is installed on sys.meta_path, it will
         receive a second argument, which is None for a top-level module, or
         package.__path__ for submodules or subpackages

         It should return a loader object if the module was found, or None if it wasn't.  
         If find_module() raises an exception, the caller will abort the import.
         When importer.find_module("spam.eggs.ham") is called, "spam.eggs" has already 
         been imported and added to sys.modules.
    '''
    def __init__(self):
        import clr
        # this might not be the correct place to load the valid NameSpaces
        self.ValidNameSpaces = clr.load_valid_namespaces()
        self.loader = loader()

    def find_module(self, fullname, path = None):
        # check for true NAMESPACE or .NET TYPE 
        import clr
        if fullname in self.ValidNameSpaces or clr.isDotNetType(fullname): 
            # fullname is a  .Net Module
            if path != None:
                __path__ = path
            try:
                return sys.modules[fullname]
            except KeyError:
                pass

            try:
                return self.loader
            except ImportError:
                return None 
        else:
            # fullname is not a .Net Module
            return None
            


