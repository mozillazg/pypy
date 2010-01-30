import py
from pypy.rlib.jit import JitDriver
from pypy.jit.metainterp.test.test_basic import LLJitMixin


class TwoJitsTests:

    def test_simple(self):
        myjitdriver1 = JitDriver(greens = [], reds = ['n'])
        def f1(n):
            while n > 0:
                myjitdriver1.can_enter_jit(n=n)
                myjitdriver1.jit_merge_point(n=n)
                n -= 10
            return n
        #
        myjitdriver2 = JitDriver(greens = [], reds = ['m', 'x'])
        def f2(m, x):
            while m > 0:
                myjitdriver2.can_enter_jit(m=m, x=x)
                myjitdriver2.jit_merge_point(m=m, x=x)
                m -= 1
                x += 3
            return x
        #
        def main(n, m, x):
            return f1(n) * f2(m, x)
        #
        res = self.meta_interp(main, [78, 7, 0], num_jit_drivers=2)
        assert res == -2 * 21


class TestLLtype(TwoJitsTests, LLJitMixin):
    pass
