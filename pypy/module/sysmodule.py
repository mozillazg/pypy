from pypy.interpreter.baseobjspace import OperationError
from pypy.interpreter.gateway import AppVisibleModule
import os, pypy

import sys as cpy_sys

class sys(AppVisibleModule):
    """ A Minimal 'sys' module.

    Currently we only provide 'stdout' and 'displayhook'
    """

    def __init__(self, space):
        opd = os.path.dirname
        pypydir = opd(opd(os.path.abspath(pypy.__file__)))
        appdir = os.path.join(pypydir, 'pypy', 'appspace')
        self.path = [appdir] + [p for p in cpy_sys.path if p!= pypydir]
        self.w_modules = space.newdict([])
        AppVisibleModule.__init__(self, space)
   
    stdout = cpy_sys.stdout 

    def _setmodule(self, module):
        """ put a module into the modules list """
        self.space.setitem(self.w_modules, module.w___name__, module._wrapped)

    def displayhook(self, w_x):
        space = self.space
        w = space.wrap
        if w_x != space.w_None:
            try:
                print space.unwrap(self.space.repr(w_x))
            except OperationError:
                print "! could not print", w_x
            space.setitem(space.w_builtins, w('_'), w_x)
