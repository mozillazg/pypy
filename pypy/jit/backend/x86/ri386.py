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

def encode_char(mc, char, orbyte, *ignored):
    mc.writechar(chr(char | orbyte))
    return 0

# ____________________________________________________________
# Encode a register number in the orbyte

@specialize.arg(1)
def encode_register(mc, (argnum, factor), orbyte, *args):
    reg = args[argnum-1]
    assert 0 <= reg < 8
    return orbyte | (reg * factor)

def register(argnum, factor=1):
    return encode_register, (argnum, factor)

# ____________________________________________________________
# Encode a constant in the orbyte

def encode_orbyte(mc, constant, orbyte, *ignored):
    return orbyte | constant

def orbyte(value):
    return encode_orbyte, value

# ____________________________________________________________
# Emit an immediate value

@specialize.arg(1)
def encode_immediate(mc, (argnum, width), orbyte, *args):
    imm = args[argnum-1]
    assert orbyte == 0
    mc.writeimm(imm, width)
    return 0

def immediate(argnum, width='i'):
    return encode_immediate, (argnum, width)

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

@specialize.arg(1)
def encode_stack(mc, (argnum, allow_single_byte), orbyte, *args):
    offset = get_ebp_ofs(args[argnum-1])
    if allow_single_byte and single_byte(offset):
        mc.writechar(chr(0x40 | ebp | orbyte))
        mc.writeimm(offset, 'b')
    else:
        mc.writechar(chr(0x80 | ebp | orbyte))
        mc.writeimm(offset, 'i')
    return 0

def stack(argnum, allow_single_byte=True):
    return encode_stack, (argnum, allow_single_byte)

# ____________________________________________________________

def insn(*encoding):
    def encode(mc, *args):
        orbyte = 0
        for encode_step, encode_static_arg in encoding_steps:
            orbyte = encode_step(mc, encode_static_arg, orbyte, *args)
        assert orbyte == 0
    #
    encoding_steps = []
    for step in encoding:
        if isinstance(step, str):
            for c in step:
                encoding_steps.append((encode_char, ord(c)))
        else:
            assert type(step) is tuple and len(step) == 2
            encoding_steps.append(step)
    encoding_steps = unrolling_iterable(encoding_steps)
    return encode

# ____________________________________________________________


class I386CodeBuilder(object):
    """Abstract base class."""

    def writechar(self, char):
        raise NotImplementedError

    @specialize.arg(2)
    def writeimm(self, imm, width='i'):
        self.writechar(chr(imm & 0xFF))
        if width != 'b':     # != byte
            self.writechar(chr((imm >> 8) & 0xFF))
            if width != 'h':    # != 2-bytes word
                self.writechar(chr((imm >> 16) & 0xFF))
                self.writechar(chr((imm >> 24) & 0xFF))

    MOV_ri = insn(register(1), '\xB8', immediate(2))
    MOV_si = insn('\xC7', orbyte(0<<3), stack(1), immediate(2))
    MOV_rr = insn('\x89', register(2,8), register(1), '\xC0')
    MOV_sr = insn('\x89', register(2,8), stack(1))
    MOV_rs = insn('\x8B', register(1,8), stack(2))

    NOP = insn('\x90')

    ADD_rr = insn('\x01', register(2,8), register(1), '\xC0')
