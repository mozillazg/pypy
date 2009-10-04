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
