
import py
from pypy.rlib.jit import JitDriver
from pypy.jit.metainterp.test.test_basic import LLJitMixin, OOJitMixin

class ListTests:
    def test_basic(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'l'])
        def f(n):
            l = [0]
            while n > 0:
                myjitdriver.can_enter_jit(n=n, l=l)
                myjitdriver.jit_merge_point(n=n, l=l)
                x = l[0]
                l[0] = x + 1
                n -= 1
            return l[0]

        res = self.meta_interp(f, [10])
        assert res == f(10)        
        self.check_loops(getitem=0, setitem=1, guard_exception=0,
                         guard_no_exception=0)

    def test_list_escapes(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'l'])
        def f(n):
            l = [0] * (n + 1)
            while n > 0:
                myjitdriver.can_enter_jit(n=n, l=l)
                myjitdriver.jit_merge_point(n=n, l=l)
                x = l[0]
                l[0] = x + 1
                l[n] = n
                n -= 1
            return l[3]

        res = self.meta_interp(f, [10])
        assert res == f(10)
        self.check_loops(setitem=2)

class TestLLtype(ListTests, LLJitMixin):
    pass
