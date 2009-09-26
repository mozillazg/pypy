from pypy.rlib.rarithmetic import intmask
from pypy.rlib.objectmodel import ComputedIntSymbolic, we_are_translated
from pypy.rlib.objectmodel import specialize
from pypy.rlib.unroll import unrolling_iterable

WORD = 4

eax = 0
ecx = 1
edx = 2
ebx = 3
esp = 4
ebp = 5
esi = 6
edi = 7


class CodeStepWriter(object):
    def encode(self, mc, args, orbyte):
        mc.writechar(chr(self.encode_byte(args) | orbyte))
    def _freeze_(self):
        return True
    def __or__(self, other):
        if isinstance(other, int):
            other = Constant(other)
        if hasattr(self, 'encode_byte'):
            return Compose(self, other)
        if hasattr(other, 'encode_byte'):
            return Compose(other, self)
        return NotImplemented
    __ror__ = __or__

class Constant(CodeStepWriter):
    def __init__(self, charvalue):
        self.charvalue = charvalue
    def encode_byte(self, args):
        return self.charvalue

class Compose(CodeStepWriter):
    def __init__(self, operand1, operand2):
        self.operand1 = operand1
        self.operand2 = operand2
    def encode(self, mc, args, orbyte):
        orbyte |= self.operand1.encode_byte(args)
        self.operand2.encode(mc, args, orbyte)

class register(CodeStepWriter):
    def __init__(self, argnum, shift=0):
        self.argnum = argnum
        self.shift = shift
    def __lshift__(self, num):
        return register(self.argnum, self.shift + num)
    def encode_byte(self, args):
        reg = args[self.argnum-1]
        assert 0 <= reg < 8
        return reg << self.shift

class imm32(CodeStepWriter):
    def __init__(self, argnum):
        self.argnum = argnum
    def encode(self, mc, args, orbyte):
        assert orbyte == 0
        imm = args[self.argnum-1]
        mc.writechar(chr(imm & 0xFF))
        mc.writechar(chr((imm >> 8) & 0xFF))
        mc.writechar(chr((imm >> 16) & 0xFF))
        mc.writechar(chr((imm >> 24) & 0xFF))


def get_ebp_ofs(position):
    # Argument is a stack position (0, 1, 2...).
    # Returns (ebp-16), (ebp-20), (ebp-24)...
    # This depends on the fact that our function prologue contains
    # exactly 4 PUSHes.
    return -WORD * (4 + position)

def single_byte(value):
    return -128 <= value < 128

class stack(CodeStepWriter):
    def __init__(self, argnum, allow_single_byte=True):
        self.argnum = argnum
        self.allow_single_byte = allow_single_byte
    def encode(self, mc, args, orbyte):
        offset = get_ebp_ofs(args[self.argnum-1])
        if self.allow_single_byte and single_byte(offset):
            mc.writechar(chr(0x40 | ebp | orbyte))
            mc.writechar(chr(offset & 0xFF))
        else:
            mc.writechar(chr(0x80 | ebp | orbyte))
            mc.writechar(chr(offset & 0xFF))
            mc.writechar(chr((offset >> 8) & 0xFF))
            mc.writechar(chr((offset >> 16) & 0xFF))
            mc.writechar(chr((offset >> 24) & 0xFF))

# ____________________________________________________________

def insn(*encoding):
    def encode(mc, *args):
        for step in encoding_steps:
            step.encode(mc, args, 0)
    #
    encoding_steps = []
    for step in encoding:
        if isinstance(step, str):
            for c in step:
                encoding_steps.append(Constant(ord(c)))
        else:
            assert isinstance(step, CodeStepWriter)
            encoding_steps.append(step)
    encoding_steps = unrolling_iterable(encoding_steps)
    return encode

# ____________________________________________________________


class I386CodeBuilder(object):
    """Abstract base class."""

    def writechar(self, char):
        raise NotImplementedError

    MOV_ri = insn(0xB8 | register(1), imm32(2))
    MOV_si = insn('\xC7', 0<<3 | stack(1), imm32(2))
    MOV_rr = insn('\x89', 0xC0 | register(2)<<3 | register(1))
    MOV_sr = insn('\x89', stack(1) | register(2)<<3)
    MOV_rs = insn('\x8B', register(1)<<3 | stack(2))

    NOP = insn('\x90')

    ADD_rr = insn('\x01', 0xC0 | register(2)<<3 | register(1))
