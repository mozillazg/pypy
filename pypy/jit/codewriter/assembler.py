from pypy.jit.metainterp import history


class JitCode(history.AbstractValue):
    empty_list = []

    def __init__(self, name, cfnptr=None, calldescr=None, called_from=None,
                 graph=None):
        self.name = name
        self.cfnptr = cfnptr
        self.calldescr = calldescr
        self.called_from = called_from
        self.graph = graph

    def setup(self, code, constants):
        self.code = code
        self.constants = constants or self.empty_list    # share the empty list
