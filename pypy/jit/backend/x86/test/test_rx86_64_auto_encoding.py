import random
from pypy.jit.backend.x86 import rx86
from pypy.jit.backend.x86.test import test_rx86_32_auto_encoding


class TestRx86_64(test_rx86_32_auto_encoding.TestRx86_32):
    WORD = 8
    TESTDIR = 'rx86_64'
    X86_CodeBuilder = rx86.X86_64_CodeBuilder
    REGNAMES = ['%rax', '%rcx', '%rdx', '%rbx', '%rsp', '%rbp', '%rsi', '%rdi',
                '%r8', '%r9', '%r10', '%r11', '%r12', '%r13', '%r14', '%r15']
    REGS = range(16)
    NONSPECREGS = [rx86.eax, rx86.ecx, rx86.edx, rx86.ebx, rx86.esi, rx86.edi,
                   rx86.r8,  rx86.r9,  rx86.r10, rx86.r11,
                   rx86.r12, rx86.r13, rx86.r14, rx86.r15]

    def array_tests(self):
        # reduce a little bit -- we spend too long in these tests
        lst = super(TestRx86_64, self).array_tests()
        random.shuffle(lst)
        return lst[:int(len(lst) * 0.2)]

    def imm64_tests(self):
        v = [-0x80000001, 0x80000000,
             -0x8000000000000000, 0x7FFFFFFFFFFFFFFF]
        for i in range(test_rx86_32_auto_encoding.COUNT1):
            x = ((random.randrange(-32768,32768)<<48) |
                 (random.randrange(0,65536)<<32) |
                 (random.randrange(0,65536)<<16) |
                 (random.randrange(0,65536)<<0))
            v.append(x)
        return v + super(TestRx86_64, self).imm32_tests()

    def test_extra_MOV_ri64(self):
        self.imm32_tests = self.imm64_tests      # patch on 'self'
        self.complete_test('MOV_ri')
