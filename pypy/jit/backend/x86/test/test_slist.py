
from pypy.jit.metainterp.test.test_slist import ListTests
from pypy.jit.backend.x86.test.test_basic import Jit386Mixin

class TestSList(Jit386Mixin, ListTests):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_slist.py
    pass
