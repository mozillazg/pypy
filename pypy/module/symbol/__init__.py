"""Dynamic replacement for the stdlib 'symbol' module.

This module exports the symbol values computed by the grammar parser
at run-time.
"""

from pypy.interpreter.mixedmodule import MixedModule

# Forward imports so they run at startup time
import pypy.interpreter.pyparser.pythonlexer
import pypy.interpreter.pyparser.pythonparse


class Module(MixedModule):
    """Non-terminal symbols of Python grammar."""
    appleveldefs = {}
    interpleveldefs = {}

    def setup_after_space_initialization(self):
        from pypy.interpreter.pyparser.pythonparse import make_pyparser
        space = self.space
        grammar_version = space.config.objspace.pyversion
        parser = make_pyparser(grammar_version)
        sym_name = {}
        for name, val in parser.symbols.items():
            # Skip negative values (the corresponding symbols are not visible in
            # pure Python).
            if val >= 0:
                space.setattr(self, space.wrap(name), space.wrap(val))
                sym_name[val] = name
        space.setattr(self, space.wrap('sym_name'), space.wrap(sym_name))
