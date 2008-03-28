
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
                raise NotImplementedError
        else:
            return self.positions[v]

    def generate_operations(self, mc):
        for operation in self.operations:
            operation.render(self, mc)

    def generate_final_var(self, mc, gv_returnvar, return_loc):
        pos = self.get_position(gv_returnvar)
        mc.MOV(return_loc, pos)
