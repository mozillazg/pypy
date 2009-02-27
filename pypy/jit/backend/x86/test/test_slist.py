
from pypy.jit.metainterp.test.test_slist import ListTests
from pypy.jit.backend.x86.test.test_basic import Jit386Mixin

class TestSList(Jit386Mixin, ListTests):
    pass
