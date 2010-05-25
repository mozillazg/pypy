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
        # XXX: Only handling i386 al, cl, dl, bl for now
        assert self.value < 4
        assert not self.is_xmm
        return self

    def location_code(self):
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
                self.value = (None, scaled_loc.value, scale, static_offset)
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
            # XXX: We just hope that the right method exists
            getattr(self, name + '_' + code1 + code2)(loc1.value, loc2.value)
        return INSN

    def _unaryop(name):
        def INSN(self, loc):
            getattr(self, name + '_' + loc.location_code())(loc.value)
        return INSN

    ADD = _binaryop('ADD')
    OR  = _binaryop('OR')
    XOR = _binaryop('XOR')
    SHL = _binaryop('SHL')
    SHR = _binaryop('SHR')
    SAR = _binaryop('SAR')
    TEST = _binaryop('TEST')

    AND = _binaryop('AND')
    SUB = _binaryop('SUB')
    IMUL = _binaryop('IMUL')
    NEG = _unaryop('NEG')

    CMP = _binaryop('CMP')
    MOV = _binaryop('MOV')
    MOV8 = _binaryop('MOV8')
    MOVZX8 = _binaryop('MOVZX8')
    MOVZX16 = _binaryop('MOVZX16')

    LEA = _binaryop('LEA')

    MOVSD = _binaryop('MOVSD')
    ADDSD = _binaryop('ADDSD')
    SUBSD = _binaryop('SUBSD')
    MULSD = _binaryop('MULSD')
    DIVSD = _binaryop('DIVSD')
    UCOMISD = _binaryop('UCOMISD')


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

    def PUSH(self, loc):
        assert isinstance(loc, RegLoc)
        self.PUSH_r(loc.value)

    def POP(self, loc):
        assert isinstance(loc, RegLoc)
        self.POP_r(loc.value)

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
