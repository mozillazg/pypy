from pypy.jit.timeshifter.greenkey import GreenKey, KeyDesc
from pypy.jit.timeshifter.greenkey import greenkey_hash, greenkey_eq
from pypy.jit.codegen.llgraph.rgenop import RGenOp
from pypy.rlib.objectmodel import r_dict
from pypy.rpython.lltypesystem import lltype

rgenop = RGenOp()

class TestGreenKeys(object):
    def newdict(self):
        return r_dict(greenkey_eq, greenkey_hash)

    def newkey(self, *values):
        desc = KeyDesc(RGenOp, *[lltype.typeOf(val) for val in values])
        return GreenKey([rgenop.genconst(val) for val in values], desc, rgenop)

    def test_simple(self):
        d = self.newdict()
        d[self.newkey(1, 2)] = 1
        assert d[self.newkey(1, 2)] == 1

    def test_check_types(self):
        d = self.newdict()
        d[self.newkey(1, 2)] = 1
        assert self.newkey(True, 2) not in d

    def test_check_lengths(self):
        d = self.newdict()
        d[self.newkey(1, 2)] = 1
        assert self.newkey(1, 2, 0) not in d
