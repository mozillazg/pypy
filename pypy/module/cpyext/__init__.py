from pypy.interpreter.mixedmodule import MixedModule
from pypy.rlib.objectmodel import we_are_translated
from pypy.module.cpyext.state import State
from pypy.module.cpyext import api


class Module(MixedModule):
    interpleveldefs = {
        'load_module': 'api.load_extension_module',
    }

    appleveldefs = {
    }

    def setup_after_space_initialization(self):
        """NOT_RPYTHON"""
        state = self.space.fromcache(State)
        if not self.space.config.translating:
            state.api_lib = str(api.build_bridge(self.space))
        else:
            api.setup_library(self.space)

    def startup(self, space):
        state = space.fromcache(State)
        if not we_are_translated():
            space.setattr(space.wrap(self),
                          space.wrap('api_lib'),
                          space.wrap(state.api_lib))
        else:
            state.init_r2w_from_w2r()

# import these modules to register api functions by side-effect
import pypy.module.cpyext.pyobject
import pypy.module.cpyext.boolobject
import pypy.module.cpyext.floatobject
import pypy.module.cpyext.modsupport
import pypy.module.cpyext.pythonrun
import pypy.module.cpyext.pyerrors
import pypy.module.cpyext.typeobject
import pypy.module.cpyext.object
import pypy.module.cpyext.stringobject
import pypy.module.cpyext.tupleobject
import pypy.module.cpyext.dictobject
import pypy.module.cpyext.intobject
import pypy.module.cpyext.listobject
import pypy.module.cpyext.sequence
# now that all rffi_platform.Struct types are registered, configure them
api.configure_types()
