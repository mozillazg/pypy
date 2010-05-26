from pypy.jit.metainterp.history import AbstractValue, ConstInt
from pypy.jit.backend.x86 import rx86

#
# This module adds support for "locations", which can be either in a Const,
# or a RegLoc or a StackLoc.  It also adds operations like mc.ADD(), which
# take two locations as arguments, decode them, and calls the right
# mc.ADD_rr()/ADD_rb()/ADD_ri().
#

class AssemblerLocation(AbstractValue):
    __slots__ = 'value'
    _immutable_ = True
    def _getregkey(self):
        return self.value


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
                self.value = (None, scaled_loc.value, scale, base_loc.value + static_offset)
        else:
            if isinstance(scaled_loc, ImmedLoc):
                # FIXME: What if base_loc is ebp or esp?
                self._location_code = 'm'
                self.value = (base_loc.value, (scaled_loc.value << scale) + static_offset)
            else:
                self._location_code = 'a'
                self.value = (base_loc.value, scaled_loc.value, scale, static_offset)

    def location_code(self):
        return self._location_code

    def value(self):
        return self.value

REGLOCS = [RegLoc(i, is_xmm=False) for i in range(8)]
XMMREGLOCS = [RegLoc(i, is_xmm=True) for i in range(8)]
eax, ecx, edx, ebx, esp, ebp, esi, edi = REGLOCS
xmm0, xmm1, xmm2, xmm3, xmm4, xmm5, xmm6, xmm7 = XMMREGLOCS


class LocationCodeBuilder(object):
    _mixin_ = True

    def _binaryop(name):
        def INSN(self, loc1, loc2):
            code1 = loc1.location_code()
            code2 = loc2.location_code()
            # XXX: All possible combinations are given, even those that are
            # impossible
            if code1 == 'r' and code2 == 'r':
                getattr(self, name + "_rr")(loc1.value, loc2.value)
            elif code1 == 'r' and code2 == 'b':
                getattr(self, name + "_rb")(loc1.value, loc2.value)
            elif code1 == 'r' and code2 == 's':
                getattr(self, name + "_rs")(loc1.value, loc2.value)
            elif code1 == 'r' and code2 == 'm':
                getattr(self, name + "_rm")(loc1.value, loc2.value)
            elif code1 == 'r' and code2 == 'a':
                getattr(self, name + "_ra")(loc1.value, loc2.value)
            elif code1 == 'r' and code2 == 'j':
                getattr(self, name + "_rj")(loc1.value, loc2.value)
            elif code1 == 'r' and code2 == 'i':
                getattr(self, name + "_ri")(loc1.value, loc2.value)
            elif code1 == 'r' and code2 == 'x':
                getattr(self, name + "_rx")(loc1.value, loc2.value)
            elif code1 == 'b' and code2 == 'r':
                getattr(self, name + "_br")(loc1.value, loc2.value)
            elif code1 == 'b' and code2 == 'b':
                getattr(self, name + "_bb")(loc1.value, loc2.value)
            elif code1 == 'b' and code2 == 's':
                getattr(self, name + "_bs")(loc1.value, loc2.value)
            elif code1 == 'b' and code2 == 'm':
                getattr(self, name + "_bm")(loc1.value, loc2.value)
            elif code1 == 'b' and code2 == 'a':
                getattr(self, name + "_ba")(loc1.value, loc2.value)
            elif code1 == 'b' and code2 == 'j':
                getattr(self, name + "_bj")(loc1.value, loc2.value)
            elif code1 == 'b' and code2 == 'i':
                getattr(self, name + "_bi")(loc1.value, loc2.value)
            elif code1 == 'b' and code2 == 'x':
                getattr(self, name + "_bx")(loc1.value, loc2.value)
            elif code1 == 's' and code2 == 'r':
                getattr(self, name + "_sr")(loc1.value, loc2.value)
            elif code1 == 's' and code2 == 'b':
                getattr(self, name + "_sb")(loc1.value, loc2.value)
            elif code1 == 's' and code2 == 's':
                getattr(self, name + "_ss")(loc1.value, loc2.value)
            elif code1 == 's' and code2 == 'm':
                getattr(self, name + "_sm")(loc1.value, loc2.value)
            elif code1 == 's' and code2 == 'a':
                getattr(self, name + "_sa")(loc1.value, loc2.value)
            elif code1 == 's' and code2 == 'j':
                getattr(self, name + "_sj")(loc1.value, loc2.value)
            elif code1 == 's' and code2 == 'i':
                getattr(self, name + "_si")(loc1.value, loc2.value)
            elif code1 == 's' and code2 == 'x':
                getattr(self, name + "_sx")(loc1.value, loc2.value)
            elif code1 == 'm' and code2 == 'r':
                getattr(self, name + "_mr")(loc1.value, loc2.value)
            elif code1 == 'm' and code2 == 'b':
                getattr(self, name + "_mb")(loc1.value, loc2.value)
            elif code1 == 'm' and code2 == 's':
                getattr(self, name + "_ms")(loc1.value, loc2.value)
            elif code1 == 'm' and code2 == 'm':
                getattr(self, name + "_mm")(loc1.value, loc2.value)
            elif code1 == 'm' and code2 == 'a':
                getattr(self, name + "_ma")(loc1.value, loc2.value)
            elif code1 == 'm' and code2 == 'j':
                getattr(self, name + "_mj")(loc1.value, loc2.value)
            elif code1 == 'm' and code2 == 'i':
                getattr(self, name + "_mi")(loc1.value, loc2.value)
            elif code1 == 'm' and code2 == 'x':
                getattr(self, name + "_mx")(loc1.value, loc2.value)
            elif code1 == 'a' and code2 == 'r':
                getattr(self, name + "_ar")(loc1.value, loc2.value)
            elif code1 == 'a' and code2 == 'b':
                getattr(self, name + "_ab")(loc1.value, loc2.value)
            elif code1 == 'a' and code2 == 's':
                getattr(self, name + "_as")(loc1.value, loc2.value)
            elif code1 == 'a' and code2 == 'm':
                getattr(self, name + "_am")(loc1.value, loc2.value)
            elif code1 == 'a' and code2 == 'a':
                getattr(self, name + "_aa")(loc1.value, loc2.value)
            elif code1 == 'a' and code2 == 'j':
                getattr(self, name + "_aj")(loc1.value, loc2.value)
            elif code1 == 'a' and code2 == 'i':
                getattr(self, name + "_ai")(loc1.value, loc2.value)
            elif code1 == 'a' and code2 == 'x':
                getattr(self, name + "_ax")(loc1.value, loc2.value)
            elif code1 == 'j' and code2 == 'r':
                getattr(self, name + "_jr")(loc1.value, loc2.value)
            elif code1 == 'j' and code2 == 'b':
                getattr(self, name + "_jb")(loc1.value, loc2.value)
            elif code1 == 'j' and code2 == 's':
                getattr(self, name + "_js")(loc1.value, loc2.value)
            elif code1 == 'j' and code2 == 'm':
                getattr(self, name + "_jm")(loc1.value, loc2.value)
            elif code1 == 'j' and code2 == 'a':
                getattr(self, name + "_ja")(loc1.value, loc2.value)
            elif code1 == 'j' and code2 == 'j':
                getattr(self, name + "_jj")(loc1.value, loc2.value)
            elif code1 == 'j' and code2 == 'i':
                getattr(self, name + "_ji")(loc1.value, loc2.value)
            elif code1 == 'j' and code2 == 'x':
                getattr(self, name + "_jx")(loc1.value, loc2.value)
            elif code1 == 'i' and code2 == 'r':
                getattr(self, name + "_ir")(loc1.value, loc2.value)
            elif code1 == 'i' and code2 == 'b':
                getattr(self, name + "_ib")(loc1.value, loc2.value)
            elif code1 == 'i' and code2 == 's':
                getattr(self, name + "_is")(loc1.value, loc2.value)
            elif code1 == 'i' and code2 == 'm':
                getattr(self, name + "_im")(loc1.value, loc2.value)
            elif code1 == 'i' and code2 == 'a':
                getattr(self, name + "_ia")(loc1.value, loc2.value)
            elif code1 == 'i' and code2 == 'j':
                getattr(self, name + "_ij")(loc1.value, loc2.value)
            elif code1 == 'i' and code2 == 'i':
                getattr(self, name + "_ii")(loc1.value, loc2.value)
            elif code1 == 'i' and code2 == 'x':
                getattr(self, name + "_ix")(loc1.value, loc2.value)
            elif code1 == 'x' and code2 == 'r':
                getattr(self, name + "_xr")(loc1.value, loc2.value)
            elif code1 == 'x' and code2 == 'b':
                getattr(self, name + "_xb")(loc1.value, loc2.value)
            elif code1 == 'x' and code2 == 's':
                getattr(self, name + "_xs")(loc1.value, loc2.value)
            elif code1 == 'x' and code2 == 'm':
                getattr(self, name + "_xm")(loc1.value, loc2.value)
            elif code1 == 'x' and code2 == 'a':
                getattr(self, name + "_xa")(loc1.value, loc2.value)
            elif code1 == 'x' and code2 == 'j':
                getattr(self, name + "_xj")(loc1.value, loc2.value)
            elif code1 == 'x' and code2 == 'i':
                getattr(self, name + "_xi")(loc1.value, loc2.value)
            elif code1 == 'x' and code2 == 'x':
                getattr(self, name + "_xx")(loc1.value, loc2.value)
            else:
                raise AssertionError("Invalid location codes")

        return INSN

    def _unaryop(name):
        def INSN(self, loc):
            code = loc.location_code()
            # "if" is unrolled for RPython
            if code == 'r':
                getattr(self, name + '_r')(loc.value)
            elif code == 'b':
                getattr(self, name + '_b')(loc.value)
            elif code == 's':
                getattr(self, name + '_s')(loc.value)
            elif code == 'm':
                getattr(self, name + '_m')(loc.value)
            elif code == 'a':
                getattr(self, name + '_a')(loc.value)
            elif code == 'j':
                getattr(self, name + '_j')(loc.value)
            elif code == 'i':
                getattr(self, name + '_i')(loc.value)
            elif code == 'x':
                getattr(self, name + '_x')(loc.value)
            else:
                raise AssertionError("Unknown code")
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


    def CALL(self, loc):
        # FIXME: Kludge that works in 32-bit because the "relative" CALL is
        # actually absolute on i386
        if loc.location_code() == 'j':
            self.CALL_l(loc.value)
        else:
            getattr(self, 'CALL_' + loc.location_code())(loc.value)

    def MOV16(self, dest_loc, src_loc):
        # Select 16-bit operand mode
        self.writechar('\x66')
        self.MOV(dest_loc, src_loc)

    def CMPi(self, loc0, loc1):
        # like CMP, but optimized for the case of loc1 being a Const
        assert isinstance(loc1, Const)
        if isinstance(loc0, RegLoc):
            self.CMP_ri(loc0.value, loc1.getint())
        else:
            assert isinstance(loc0, StackLoc)
            self.CMP_bi(loc0.value, loc1.getint())

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
