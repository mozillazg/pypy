
from pypy.jit.codegen.i386.ri386 import *

class RegAlloc(object):
    def __init__(self, operations):
        self.operations = operations
        self.positions = {}

    def set_position(self, var, pos):
        self.positions[var] = pos

    def get_position(self, v):
        from pypy.jit.codegen.ia32.rgenop import IntConst
        if v.is_const:
            if type(v) is IntConst: 
                return imm(v.value)
            else:
                xxx
        else:
            return self.positions[v]

    def generate_operations(self, mc):
        for operation in self.operations:
            operation.render(self, mc)
