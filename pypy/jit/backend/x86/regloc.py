from pypy.jit.metainterp.history import AbstractValue, ConstInt
from pypy.jit.backend.x86 import rx86
from pypy.rlib.unroll import unrolling_iterable

#
# This module adds support for "locations", which can be either in a Const,
# or a RegLoc or a StackLoc.  It also adds operations like mc.ADD(), which
# take two locations as arguments, decode them, and calls the right
# mc.ADD_rr()/ADD_rb()/ADD_ri().
#

class AssemblerLocation(AbstractValue):
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
    def __init__(self, position, ebp_offset, num_words):
        assert ebp_offset < 0   # so no confusion with RegLoc.value
        self.position = position
        self.value = ebp_offset
        # XXX: Word size hardcoded
        self.width = num_words * 4
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
        # XXX: Word size
        if self.is_xmm:
            self.width = 8
        else:
            self.width = 4
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
    # XXX: word size hardcoded. And does this even make sense for an immediate?
    width = 4
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

    # XXX
    width = 4
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

REGLOCS = [RegLoc(i, is_xmm=False) for i in range(8)]
XMMREGLOCS = [RegLoc(i, is_xmm=True) for i in range(8)]
eax, ecx, edx, ebx, esp, ebp, esi, edi = REGLOCS
xmm0, xmm1, xmm2, xmm3, xmm4, xmm5, xmm6, xmm7 = XMMREGLOCS

possible_location_codes = list("rbsmajix")
# Separate objects are required because you can't use the same
# unrolling_iterable instance in more than once place
_binop_pc_outer = unrolling_iterable(possible_location_codes)
_binop_pc_inner = unrolling_iterable(possible_location_codes)
_unaryop_pc = unrolling_iterable(possible_location_codes)

class LocationCodeBuilder(object):
    _mixin_ = True

    def _binaryop(name):
        def INSN(self, loc1, loc2):
            code1 = loc1.location_code()
            code2 = loc2.location_code()
            for possible_code1 in _binop_pc_outer:
                if code1 == possible_code1:
                    for possible_code2 in _binop_pc_inner:
                        if code2 == possible_code2:
                            methname = name + "_" + possible_code1 + possible_code2
                            if hasattr(rx86.AbstractX86CodeBuilder, methname):
                                val1 = getattr(loc1, "value_" + possible_code1)()
                                val2 = getattr(loc2, "value_" + possible_code2)()
                                getattr(self, methname)(val1, val2)
                                return
                            else:
                                raise AssertionError("Instruction not defined: " + methname)

        return INSN

    def _unaryop(name):
        def INSN(self, loc):
            code = loc.location_code()
            for possible_code in _unaryop_pc:
                if code == possible_code:
                    methname = name + "_" + possible_code
                    if hasattr(rx86.AbstractX86CodeBuilder, methname):
                        val = getattr(loc, "value_" + possible_code)()
                        getattr(self, methname)(val)
                        return
                    else:
                        raise AssertionError("Instruction not defined: " + methname)

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
    MOV = _binaryop('MOV')
    MOV8 = _binaryop('MOV8')
    MOVZX8 = _binaryop('MOVZX8')
    MOVZX16 = _binaryop('MOVZX16')

    PUSH = _unaryop("PUSH")
    POP = _unaryop("POP")

    LEA = _binaryop('LEA')

    MOVSD = _binaryop('MOVSD')
    ADDSD = _binaryop('ADDSD')
    SUBSD = _binaryop('SUBSD')
    MULSD = _binaryop('MULSD')
    DIVSD = _binaryop('DIVSD')
    UCOMISD = _binaryop('UCOMISD')
    CVTSI2SD = _binaryop('CVTSI2SD')
    CVTTSD2SI = _binaryop('CVTTSD2SI')

    CALL = _unaryop('CALL')

    def MOV16(self, dest_loc, src_loc):
        # Select 16-bit operand mode
        self.writechar('\x66')
        self.MOV(dest_loc, src_loc)

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
