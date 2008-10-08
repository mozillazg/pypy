from pypy.jit.codegen.x86_64 import assembler
from pypy.jit.codegen.x86_64.objmodel import IntVar, Immediate32

class AsmTest(assembler.X86_64CodeBuilder):
    def __init__(self):
        self.data = []

    def get_as_string(self):
        return "".join(self.data)

    def write(self,char):
        self.data.append(char)

def test_add():
    mc = AsmTest()
    mc.ADD(IntVar("rax", "Register64"), IntVar("r11", "Register64"))
    assert mc.get_as_string() == "\x4C\x01\xD8"
    mc.ADD(IntVar("rbx", "Register64"), IntVar("rbx", "Register64"))
    assert mc.get_as_string() == "\x4C\x01\xD8\x48\x01\xDB"
    
def test_mov():
    mc = AsmTest()
    mc.MOV(IntVar("r15", "Register64"), IntVar("rsp", "Register64"))
    assert mc.get_as_string() == "\x49\x89\xE7"