from pypy.rpython.annlowlevel import cachedtype
from pypy.rlib.rarithmetic import intmask
from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.objectmodel import r_dict
from pypy.rpython.lltypesystem import lltype

# XXX green dicts are unsafe with moving GCs

class KeyDesc(object):
    __metaclass__ = cachedtype

    def __init__(self, RGenOp=None, *TYPES):
        self.RGenOp = RGenOp
        self.TYPES = TYPES
        self.nb_vals = len(TYPES)
        if not TYPES:
            assert RGenOp is None

        if RGenOp is None:
            assert len(TYPES) == 0
            self.hash = lambda self: 0
            self.compare = lambda self, other: True

        index_TYPE = []
        for i, TYPE in enumerate(TYPES):
            # XXX more cases?
            TARGET = lltype.Signed
            if TYPE == lltype.Void:
                continue
            elif TYPE == lltype.Float:
                TARGET = TYPE
            index_TYPE.append((i, TARGET))

        iterator = unrolling_iterable(index_TYPE)
        length = len(TYPES)
        def greenhash(self):
            retval = 0x345678
            mult = 1000003
            for i, TARGET in iterator:
                genconst = self.values[i]
                item = genconst.revealconst(TARGET)
                retval = intmask((retval ^ hash(item)) * intmask(mult))
                mult = mult + 82520 + 2*length
            return retval
        self.hash = greenhash
        def greencompare(self, other):
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
    def __init__(self, values, desc):
        assert len(values) == desc.nb_vals
        self.desc = desc
        self.values = values

    def __eq__(self, other):
        raise TypeError("don't store GreenKeys in a normal dict")

    def __ne__(self, other):
        raise TypeError("don't store GreenKeys in a normal dict")

    def __hash__(self):
        if len(self.values) == 0:
            # to support using the empty_key as an annotation-time constant
            return 7623876
        raise TypeError("not hashable")

def greenkey_eq(self, other):
    if self is other:
        return True
    if self.desc is not other.desc:
        return False
    return self.desc.compare(self, other)

def greenkey_hash(self):
    return self.desc.hash(self)

def newgreendict():
    return r_dict(greenkey_eq, greenkey_hash)

empty_key = GreenKey([], KeyDesc())
