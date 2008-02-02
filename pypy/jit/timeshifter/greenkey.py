from pypy.rpython.annlowlevel import cachedtype
from pypy.rlib.rarithmetic import intmask
from pypy.rlib.unroll import unrolling_iterable
from pypy.rpython.lltypesystem import lltype

class KeyDesc(object):
    __metaclass__ = cachedtype

    def __init__(self, RGenOp, *TYPES):
        self.RGenOp = RGenOp
        self.TYPES = TYPES
        TARGETTYPES = []
        for TYPE in TYPES:
            # XXX more cases?
            TARGET = lltype.Signed
            if TYPE == lltype.Float:
                TARGET = TYPE
            TARGETTYPES.append(TARGET)

        iterator = unrolling_iterable(enumerate(TARGETTYPES))
        length = len(TYPES)
        def greenhash(self, rgenop):
            retval = 0x345678
            mult = 1000003
            for i, TARGET in iterator:
                genconst = self.values[i]
                item = genconst.revealconst(TARGET)
                retval = intmask((retval ^ hash(item)) * intmask(mult))
                mult = mult + 82520 + 2*length
            return retval
        self.hash = greenhash
        def greencompare(self, other, rgenop):
            for i, TARGET in iterator:
                genconst = self.values[i]
                item_self = genconst.revealconst(TARGET)
                genconst = other.values[i]
                item_other = genconst.revealconst(TARGET)
                if item_self != item_other:
                    return False
            return True
        self.compare = greencompare

    def _freeze_(self):
        return True


class GreenKey(object):
    def __init__(self, values, desc, rgenop):
        self.desc = desc
        self.values = values
        self.rgenop = rgenop

    def __eq__(self, other):
        raise TypeError("don't store GreenKeys in a normal dict")

    def __ne__(self, other):
        raise TypeError("don't store GreenKeys in a normal dict")

    def __hash__(self):
        raise TypeError("not hashable")

def greenkey_eq(self, other):
    assert self.rgenop is other.rgenop
    if self is other:
        return True
    if self.desc is not other.desc:
        return False
    return self.desc.compare(self, other, self.rgenop)

def greenkey_hash(self):
    return self.desc.hash(self, self.rgenop)

