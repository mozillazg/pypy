
from pypy.rpython.test.tool import BaseRtypingTest, LLRtypeMixin
from pypy.rlib.r_iter import list_iter

class AbstractRIterTest(BaseRtypingTest):
    def test_basic(self):
        def f():
            l = [1, 2, 3, 4, 5]
            a = []
            for i in list_iter(l):
                a.append(i)
            return len(a)

        assert f() == 5
        res = self.interpret(f, [])
        assert res == 5

class TestRType(AbstractRIterTest, LLRtypeMixin):
    pass
