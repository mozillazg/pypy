
from pypy.interpreter.mixedmodule import MixedModule
from pypy.module._curses import fficurses
from pypy.module._curses import interp_curses
from pypy.rlib.nonconst import NonConstant
import _curses

class Module(MixedModule):
    """ Low-level interface for curses module,
    not meant to be used directly
    """
    applevel_name = "_curses"

    appleveldefs = {
        'error'          : 'app_curses.error',
    }
    
    interpleveldefs = {
        'setupterm'      : 'interp_curses.setupterm',
        'tigetstr'       : 'interp_curses.tigetstr',
        'tparm'          : 'interp_curses.tparm',
    }

    def startup(self, space):
        # XXX nasty annotation trick
        try:
            raise interp_curses.curses_error(NonConstant("xxx"))
        except _curses.error, e:
            pass

import _curses
for i in dir(_curses):
    val = getattr(_curses, i)
    if i.isupper() and type(val) is int:
        Module.interpleveldefs[i] = "space.wrap(%s)" % val
