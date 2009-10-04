from pypy.rlib.rarithmetic import intmask, r_uint, r_ulonglong
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
def encode_register(mc, reg, factor, orbyte):
    assert 0 <= reg < 8
    return orbyte | (reg * factor)

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
def encode_immediate(mc, immediate, width, orbyte):
    assert orbyte == 0
    if width == 'b':
        mc.writeimm8(immediate)
    elif width == 'h':
        mc.writeimm16(immediate)
    else:
        mc.writeimm32(immediate)
    return 0

def immediate(argnum, width='i'):
    return encode_immediate, argnum, width

# ____________________________________________________________
# Emit a mod/rm referencing a stack location [EBP+offset]

def single_byte(value):
    return -128 <= value < 128

@specialize.arg(2)
def encode_stack(mc, offset, force_32bits, orbyte):
    if not force_32bits and single_byte(offset):
        mc.writechar(chr(0x40 | ebp | orbyte))
        mc.writeimm8(offset)
    else:
        mc.writechar(chr(0x80 | ebp | orbyte))
        mc.writeimm32(offset)
    return 0

def stack(argnum, force_32bits=False):
    return encode_stack, argnum, force_32bits

# ____________________________________________________________
# Emit a mod/rm referencing a memory location [reg1+offset]

def reg_offset(reg, offset):
    assert 0 <= reg < 8 and reg != esp and reg != ebp
    return (r_ulonglong(reg) << 32) | r_ulonglong(r_uint(offset))

def encode_mem_reg_plus_const(mc, reg1_offset, _, orbyte):
    reg1 = intmask(reg1_offset >> 32)
    offset = intmask(reg1_offset)
    if offset == 0:
        mc.writechar(chr(0x00 | reg1 | orbyte))
    elif single_byte(offset):
        mc.writechar(chr(0x40 | reg1 | orbyte))
        mc.writeimm8(offset)
    else:
        mc.writechar(chr(0x80 | reg1 | orbyte))
        mc.writeimm32(offset)
    return 0

def mem_reg_plus_const(argnum):
    return encode_mem_reg_plus_const, argnum, None

# ____________________________________________________________
# Emit a mod/rm referencing an array memory location [reg1+reg2*scale+offset]

def reg_reg_scaleshift_offset(reg1, reg2, scaleshift, offset):
    assert 0 <= reg1 < 8 and reg1 != ebp
    assert 0 <= reg2 < 8 and reg2 != esp
    assert 0 <= scaleshift < 4
    SIB = (scaleshift<<6) | (reg2<<3) | reg1
    return (r_ulonglong(SIB) << 32) | r_ulonglong(r_uint(offset))

def encode_mem_reg_plus_scaled_reg_plus_const(mc, reg1_reg2_scaleshift_offset,
                                              _, orbyte):
    SIB = chr(intmask(reg1_reg2_scaleshift_offset >> 32))
    offset = intmask(reg1_reg2_scaleshift_offset)
    if offset == 0:
        mc.writechar(chr(0x04 | orbyte))
        mc.writechar(SIB)
    elif single_byte(offset):
        mc.writechar(chr(0x44 | orbyte))
        mc.writechar(SIB)
        mc.writeimm8(offset)
    else:
        mc.writechar(chr(0x84 | orbyte))
        mc.writechar(SIB)
        mc.writeimm32(offset)
    return 0

def mem_reg_plus_scaled_reg_plus_const(argnum):
    return encode_mem_reg_plus_scaled_reg_plus_const, argnum, None

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

def common_modes(group):
    base = group * 8
    INSN_ri8 = insn('\x83', orbyte(group<<3), register(1), '\xC0',
                    immediate(2,'b'))
    INSN_ri32 = insn('\x81', orbyte(group<<3), register(1), '\xC0',
                     immediate(2))
    INSN_rr = insn(chr(base+1), register(2,8), register(1,1), '\xC0')
    INSN_rs = insn(chr(base+3), register(1,8), stack(2))

    def INSN_ri(mc, reg, immed):
        if single_byte(immed):
            INSN_ri8(mc, reg, immed)
        else:
            INSN_ri32(mc, reg, immed)

    return INSN_ri, INSN_rr, INSN_rs

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

    # "MOV reg1, [reg2+offset]" and the opposite direction
    MOV_rm = insn('\x8B', register(1,8), mem_reg_plus_const(2))
    MOV_mr = insn('\x89', register(2,8), mem_reg_plus_const(1))

    # "MOV reg1, [reg2+reg3*scale+offset]" and the opposite direction
    MOV_ra = insn('\x8B', register(1,8), mem_reg_plus_scaled_reg_plus_const(2))
    MOV_ar = insn('\x89', register(2,8), mem_reg_plus_scaled_reg_plus_const(1))

    ADD_ri, ADD_rr, ADD_rs = common_modes(0)
    OR_ri,  OR_rr,  OR_rs  = common_modes(1)
    AND_ri, AND_rr, AND_rs = common_modes(4)
    SUB_ri, SUB_rr, SUB_rs = common_modes(5)
    XOR_ri, XOR_rr, XOR_rs = common_modes(6)
    CMP_ri, CMP_rr, CMP_rs = common_modes(7)

    NOP = insn('\x90')
    RET = insn('\xC3')

    PUSH_r = insn(register(1), '\x50')

    LEA_rs = insn('\x8D', register(1,8), stack(2))
    LEA32_rs = insn('\x8D', register(1,8), stack(2, force_32bits=True))

# ____________________________________________________________

all_instructions = [name for name in I386CodeBuilder.__dict__
                    if name.split('_')[0].isupper()]
all_instructions.sort()
