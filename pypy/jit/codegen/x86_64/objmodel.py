from pypy.jit.codegen import model
from pypy.rpython.lltypesystem import lltype, rffi, llmemory
# Wrapper Classes:
# The opcodes(assemble.py) differ from the type of
# the operand(eg. Register, Immediate...). 
# The to_string method is used to choose the right
# method inside the assembler

class IntVar(model.GenVar):
    def __init__(self, pos_str, location_type):
        self.pos_str = pos_str
        self.location_type = location_type
        assert location_type == "Register64" or location_type == "Register8"
    
    def to_string(self):
        if self.location_type=="Register8":
            return "_8REG"
        elif self.location_type=="Register64":
            return "_QWREG"

class Immediate8(model.GenConst):
    def __init__(self, value):
        self.value = value
        
    def to_string(self):
        return "_IMM8"
    
class Immediate32(model.GenConst):
    def __init__(self, value):
        self.value = value
        
    def to_string(self):
        return "_IMM32"
    
# TODO: understand GenConst
class Immediate64(model.GenConst):
    def __init__(self, value):
        self.value = value
        
    def to_string(self):
        return "_IMM64"