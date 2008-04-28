from pypy.jit.timeshifter.greenkey import GreenKey, KeyDesc, newgreendict
from pypy.jit.timeshifter.greenkey import greenkey_hash, greenkey_eq, empty_key
from pypy.jit.codegen.llgraph.rgenop import RGenOp
from pypy.rpython.lltypesystem import lltype

rgenop = RGenOp()

class TestGreenKeys(object):
    def newkey(self, *values):
        desc = KeyDesc(RGenOp, *[lltype.typeOf(val) for val in values])
        return GreenKey([rgenop.genconst(val) for val in values], desc)

    def test_simple(self):
        d = newgreendict()
        d[self.newkey(1, 2)] = 1
        assert d[self.newkey(1, 2)] == 1

    def test_check_types(self):
        d = newgreendict()
        d[self.newkey(1, 2)] = 1
        assert self.newkey(True, 2) not in d

    def test_check_lengths(self):
        d = newgreendict()
        d[self.newkey(1, 2)] = 1
        assert self.newkey(1, 2, 0) not in d

    def test_empty_key(self):
        d = newgreendict()
        assert empty_key not in d
        d[empty_key] = 1
        assert d[empty_key] == 1
        assert self.newkey(1, 2, 0) not in d
