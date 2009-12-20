from pypy.jit.metainterp.history import AbstractValue
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
    def __init__(self, position, ebp_offset):
        assert ebp_offset < 0   # so no confusion with RegLoc.value
        self.position = position
        self.value = ebp_offset
    def __repr__(self):
        return '%d(%%ebp)' % (self.value,)

class RegLoc(AssemblerLocation):
    _immutable_ = True
    def __init__(self, regnum, is_xmm):
        assert regnum >= 0
        self.value = regnum
        self.is_xmm = is_xmm
    def __repr__(self):
        if self.is_xmm:
            return rx86.R.xmmnames[self.value]
        else:
            return rx86.R.names[self.value]

REGLOCS = [RegLoc(i, is_xmm=False) for i in range(8)]
XMMREGLOCS = [RegLoc(i, is_xmm=True) for i in range(8)]
eax, ecx, edx, ebx, esp, ebp, esi, edi = REGLOCS
xmm0, xmm1, xmm2, xmm3, xmm4, xmm5, xmm6, xmm7 = XMMREGLOCS


class LocationCodeBuilder(object):
    _mixin_ = True

    def _binaryop(name):
        def INSN(self, loc1, loc2):
            assert isinstance(loc1, RegLoc)
            val1 = loc1.value
            if isinstance(loc2, RegLoc):
                getattr(self, name + '_rr')(val1, loc2.value)
            elif isinstance(loc2, StackLoc):
                getattr(self, name + '_rb')(val1, loc2.value)
            else:
                getattr(self, name + '_ri')(val1, loc2.getint())
        return INSN

    ADD = _binaryop('ADD')
    OR  = _binaryop('OR')
    AND = _binaryop('AND')
    SUB = _binaryop('SUB')
    XOR = _binaryop('XOR')

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


all_extra_instructions = [name for name in LocationCodeBuilder.__dict__
                          if name[0].isupper()]
all_extra_instructions.sort()
