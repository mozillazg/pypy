from pypy.jit.codegen.x86_64 import assembler
from pypy.jit.codegen.x86_64.objmodel import Register64, Immediate32

class AsmTest(assembler.X86_64CodeBuilder):
    def __init__(self):
        self.data = []

    def get_as_string(self):
        return "".join(self.data)

    def write(self,char):
        self.data.append(char)

def test_add():
    mc = AsmTest()
    mc.ADD(Register64("rax"), Register64("r11"))
    assert mc.get_as_string() == "\x4C\x01\xD8"
    mc.ADD(Register64("rbx"), Register64("rbx"))
    assert mc.get_as_string() == "\x4C\x01\xD8\x48\x01\xDB"
    
def test_mov():
    mc = AsmTest()
    mc.MOV(Register64("r15"),Register64("rsp"))
    assert mc.get_as_string() == "\x49\x89\xE7"