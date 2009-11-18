from pypy.jit.backend.x86.assembler import Assembler386
from pypy.jit.metainterp.history import BoxInt, BoxPtr


class FakeCPU:
    rtyper = None

class FakeMC:
    def __init__(self):
        self.content = []
    def writechr(self, n):
        self.content.append(n)


def test_bitfield():
    assembler = Assembler386(FakeCPU())
    mc = FakeMC()
    assembler.write_bitfield_for_failargs(mc, [BoxInt(), BoxPtr()], False)
    assert mc.content == [4]
    bitfield = map(chr, mc.content)
    assert assembler.getbit_from_bitfield(bitfield, 0) == False
    assert assembler.getbit_from_bitfield(bitfield, 1) == False
    assert assembler.getbit_from_bitfield(bitfield, 2) == True

def test_larger_bitfield():
    assembler = Assembler386(FakeCPU())
    mc = FakeMC()
    lst = [BoxInt(), BoxPtr(), BoxPtr()] * 6
    assembler.write_bitfield_for_failargs(mc, lst, True)
    bitfield = map(chr, mc.content)
    assert assembler.getbit_from_bitfield(bitfield, 0) == True
    for i in range(len(lst)):
        expected = (lst[i].__class__ == BoxPtr)
        assert assembler.getbit_from_bitfield(bitfield, 1+i) == expected
