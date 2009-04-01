from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    """A gdbm built-in module based on rffi."""

    interpleveldefs = {
        'gdbm' : 'gdbm.GDBM',
        'new'  : 'gdbm.GDBM'
    }

    appleveldefs = {
    }

