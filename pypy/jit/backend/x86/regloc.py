from pypy.jit.metainterp.history import AbstractValue, ConstInt
from pypy.jit.backend.x86 import rx86
from pypy.rlib.unroll import unrolling_iterable
from pypy.jit.backend.x86.arch import WORD

#
# This module adds support for "locations", which can be either in a Const,
# or a RegLoc or a StackLoc.  It also adds operations like mc.ADD(), which
# take two locations as arguments, decode them, and calls the right
# mc.ADD_rr()/ADD_rb()/ADD_ri().
#

class AssemblerLocation(object):
    # XXX: Is adding "width" here correct?
    __slots__ = ('value', 'width')
    _immutable_ = True
    def _getregkey(self):
        return self.value

    def value_r(self): return self.value
    def value_b(self): return self.value
    def value_s(self): return self.value
    def value_j(self): return self.value
    def value_i(self): return self.value
    def value_x(self): return self.value

class StackLoc(AssemblerLocation):
    _immutable_ = True
    def __init__(self, position, ebp_offset, num_words, type):
        assert ebp_offset < 0   # so no confusion with RegLoc.value
        self.position = position
        self.value = ebp_offset
        self.width = num_words * WORD
        # One of INT, REF, FLOAT
        self.type = type

    def frame_size(self):
        return self.width // WORD

    def __repr__(self):
        return '%d(%%ebp)' % (self.value,)

    def location_code(self):
        return 'b'

    # FIXME: This definition of assembler sufficient?
    def assembler(self):
        return repr(self)

class RegLoc(AssemblerLocation):
    _immutable_ = True
    def __init__(self, regnum, is_xmm):
        assert regnum >= 0
        self.value = regnum
        self.is_xmm = is_xmm
        if self.is_xmm:
            self.width = 8
        else:
            self.width = WORD
    def __repr__(self):
        if self.is_xmm:
            return rx86.R.xmmnames[self.value]
        else:
            return rx86.R.names[self.value]

    def lowest8bits(self):
        assert not self.is_xmm
        return RegLoc(rx86.low_byte(self.value), False)

    def higher8bits(self):
        assert not self.is_xmm
        return RegLoc(rx86.high_byte(self.value), False)

    def location_code(self):
        if self.is_xmm:
            return 'x'
        else:
            return 'r'

    # FIXME: This definition of assembler sufficient?
    def assembler(self):
        return '%' + repr(self)

class ImmedLoc(AssemblerLocation):
    _immutable_ = True
    # XXX: Does this even make sense for an immediate?
    width = WORD
    def __init__(self, value):
        self.value = value

    def location_code(self):
        return 'i'

    def getint(self):
        return self.value

    def __repr__(self):
        return "ImmedLoc(%d)" % (self.value)

    def lowest8bits(self):
        val = self.value & 0xFF
        if val > 0x7F:
            val -= 0x100
        return ImmedLoc(val)

class AddressLoc(AssemblerLocation):
    _immutable_ = True

    width = WORD
    # The address is base_loc + (scaled_loc << scale) + static_offset
    def __init__(self, base_loc, scaled_loc, scale=0, static_offset=0):
        assert 0 <= scale < 4
        assert isinstance(base_loc, ImmedLoc) or isinstance(base_loc, RegLoc)
        assert isinstance(scaled_loc, ImmedLoc) or isinstance(scaled_loc, RegLoc)

        if isinstance(base_loc, ImmedLoc):
            if isinstance(scaled_loc, ImmedLoc):
                self._location_code = 'j'
                self.value = base_loc.value + (scaled_loc.value << scale) + static_offset
            else:
                self._location_code = 'a'
                self.loc_a = (rx86.NO_BASE_REGISTER, scaled_loc.value, scale, base_loc.value + static_offset)
        else:
            if isinstance(scaled_loc, ImmedLoc):
                # FIXME: What if base_loc is ebp or esp?
                self._location_code = 'm'
                self.loc_m = (base_loc.value, (scaled_loc.value << scale) + static_offset)
            else:
                self._location_code = 'a'
                self.loc_a = (base_loc.value, scaled_loc.value, scale, static_offset)

    def location_code(self):
        return self._location_code

    def value_a(self):
        return self.loc_a

    def value_m(self):
        return self.loc_m

REGLOCS = [RegLoc(i, is_xmm=False) for i in range(16)]
XMMREGLOCS = [RegLoc(i, is_xmm=True) for i in range(16)]
eax, ecx, edx, ebx, esp, ebp, esi, edi, r8, r9, r10, r11, r12, r13, r14, r15 = REGLOCS
xmm0, xmm1, xmm2, xmm3, xmm4, xmm5, xmm6, xmm7, xmm8, xmm9, xmm10, xmm11, xmm12, xmm13, xmm14, xmm15 = XMMREGLOCS

X86_64_SCRATCH_REG = r11
# XXX: a GPR scratch register is definitely needed, but we could probably do
# without an xmm scratch reg.
X86_64_XMM_SCRATCH_REG = xmm15

unrolling_location_codes = unrolling_iterable(list("rbsmajix"))

class LocationCodeBuilder(object):
    _mixin_ = True

    def _binaryop(name):
        def INSN(self, loc1, loc2):
            code1 = loc1.location_code()
            code2 = loc2.location_code()
            for possible_code1 in unrolling_location_codes:
                if code1 == possible_code1:
                    for possible_code2 in unrolling_location_codes:
                        if code2 == possible_code2:
                            # FIXME: Not RPython anymore!
                            # Fake out certain operations for x86_64
                            val1 = getattr(loc1, "value_" + possible_code1)()
                            val2 = getattr(loc2, "value_" + possible_code2)()
                            # XXX: Could use RIP+disp32 in some cases
                            if self.WORD == 8 and possible_code2 == 'i' and not rx86.fits_in_32bits(val2):
                                if possible_code1 == 'j':
                                    # This is the worst case: MOV_ji, and both operands are 64-bit
                                    # Hopefully this doesn't happen too often
                                    self.PUSH_r(eax.value)
                                    self.MOV_ri(eax.value, val1)
                                    self.MOV_ri(X86_64_SCRATCH_REG.value, val2)
                                    self.MOV_mr((eax.value, 0), X86_64_SCRATCH_REG.value)
                                    self.POP_r(eax.value)
                                else:
                                    self.MOV_ri(X86_64_SCRATCH_REG.value, val2)
                                    getattr(self, name + "_" + possible_code1 + "r")(val1, X86_64_SCRATCH_REG.value)
                            elif self.WORD == 8 and possible_code1 == 'j':
                                self.MOV_ri(X86_64_SCRATCH_REG.value, val1)
                                getattr(self, name + "_" + "m" + possible_code2)((X86_64_SCRATCH_REG.value, 0), val2)
                            elif self.WORD == 8 and possible_code2 == 'j':
                                self.MOV_ri(X86_64_SCRATCH_REG.value, val2)
                                getattr(self, name + "_" + possible_code1 + "m")(val1, (X86_64_SCRATCH_REG.value, 0))
                            else:
                                methname = name + "_" + possible_code1 + possible_code2
                                getattr(self, methname)(val1, val2)

        return INSN

    def _unaryop(name):
        def INSN(self, loc):
            code = loc.location_code()
            for possible_code in unrolling_location_codes:
                if code == possible_code:
                    methname = name + "_" + possible_code
                    # if hasattr(rx86.AbstractX86CodeBuilder, methname):
                    if hasattr(self, methname):
                        val = getattr(loc, "value_" + possible_code)()
                        getattr(self, methname)(val)
                        return
                    else:
                        raise AssertionError("Instruction not defined: " + methname)

        return INSN

    def _16_bit_binaryop(name):
        def INSN(self, loc1, loc2):
            # Select 16-bit operand mode
            self.writechar('\x66')
            # XXX: Hack to let immediate() in rx86 know to do a 16-bit encoding
            self._use_16_bit_immediate = True
            getattr(self, name)(loc1, loc2)
            self._use_16_bit_immediate = False

        return INSN

    AND = _binaryop('AND')
    OR  = _binaryop('OR')
    XOR = _binaryop('XOR')
    NOT = _unaryop('NOT')
    SHL = _binaryop('SHL')
    SHR = _binaryop('SHR')
    SAR = _binaryop('SAR')
    TEST = _binaryop('TEST')

    ADD = _binaryop('ADD')
    SUB = _binaryop('SUB')
    IMUL = _binaryop('IMUL')
    NEG = _unaryop('NEG')

    CMP = _binaryop('CMP')
    CMP16 = _16_bit_binaryop('CMP')
    MOV = _binaryop('MOV')
    MOV8 = _binaryop('MOV8')
    MOV16 = _16_bit_binaryop('MOV')
    MOVZX8 = _binaryop('MOVZX8')
    MOVZX16 = _binaryop('MOVZX16')
    MOV32 = _binaryop('MOV32')
    XCHG = _binaryop('XCHG')

    PUSH = _unaryop('PUSH')
    POP = _unaryop('POP')

    LEA = _binaryop('LEA')

    MOVSD = _binaryop('MOVSD')
    ADDSD = _binaryop('ADDSD')
    SUBSD = _binaryop('SUBSD')
    MULSD = _binaryop('MULSD')
    DIVSD = _binaryop('DIVSD')
    UCOMISD = _binaryop('UCOMISD')
    CVTSI2SD = _binaryop('CVTSI2SD')
    CVTTSD2SI = _binaryop('CVTTSD2SI')

    ANDPD = _binaryop('ANDPD')
    XORPD = _binaryop('XORPD')

    CALL = _unaryop('CALL')

def imm(x):
    # XXX: ri386 migration shim
    if isinstance(x, ConstInt):
        return ImmedLoc(x.getint())
    else:
        return ImmedLoc(x)

def rel32(x):
    # XXX: ri386 migration shim
    return AddressLoc(ImmedLoc(x), ImmedLoc(0))

all_extra_instructions = [name for name in LocationCodeBuilder.__dict__
                          if name[0].isupper()]
all_extra_instructions.sort()
