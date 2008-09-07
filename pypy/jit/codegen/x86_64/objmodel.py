from pypy.jit.codegen import model
from pypy.rpython.lltypesystem import lltype, rffi, llmemory
# Wrapper Classes
# The opcaodes differ from the type of
# the operand. So every wrapper is necessary
# The to string method is used to choose the right
# method inside the assembler
class Register8(model.GenVar):
    def __init__(self, reg):
        self.reg = reg
        
    def to_string(self):
        return "_8REG"

class Register64(model.GenVar):
    def __init__(self, reg):
        self.reg = reg
        
    def to_string(self):
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