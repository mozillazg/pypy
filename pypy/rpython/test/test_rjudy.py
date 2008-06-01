
from pypy.rpython.test.tool import BaseRtypingTest, LLRtypeMixin, OORtypeMixin

from pypy.rlib.rjudy import JudyTree

class BaseTest(BaseRtypingTest):
    def test_creation(self):
        def f():
            x = JudyTree()
            res = len(x)
            x.free()
            return res
        assert self.interpret(f, []) == 0

class TestLLtype(BaseTest, LLRtypeMixin):
    pass

