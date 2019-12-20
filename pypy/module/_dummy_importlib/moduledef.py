from pypy.interpreter.mixedmodule import MixedModule
from pypy.interpreter.gateway import interp2app
from pypy.module._dummy_importlib import interp_import

class Module(MixedModule):
    interpleveldefs = {
        }

    appleveldefs = {
        }

    def install(self):
        """NOT_RPYTHON"""
        super(Module, self).install()
        self.w_import = self.space.wrap(
            interp2app(interp_import.importhook, app_name='__dummy_import__'))

    def startup(self, space):
        """Copy our __import__ to builtins."""
        # use special module api to prevent a cell from being introduced
        self.space.builtin.setdictvalue_dont_introduce_cell(
            '__import__', self.w_import)
