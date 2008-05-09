import random, sys
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.memory import lldict


class TestLLAddressDict:

    def setup_method(self, meth):
        lldict.alloc_count = 0

    def test_basics(self):
        d = lldict.newdict()
        d.add(intaddr(42))
        d.setitem(intaddr(43), intaddr(44))
        assert not d.contains(intaddr(41))
        assert d.contains(intaddr(42))
        assert d.contains(intaddr(43))
        assert not d.contains(intaddr(44))
        assert d.get(intaddr(41)) == llmemory.NULL
        assert d.get(intaddr(42)) == llmemory.NULL
        assert d.get(intaddr(43)) == intaddr(44)
        assert d.get(intaddr(44)) == llmemory.NULL
        d.delete()
        assert lldict.alloc_count == 0

    def test_random(self):
        for i in range(8) + range(8, 80, 10):
            examples = {}
            lst = []
            for j in range(i):
                if j % 17 == 13:
                    intval = random.choice(lst)
                else:
                    intval = random.randrange(-sys.maxint, sys.maxint) or 1
                lst.append(intval)
                examples[intval] = True

            d = lldict.newdict()
            for intval in lst:
                d.setitem(intaddr(intval), intaddr(-intval))
            for intval in lst:
                assert d.contains(intaddr(intval))
                assert d.get(intaddr(intval), "???").intval == -intval
            for intval in lst:
                for j in range(intval-5, intval+5):
                    if j not in examples:
                        assert not d.contains(intaddr(j))
            assert not d.contains(llmemory.NULL)
            d.delete()
            assert lldict.alloc_count == 0


class intaddr(object):
    _TYPE = llmemory.Address
    def __init__(self, intval):
        self.intval = intval
    def _cast_to_int(self):
        return self.intval
    def __repr__(self):
        return '<intaddr 0x%x>' % (self.intval & (sys.maxint*2+1),)
    def __eq__(self, other):
        return isinstance(other, intaddr) and self.intval == other.intval
    def __ne__(self, other):
        return not self.__eq__(other)
