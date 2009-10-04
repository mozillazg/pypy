from pypy.rlib.rarithmetic import intmask, r_ulonglong
from pypy.rlib.objectmodel import ComputedIntSymbolic, we_are_translated
from pypy.rlib.objectmodel import specialize
from pypy.rlib.unroll import unrolling_iterable
from pypy.rpython.lltypesystem import rffi

# the following are synonyms for rax, rcx, etc. on 64 bits
eax = 0
ecx = 1
edx = 2
ebx = 3
esp = 4
ebp = 5
esi = 6
edi = 7

# the following are extra registers available only on 64 bits
r8  = 8
r9  = 9
r10 = 10
r11 = 11
r12 = 12
r13 = 13
r14 = 14
r15 = 15

def single_byte(value):
    return -128 <= value < 128

def fits_in_32bits(value):
    return -2147483648 <= value <= 2147483647

# ____________________________________________________________
# Emit a single char

def encode_char(mc, _, char, orbyte):
    mc.writechar(chr(char | orbyte))
    return 0

# ____________________________________________________________
# Encode a register number in the orbyte

def reg_number_3bits(mc, reg):
    if mc.WORD == 4:
        assert 0 <= reg < 8
        return reg
    else:
        assert 0 <= reg < 16
        return reg & 7

@specialize.arg(2)
def encode_register(mc, reg, factor, orbyte):
    return orbyte | (reg_number_3bits(mc, reg) * factor)

@specialize.arg(2)
def rex_register(mc, reg, factor):
    if reg >= 8:
        if factor == 1:
            return REX_B
        elif factor == 8:
            return REX_R
        else:
            raise ValueError(factor)
    return 0

def register(argnum, factor=1):
    return encode_register, argnum, factor, rex_register

# ____________________________________________________________
# Encode a constant in the orbyte

def encode_orbyte(mc, _, constant, orbyte):
    return orbyte | constant

def orbyte(value):
    return encode_orbyte, None, value, None

# ____________________________________________________________
# Emit an immediate value

@specialize.arg(2)
def encode_immediate(mc, immediate, width, orbyte):
    assert orbyte == 0
    if width == 'b':
        mc.writeimm8(immediate)
    elif width == 'h':
        mc.writeimm16(immediate)
    elif width == 'q' and mc.WORD == 8:
        mc.writeimm64(immediate)
    else:
        mc.writeimm32(immediate)
    return 0

def immediate(argnum, width='i'):
    return encode_immediate, argnum, width, None

# ____________________________________________________________
# Emit a mod/rm referencing a stack location [EBP+offset]

@specialize.arg(2)
def encode_stack(mc, offset, force_32bits, orbyte):
    if not force_32bits and single_byte(offset):
        mc.writechar(chr(0x40 | orbyte | ebp))
        mc.writeimm8(offset)
    else:
        assert fits_in_32bits(offset)
        mc.writechar(chr(0x80 | orbyte | ebp))
        mc.writeimm32(offset)
    return 0

def stack(argnum, force_32bits=False):
    return encode_stack, argnum, force_32bits, None

# ____________________________________________________________
# Emit a mod/rm referencing a memory location [reg1+offset]

def reg_offset(reg, offset):
    # returns a 64-bits integer encoding "reg1+offset".
    # * 'offset' is stored as bytes 1-4 of the result;
    # * 'reg1' is stored as byte 5 of the result.
    assert reg != esp and reg != ebp
    assert fits_in_32bits(offset)
    return (r_ulonglong(reg) << 32) | r_ulonglong(rffi.r_uint(offset))

def encode_mem_reg_plus_const(mc, reg1_offset, _, orbyte):
    reg1 = reg_number_3bits(mc, intmask(reg1_offset >> 32))
    offset = intmask(reg1_offset)
    no_offset = offset == 0
    SIB = -1
    # 64-bits special cases for reg1 == r12 or r13
    # (which look like esp or ebp after being truncated to 3 bits)
    if mc.WORD == 8:
        if reg1 == esp:             # forces an SIB byte:
            SIB = (esp<<3) | esp    #   use [r12+(no index)+offset]
        elif reg1 == ebp:
            no_offset = False
    # end of 64-bits special cases
    if no_offset:
        mc.writechar(chr(0x00 | orbyte | reg1))
        if SIB >= 0: mc.writechar(chr(SIB))
    elif single_byte(offset):
        mc.writechar(chr(0x40 | orbyte | reg1))
        if SIB >= 0: mc.writechar(chr(SIB))
        mc.writeimm8(offset)
    else:
        mc.writechar(chr(0x80 | orbyte | reg1))
        if SIB >= 0: mc.writechar(chr(SIB))
        mc.writeimm32(offset)
    return 0

def rex_mem_reg_plus_const(mc, reg1_offset, _):
    reg1 = intmask(reg1_offset >> 32)
    if reg1 >= 8:
        return REX_B
    return 0

def mem_reg_plus_const(argnum):
    return encode_mem_reg_plus_const, argnum, None, rex_mem_reg_plus_const

# ____________________________________________________________
# Emit a mod/rm referencing an array memory location [reg1+reg2*scale+offset]

def reg_reg_scaleshift_offset(reg1, reg2, scaleshift, offset):
    # returns a 64-bits integer encoding "reg1+reg2<<scaleshift+offset".
    # * 'offset' is stored as bytes 1-4 of the result;
    # * the SIB byte is computed and stored as byte 5 of the result;
    # * for 64-bits mode, the optional REX.B and REX.X flags go to byte 6.
    assert 0 <= reg1 < 16 and reg1 != ebp
    assert 0 <= reg2 < 16 and reg2 != esp
    assert 0 <= scaleshift < 4
    assert fits_in_32bits(offset)
    encoding = 0
    if reg1 >= 8:
        encoding |= REX_B << 8
        reg1 &= 7
    if reg2 >= 8:
        encoding |= REX_X << 8
        reg2 &= 7
    encoding |= (scaleshift<<6) | (reg2<<3) | reg1
    return (r_ulonglong(encoding) << 32) | r_ulonglong(rffi.r_uint(offset))

def encode_mem_reg_plus_scaled_reg_plus_const(mc, reg1_reg2_scaleshift_offset,
                                              _, orbyte):
    encoding = intmask(reg1_reg2_scaleshift_offset >> 32)
    if mc.WORD == 4:
        assert encoding <= 0xFF    # else registers r8..r15 have been used
        SIB = chr(encoding)
    else:
        SIB = chr(encoding & 0xFF)
    offset = intmask(reg1_reg2_scaleshift_offset)
    no_offset = offset == 0
    # 64-bits special cases for reg1 == r13
    # (which look like ebp after being truncated to 3 bits)
    if mc.WORD == 8:
        if (encoding & 7) == ebp:
            no_offset = False
    # end of 64-bits special cases
    if no_offset:
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

def rex_mem_reg_plus_scaled_reg_plus_const(mc, reg1_reg2_scaleshift_offset, _):
    return intmask(reg1_reg2_scaleshift_offset >> (32+8))

def mem_reg_plus_scaled_reg_plus_const(argnum):
    return (encode_mem_reg_plus_scaled_reg_plus_const, argnum, None,
            rex_mem_reg_plus_scaled_reg_plus_const)

# ____________________________________________________________
# For 64-bits mode: the REX.W, REX.R, REX.X, REG.B prefixes

REX_W = 8
REX_R = 4
REX_X = 2
REX_B = 1

@specialize.arg(2)
def encode_rex(mc, _, basevalue, orbyte):
    if mc.WORD == 8:
        assert 0 <= orbyte < 8
        if basevalue != 0x40 or orbyte != 0:
            mc.writechar(chr(basevalue | orbyte))
    else:
        assert orbyte == 0
    return 0

rex_w  = encode_rex, None, (0x40 | REX_W), None
rex_nw = encode_rex, None, 0x40, None

# ____________________________________________________________

def insn(*encoding):
    def encode(mc, *args):
        orbyte = 0
        if mc.WORD == 8:
            # compute the REX byte, if any
            for encode_step, arg, extra, rex_step in encoding_steps:
                if rex_step:
                    if arg is not None:
                        arg = args[arg-1]
                    orbyte |= rex_step(mc, arg, extra)
        # emit the bytes of the instruction
        for encode_step, arg, extra, rex_step in encoding_steps:
            if arg is not None:
                arg = args[arg-1]
            orbyte = encode_step(mc, arg, extra, orbyte)
        assert orbyte == 0
    #
    encoding_steps = []
    for step in encoding:
        if isinstance(step, str):
            for c in step:
                encoding_steps.append((encode_char, None, ord(c), None))
        else:
            assert type(step) is tuple and len(step) == 4
            encoding_steps.append(step)
    encoding_steps = unrolling_iterable(encoding_steps)
    return encode

def common_modes(group):
    base = group * 8
    INSN_ri8 = insn(rex_w, '\x83', orbyte(group<<3), register(1), '\xC0',
                    immediate(2,'b'))
    INSN_ri32 = insn(rex_w, '\x81', orbyte(group<<3), register(1), '\xC0',
                     immediate(2))
    INSN_rr = insn(rex_w, chr(base+1), register(2,8), register(1,1), '\xC0')
    INSN_rs = insn(rex_w, chr(base+3), register(1,8), stack(2))

    def INSN_ri(mc, reg, immed):
        if single_byte(immed):
            INSN_ri8(mc, reg, immed)
        else:
            INSN_ri32(mc, reg, immed)

    return INSN_ri, INSN_rr, INSN_rs

# ____________________________________________________________


class AbstractX86CodeBuilder(object):
    """Abstract base class."""

    def writechar(self, char):
        raise NotImplementedError

    def writeimm8(self, imm):
        self.writechar(chr(imm & 0xFF))

    def writeimm16(self, imm):
        self.writechar(chr(imm & 0xFF))
        self.writechar(chr((imm >> 8) & 0xFF))

    def writeimm32(self, imm):
        assert fits_in_32bits(imm)
        self.writechar(chr(imm & 0xFF))
        self.writechar(chr((imm >> 8) & 0xFF))
        self.writechar(chr((imm >> 16) & 0xFF))
        self.writechar(chr((imm >> 24) & 0xFF))

    MOV_ri = insn(rex_w, register(1), '\xB8', immediate(2, 'q'))
    #MOV_si = insn(rex_w, '\xC7', orbyte(0<<3), stack(1), immediate(2))
    MOV_rr = insn(rex_w, '\x89', register(2,8), register(1), '\xC0')
    MOV_sr = insn(rex_w, '\x89', register(2,8), stack(1))
    MOV_rs = insn(rex_w, '\x8B', register(1,8), stack(2))

    # "MOV reg1, [reg2+offset]" and the opposite direction
    MOV_rm = insn(rex_w, '\x8B', register(1,8), mem_reg_plus_const(2))
    MOV_mr = insn(rex_w, '\x89', register(2,8), mem_reg_plus_const(1))

    # "MOV reg1, [reg2+reg3*scale+offset]" and the opposite direction
    MOV_ra = insn(rex_w, '\x8B', register(1,8),
                                 mem_reg_plus_scaled_reg_plus_const(2))
    MOV_ar = insn(rex_w, '\x89', register(2,8),
                                 mem_reg_plus_scaled_reg_plus_const(1))

    ADD_ri, ADD_rr, ADD_rs = common_modes(0)
    OR_ri,  OR_rr,  OR_rs  = common_modes(1)
    AND_ri, AND_rr, AND_rs = common_modes(4)
    SUB_ri, SUB_rr, SUB_rs = common_modes(5)
    XOR_ri, XOR_rr, XOR_rs = common_modes(6)
    CMP_ri, CMP_rr, CMP_rs = common_modes(7)

    NOP = insn('\x90')
    RET = insn('\xC3')

    PUSH_r = insn(rex_nw, register(1), '\x50')

    LEA_rs = insn(rex_w, '\x8D', register(1,8), stack(2))
    LEA32_rs = insn(rex_w, '\x8D', register(1,8), stack(2, force_32bits=True))


class X86_32_CodeBuilder(AbstractX86CodeBuilder):
    WORD = 4


class X86_64_CodeBuilder(AbstractX86CodeBuilder):
    WORD = 8

    def writeimm64(self, imm):
        self.writeimm32(intmask(rffi.cast(rffi.INT, imm)))
        self.writeimm32(imm >> 32)

    # MOV_ri from the parent class is not wrong, but add a better encoding
    # for the common case where the immediate fits in 32 bits
    _MOV_ri32 = insn(rex_w, '\xC7', register(1), '\xC0', immediate(2, 'i'))

    def MOV_ri(self, reg, immed):
        if fits_in_32bits(immed):
            self._MOV_ri32(reg, immed)
        else:
            AbstractX86CodeBuilder.MOV_ri(self, reg, immed)

# ____________________________________________________________

all_instructions = [name for name in AbstractX86CodeBuilder.__dict__
                    if name.split('_')[0].isupper()]
all_instructions.sort()
