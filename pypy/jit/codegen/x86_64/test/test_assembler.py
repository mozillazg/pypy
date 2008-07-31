from pypy.jit.codegen.x86_64 import assembler

class AsmTest(assembler.X86_64CodeBuilder):
    def __init__(self):
        self.data = []

    def get_as_string(self):
        return "".join(self.data)

    def write(self,char):
        self.data.append(char)

def test_add():
    mc = AsmTest()
    mc.ADD("rax", "r11")
    assert mc.get_as_string() == "\x49\x00\xC3"
    mc.ADD("rbx", "rbx")
    assert mc.get_as_string() == "\x49\x00\xC3\x48\x00\xDB"