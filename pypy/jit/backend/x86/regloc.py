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
        return self.value

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

class AddressLoc(AssemblerLocation):
    _immutable_ = True

    # The address is base_loc + (scaled_loc << scale) + static_offset
    def __init__(self, base_loc, scaled_loc, scale, static_offset):
        assert 0 <= scale < 4
        assert isinstance(base_loc, ImmedLoc) or isinstance(base_loc, RegLoc)
        assert isinstance(scaled_loc, ImmedLoc) or isinstance(scaled_loc, RegLoc)

        if isinstance(base_loc, ImmedLoc):
            if isinstance(scaled_loc, ImmedLoc):
                self.location_code = 'j'
                self.value = base_loc.value + (scaled_loc.value << scale) + static_offset
            else:
                # FIXME
                raise AssertionError("Don't know how to handle this case yet")
        else:
            if isinstance(scaled_loc, ImmedLoc):
                # FIXME: What if base_loc is ebp or esp?
                self.location_code = 'm'
                self.value = (base_loc.value, (scaled_loc.value << scale) + static_offset)
            else:
                self.location_code = 'a'
                self.value = (base_loc.value, scaled_loc.value, scale, static_offset)

    def location_code(self):
        return self.location_code

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

    ADD = _binaryop('ADD')
    OR  = _binaryop('OR')
    AND = _binaryop('AND')
    SUB = _binaryop('SUB')
    XOR = _binaryop('XOR')
    MOV = _binaryop('MOV')
    MOVSD = _binaryop('MOVSD')
    IMUL = _binaryop('IMUL')

    def PUSH(self, loc):
        assert isinstance(loc, RegLoc)
        self.PUSH_r(loc.value)

    def POP(self, loc):
        assert isinstance(loc, RegLoc)
        self.POP_r(loc.value)

    def CMP(self, loc0, loc1):
        if isinstance(loc0, RegLoc):
            val0 = loc0.value
            if isinstance(loc1, RegLoc):
                self.CMP_rr(val0, loc1.value)
            elif isinstance(loc1, StackLoc):
                self.CMP_rb(val0, loc1.value)
            else:
                self.CMP_ri(val0, loc1.getint())
        else:
            assert isinstance(loc0, StackLoc)
            val0 = loc0.value
            if isinstance(loc1, RegLoc):
                self.CMP_br(val0, loc1.value)
            else:
                self.CMP_bi(val0, loc1.getint())

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

all_extra_instructions = [name for name in LocationCodeBuilder.__dict__
                          if name[0].isupper()]
all_extra_instructions.sort()
