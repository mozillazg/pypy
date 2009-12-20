from pypy.jit.metainterp.history import AbstractValue
from pypy.jit.backend.x86 import rx86


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
