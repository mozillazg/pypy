import py
from pypy.rlib.objectmodel import ComputedIntSymbolic, we_are_translated
from pypy.rlib.objectmodel import specialize
from pypy.rlib.unroll import unrolling_iterable
from pypy.rpython.lltypesystem import rffi

class R(object):
    # the following are synonyms for rax, rcx, etc. on 64 bits
    eax, ecx, edx, ebx, esp, ebp, esi, edi = range(8)

    # xmm registers
    xmm0, xmm1, xmm2, xmm3, xmm4, xmm5, xmm6, xmm7 = range(8)

    # the following are extra registers available only on 64 bits
    r8, r9, r10, r11, r12, r13, r14, r15 = range(8, 16)
    xmm8, xmm9, xmm10, xmm11, xmm12, xmm13, xmm14, xmm15 = range(8, 16)

    names = ['eax', 'ecx', 'edx', 'ebx', 'esp', 'ebp', 'esi', 'edi',
             'r8', 'r9', 'r10', 'r11', 'r12', 'r13', 'r14', 'r15']
    xmmnames = ['xmm%d' % i for i in range(16)]


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
    assert factor in (1, 8)
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
    elif width == 'o':
        return immediate    # in the 'orbyte' for the next command
    elif width == 'q' and mc.WORD == 8:
        mc.writeimm64(immediate)
    else:
        mc.writeimm32(immediate)
    return 0

def immediate(argnum, width='i'):
    return encode_immediate, argnum, width, None

# ____________________________________________________________
# Emit an immediate displacement (relative to the cur insn)

def encode_relative(mc, target, _, orbyte):
    assert orbyte == 0
    offset = target - mc.tell()
    mc.writeimm32(offset)
    return 0

def relative(argnum):
    return encode_relative, argnum, None, None

# ____________________________________________________________
# Emit a mod/rm referencing a stack location [EBP+offset]

@specialize.arg(2)
def encode_stack_bp(mc, offset, force_32bits, orbyte):
    if not force_32bits and single_byte(offset):
        mc.writeimm8(offset)
        mc.writechar(chr(0x40 | orbyte | R.ebp))
    else:
        mc.writeimm32(offset)
        mc.writechar(chr(0x80 | orbyte | R.ebp))
    return 0

def stack_bp(argnum, force_32bits=False):
    return encode_stack_bp, argnum, force_32bits, None

# ____________________________________________________________
# Emit a mod/rm referencing a stack location [ESP+offset]

def encode_stack_sp(mc, offset, _, orbyte):
    SIB = chr((R.esp<<3) | R.esp)    #   use [esp+(no index)+offset]
    if offset == 0:
        mc.writechar(SIB)
        mc.writechar(chr(0x04 | orbyte))
    elif single_byte(offset):
        mc.writeimm8(offset)
        mc.writechar(SIB)
        mc.writechar(chr(0x44 | orbyte))
    else:
        mc.writeimm32(offset)
        mc.writechar(SIB)
        mc.writechar(chr(0x84 | orbyte))
    return 0

def stack_sp(argnum):
    return encode_stack_sp, argnum, None, None

# ____________________________________________________________
# Emit a mod/rm referencing a memory location [reg1+offset]

def encode_mem_reg_plus_const(mc, (reg, offset), _, orbyte):
    assert reg != R.esp and reg != R.ebp
    #
    reg1 = reg_number_3bits(mc, reg)
    no_offset = offset == 0
    SIB = -1
    # 64-bits special cases for reg1 == r12 or r13
    # (which look like esp or ebp after being truncated to 3 bits)
    if mc.WORD == 8:
        if reg1 == R.esp:               # forces an SIB byte:
            SIB = (R.esp<<3) | R.esp    #   use [r12+(no index)+offset]
        elif reg1 == R.ebp:
            no_offset = False
    # end of 64-bits special cases
    if no_offset:
        if SIB >= 0: mc.writechar(chr(SIB))
        mc.writechar(chr(0x00 | orbyte | reg1))
    elif single_byte(offset):
        mc.writeimm8(offset)
        if SIB >= 0: mc.writechar(chr(SIB))
        mc.writechar(chr(0x40 | orbyte | reg1))
    else:
        mc.writeimm32(offset)
        if SIB >= 0: mc.writechar(chr(SIB))
        mc.writechar(chr(0x80 | orbyte | reg1))
    return 0

def rex_mem_reg_plus_const(mc, (reg, offset), _):
    if reg >= 8:
        return REX_B
    return 0

def mem_reg_plus_const(argnum):
    return encode_mem_reg_plus_const, argnum, None, rex_mem_reg_plus_const

# ____________________________________________________________
# Emit a mod/rm referencing an array memory location [reg1+reg2*scale+offset]

def encode_mem_reg_plus_scaled_reg_plus_const(mc,
                                              (reg1, reg2, scaleshift, offset),
                                              _, orbyte):
    # emit "reg1 + (reg2 << scaleshift) + offset"
    assert reg1 != R.ebp and reg2 != R.esp
    assert 0 <= scaleshift < 4
    reg1 = reg_number_3bits(mc, reg1)
    reg2 = reg_number_3bits(mc, reg2)
    SIB = chr((scaleshift<<6) | (reg2<<3) | reg1)
    #
    no_offset = offset == 0
    # 64-bits special case for reg1 == r13
    # (which look like ebp after being truncated to 3 bits)
    if mc.WORD == 8:
        if reg1 == R.ebp:
            no_offset = False
    # end of 64-bits special case
    if no_offset:
        mc.writechar(SIB)
        mc.writechar(chr(0x04 | orbyte))
    elif single_byte(offset):
        mc.writeimm8(offset)
        mc.writechar(SIB)
        mc.writechar(chr(0x44 | orbyte))
    else:
        mc.writeimm32(offset)
        mc.writechar(SIB)
        mc.writechar(chr(0x84 | orbyte))
    return 0

def rex_mem_reg_plus_scaled_reg_plus_const(mc,
                                           (reg1, reg2, scaleshift, offset),
                                           _):
    rex = 0
    if reg1 >= 8: rex |= REX_B
    if reg2 >= 8: rex |= REX_X
    return rex

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
def encode_rex(mc, rexbyte, basevalue, orbyte):
    if mc.WORD == 8:
        assert 0 <= rexbyte < 8
        if basevalue != 0x40 or rexbyte != 0:
            mc.writechar(chr(basevalue | rexbyte))
    else:
        assert rexbyte == 0
    return 0

rex_w  = encode_rex, 0, (0x40 | REX_W), None
rex_nw = encode_rex, 0, 0x40, None

# ____________________________________________________________

def insn(*encoding):
    def encode(mc, *args):
        # emit the bytes of the instruction
        rexbyte = 0
        orbyte = 0
        for encode_step, arg, extra, rex_step in encoding_steps:
            if arg is not None:
                if arg == 0:
                    arg = rexbyte
                else:
                    arg = args[arg-1]
            if rex_step and mc.WORD == 8:
                rexbyte |= rex_step(mc, arg, extra)
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
    encoding_steps.reverse()
    encoding_steps = unrolling_iterable(encoding_steps)
    return encode

def xmminsn(*encoding):
    encode = insn(*encoding)
    encode.is_xmm_insn = True
    return encode

def common_modes(group):
    base = group * 8
    char = chr(0xC0 | base)
    INSN_ri8 = insn(rex_w, '\x83', char, register(1), immediate(2,'b'))
    INSN_ri32= insn(rex_w, '\x81', char, register(1), immediate(2))
    INSN_rr = insn(rex_w, chr(base+1), '\xC0', register(2,8), register(1,1))
    INSN_br = insn(rex_w, chr(base+1), stack_bp(1), register(2,8))
    INSN_rb = insn(rex_w, chr(base+3), stack_bp(2), register(1,8))
    INSN_bi8 = insn(rex_w, '\x83', stack_bp(1), orbyte(base), immediate(2,'b'))
    INSN_bi32= insn(rex_w, '\x81', stack_bp(1), orbyte(base), immediate(2))

    def INSN_ri(mc, reg, immed):
        if single_byte(immed):
            INSN_ri8(mc, reg, immed)
        else:
            INSN_ri32(mc, reg, immed)
    INSN_ri._always_inline_ = True      # try to constant-fold single_byte()

    def INSN_bi(mc, offset, immed):
        if single_byte(immed):
            INSN_bi8(mc, offset, immed)
        else:
            INSN_bi32(mc, offset, immed)
    INSN_bi._always_inline_ = True      # try to constant-fold single_byte()

    return INSN_ri, INSN_rr, INSN_rb, INSN_bi, INSN_br

# ____________________________________________________________


class AbstractX86CodeBuilder(object):
    """Abstract base class."""

    def writechar(self, char):
        raise NotImplementedError

    def writeimm8(self, imm):
        self.writechar(chr(imm & 0xFF))

    def writeimm16(self, imm):
        self.writechar(chr((imm >> 8) & 0xFF))
        self.writechar(chr(imm & 0xFF))

    def writeimm32(self, imm):
        assert fits_in_32bits(imm)
        self.writechar(chr((imm >> 24) & 0xFF))
        self.writechar(chr((imm >> 16) & 0xFF))
        self.writechar(chr((imm >> 8) & 0xFF))
        self.writechar(chr(imm & 0xFF))

    # ------------------------------ MOV ------------------------------

    MOV_ri = insn(rex_w, '\xB8', register(1), immediate(2, 'q'))
    MOV_rr = insn(rex_w, '\x89', '\xC0', register(2,8), register(1))
    MOV_br = insn(rex_w, '\x89', stack_bp(1), register(2,8))
    MOV_rb = insn(rex_w, '\x8B', stack_bp(2), register(1,8))

    # "MOV reg1, [reg2+offset]" and the opposite direction
    MOV_rm = insn(rex_w, '\x8B', mem_reg_plus_const(2), register(1,8))
    MOV_mr = insn(rex_w, '\x89', mem_reg_plus_const(1), register(2,8))
    MOV_mi = insn(rex_w, '\xC7', mem_reg_plus_const(1), orbyte(0<<3),
                                 immediate(2, 'i'))

    # "MOV reg1, [reg2+reg3*scale+offset]" and the opposite direction
    MOV_ra = insn(rex_w, '\x8B', mem_reg_plus_scaled_reg_plus_const(2),
                                 register(1,8))
    MOV_ar = insn(rex_w, '\x89', mem_reg_plus_scaled_reg_plus_const(1),
                                 register(2,8))

    # "MOV reg1, [immediate2]" and the opposite direction
    MOV_rj = insn(rex_w, '\x8B', '\x05', register(1,8), immediate(2))
    MOV_jr = insn(rex_w, '\x89', '\x05', register(2,8), immediate(1))

    # ------------------------------ Arithmetic ------------------------------

    ADD_ri, ADD_rr, ADD_rb, _, _ = common_modes(0)
    OR_ri,  OR_rr,  OR_rb,  _, _ = common_modes(1)
    AND_ri, AND_rr, AND_rb, _, _ = common_modes(4)
    SUB_ri, SUB_rr, SUB_rb, _, _ = common_modes(5)
    XOR_ri, XOR_rr, XOR_rb, _, _ = common_modes(6)
    CMP_ri, CMP_rr, CMP_rb, CMP_bi, CMP_br = common_modes(7)

    # ------------------------------ Misc stuff ------------------------------

    NOP = insn('\x90')
    RET = insn('\xC3')

    PUSH_r = insn(rex_nw, '\x50', register(1))
    POP_r = insn(rex_nw, '\x58', register(1))

    LEA_rb = insn(rex_w, '\x8D', stack_bp(2), register(1,8))
    LEA32_rb = insn(rex_w, '\x8D', stack_bp(2,force_32bits=True),register(1,8))

    CALL_l = insn('\xE8', relative(1))
    CALL_r = insn(rex_nw, '\xFF', chr(0xC0 | (2<<3)), register(1))
    CALL_b = insn('\xFF', stack_bp(1), orbyte(2<<3))

    XCHG_rm = insn(rex_w, '\x87', mem_reg_plus_const(2), register(1,8))

    JMP_l = insn('\xE9', relative(1))
    J_il = insn('\x0F\x80', immediate(1,'o'), relative(2))
    SET_ir = insn('\x0F\x90', immediate(1,'o'), '\xC0', register(2))

    # ------------------------------ SSE2 ------------------------------

    MOVSD_rr = xmminsn('\xF2', rex_nw,'\x0F\x10\xC0',register(1,8),register(2))
    MOVSD_rb = xmminsn('\xF2', rex_nw, '\x0F\x10', stack_bp(2), register(1,8))
    MOVSD_br = xmminsn('\xF2', rex_nw, '\x0F\x11', stack_bp(1), register(2,8))
    MOVSD_rs = xmminsn('\xF2', rex_nw, '\x0F\x10', stack_sp(2), register(1,8))
    MOVSD_sr = xmminsn('\xF2', rex_nw, '\x0F\x11', stack_sp(1), register(2,8))
    MOVSD_rm = xmminsn('\xF2', rex_nw, '\x0F\x10', mem_reg_plus_const(2),
                                                   register(1,8))
    MOVSD_mr = xmminsn('\xF2', rex_nw, '\x0F\x11', mem_reg_plus_const(1),
                                                   register(2,8))

    # ------------------------------------------------------------

Conditions = {
     'O':  0,
    'NO':  1,
     'C':  2,     'B':  2,   'NAE':  2,
    'NC':  3,    'NB':  3,    'AE':  3,
     'Z':  4,     'E':  4,
    'NZ':  5,    'NE':  5,
                 'BE':  6,    'NA':  6,
                'NBE':  7,     'A':  7,
     'S':  8,
    'NS':  9,
     'P': 10,    'PE': 10,
    'NP': 11,    'PO': 11,
                  'L': 12,   'NGE': 12,
                 'NL': 13,    'GE': 13,
                 'LE': 14,    'NG': 14,
                'NLE': 15,     'G': 15,
}


class X86_32_CodeBuilder(AbstractX86CodeBuilder):
    WORD = 4


class X86_64_CodeBuilder(AbstractX86CodeBuilder):
    WORD = 8

    def writeimm64(self, imm):
        self.writechar(chr((imm >> 56) & 0xFF))
        self.writechar(chr((imm >> 48) & 0xFF))
        self.writechar(chr((imm >> 40) & 0xFF))
        self.writechar(chr((imm >> 32) & 0xFF))
        self.writechar(chr((imm >> 24) & 0xFF))
        self.writechar(chr((imm >> 16) & 0xFF))
        self.writechar(chr((imm >> 8) & 0xFF))
        self.writechar(chr(imm & 0xFF))

    # MOV_ri from the parent class is not wrong, but here is a better encoding
    # for the common case where the immediate fits in 32 bits
    _MOV_ri32 = insn(rex_w, '\xC7\xC0', register(1), immediate(2, 'i'))

    def MOV_ri(self, reg, immed):
        if fits_in_32bits(immed):
            self._MOV_ri32(reg, immed)
        else:
            AbstractX86CodeBuilder.MOV_ri(self, reg, immed)

    # case of a 64-bit immediate: encode via RAX (assuming it's ok to
    # randomly change this register at that point in time)
    def CALL_l(self, target):
        offset = target - (self.tell() + 5)
        if fits_in_32bits(offset):
            AbstractX86CodeBuilder.CALL_l(self, target)
        else:
            AbstractX86CodeBuilder.CALL_r(self, R.eax)
            AbstractX86CodeBuilder.MOV_ri(self, R.eax, target)

    # unsupported -- must use e.g. MOV tmpreg, immed64; MOV reg, [tmpreg]
    def MOV_rj(self, reg, mem_immed):
        py.test.skip("MOV_rj unsupported")
    def MOV_jr(self, mem_immed, reg):
        py.test.skip("MOV_jr unsupported")

# ____________________________________________________________

all_instructions = [name for name in AbstractX86CodeBuilder.__dict__
                    if name.split('_')[0].isupper()]
all_instructions.sort()
