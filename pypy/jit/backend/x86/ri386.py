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

# ____________________________________________________________
# Emit a single char

def encode_char(mc, _, char, orbyte):
    mc.writechar(chr(char | orbyte))
    return 0

# ____________________________________________________________
# Encode a register number in the orbyte

@specialize.arg(2)
def encode_register(mc, arg, factor, orbyte):
    assert 0 <= arg < 8
    return orbyte | (arg * factor)

def register(argnum, factor=1):
    return encode_register, argnum, factor

# ____________________________________________________________
# Encode a constant in the orbyte

def encode_orbyte(mc, _, constant, orbyte):
    return orbyte | constant

def orbyte(value):
    return encode_orbyte, None, value

# ____________________________________________________________
# Emit an immediate value

@specialize.arg(2)
def encode_immediate(mc, arg, width, orbyte):
    assert orbyte == 0
    if width == 'b':
        mc.writeimm8(arg)
    elif width == 'h':
        mc.writeimm16(arg)
    else:
        mc.writeimm32(arg)
    return 0

def immediate(argnum, width='i'):
    return encode_immediate, argnum, width

# ____________________________________________________________
# Emit a mod/rm referencing a stack location
# This depends on the fact that our function prologue contains
# exactly 4 PUSHes.

def get_ebp_ofs(position):
    # Argument is a stack position (0, 1, 2...).
    # Returns (ebp-16), (ebp-20), (ebp-24)...
    # This depends on the fact that our function prologue contains
    # exactly 4 PUSHes.
    return -WORD * (4 + position)

def single_byte(value):
    return -128 <= value < 128

@specialize.arg(2)
def encode_stack(mc, arg, allow_single_byte, orbyte):
    offset = get_ebp_ofs(arg)
    if allow_single_byte and single_byte(offset):
        mc.writechar(chr(0x40 | ebp | orbyte))
        mc.writeimm8(offset)
    else:
        mc.writechar(chr(0x80 | ebp | orbyte))
        mc.writeimm32(offset)
    return 0

def stack(argnum, allow_single_byte=True):
    return encode_stack, argnum, allow_single_byte

# ____________________________________________________________

def insn(*encoding):
    def encode(mc, *args):
        orbyte = 0
        for encode_step, arg, extra in encoding_steps:
            if arg is not None:
                arg = args[arg-1]
            orbyte = encode_step(mc, arg, extra, orbyte)
        assert orbyte == 0
    #
    encoding_steps = []
    for step in encoding:
        if isinstance(step, str):
            for c in step:
                encoding_steps.append((encode_char, None, ord(c)))
        else:
            assert type(step) is tuple and len(step) == 3
            encoding_steps.append(step)
    encoding_steps = unrolling_iterable(encoding_steps)
    return encode

# ____________________________________________________________


class I386CodeBuilder(object):
    """Abstract base class."""

    def writechar(self, char):
        raise NotImplementedError

    def writeimm8(self, imm):
        self.writechar(chr(imm & 0xFF))

    def writeimm16(self, imm):
        self.writechar(chr(imm & 0xFF))
        self.writechar(chr((imm >> 8) & 0xFF))

    def writeimm32(self, imm):
        self.writechar(chr(imm & 0xFF))
        self.writechar(chr((imm >> 8) & 0xFF))
        self.writechar(chr((imm >> 16) & 0xFF))
        self.writechar(chr((imm >> 24) & 0xFF))

    MOV_ri = insn(register(1), '\xB8', immediate(2))
    MOV_si = insn('\xC7', orbyte(0<<3), stack(1), immediate(2))
    MOV_rr = insn('\x89', register(2,8), register(1), '\xC0')
    MOV_sr = insn('\x89', register(2,8), stack(1))
    MOV_rs = insn('\x8B', register(1,8), stack(2))

    NOP = insn('\x90')

    ADD_rr = insn('\x01', register(2,8), register(1), '\xC0')
