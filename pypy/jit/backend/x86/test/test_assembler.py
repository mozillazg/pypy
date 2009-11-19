from pypy.jit.backend.x86.ri386 import *
from pypy.jit.backend.x86.assembler import Assembler386
from pypy.jit.backend.x86.regalloc import X86StackManager
from pypy.jit.metainterp.history import BoxInt, BoxPtr, BoxFloat


class FakeCPU:
    rtyper = None

class FakeMC:
    def __init__(self):
        self.content = []
    def writechr(self, n):
        self.content.append(n)


def test_write_failure_recovery_description():
    assembler = Assembler386(FakeCPU())
    mc = FakeMC()
    failargs = [BoxInt(), BoxPtr(), BoxFloat()] * 3
    locs = [X86StackManager.stack_pos(0, 1),
            X86StackManager.stack_pos(1, 1),
            X86StackManager.stack_pos(10, 2),
            X86StackManager.stack_pos(100, 1),
            X86StackManager.stack_pos(101, 1),
            X86StackManager.stack_pos(110, 2),
            ebx,
            esi,
            xmm2]
    assembler.write_failure_recovery_description(mc, failargs, locs)
    nums = [0 + 4*(8+0),
            1 + 4*(8+1),
            2 + 4*(8+10),
            0 + 4*(8+100),
            1 + 4*(8+101),
            2 + 4*(8+110),
            0 + 4*ebx.op,
            1 + 4*esi.op,
            2 + 4*xmm2.op]
    double_byte_nums = []
    for num in nums[3:6]:
        double_byte_nums.append((num & 0x7F) | 0x80)
        double_byte_nums.append(num >> 7)
    assert mc.content == (nums[:3] + double_byte_nums + nums[6:] +
                          [assembler.DESCR_STOP])
