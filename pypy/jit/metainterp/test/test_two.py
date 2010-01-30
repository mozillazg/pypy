import py
from pypy.rlib.jit import JitDriver
from pypy.jit.metainterp.test.test_basic import LLJitMixin


myjitdriver1 = JitDriver(greens = [], reds = ['n'])
def f1(n):
    while n > 0:
        myjitdriver1.can_enter_jit(n=n)
        myjitdriver1.jit_merge_point(n=n)
        n -= 10
    return n

myjitdriver2 = JitDriver(greens = [], reds = ['m', 'x'])
def f2(m, x):
    while m > 0:
        myjitdriver2.can_enter_jit(m=m, x=x)
        myjitdriver2.jit_merge_point(m=m, x=x)
        m -= 1
        x += 3
    return x

myjitdriver3 = JitDriver(greens = [], reds = ['a', 'b', 'c'])
def f3(a, b, c):
    while a > 0:
        myjitdriver3.can_enter_jit(a=a, b=b, c=c)
        myjitdriver3.jit_merge_point(a=a, b=b, c=c)
        a -= f2(b, c)
    return a


class TwoJitsTests:

    def test_simple(self):
        def main(n, m, x):
            return f1(n) * f2(m, x)
        res = self.meta_interp(main, [78, 7, 0], num_jit_drivers=2)
        assert res == -2 * 21

    def test_call(self):
        res = self.meta_interp(f3, [100, 7, 0], num_jit_drivers=2)
        assert res == 100 - 5 * 21


class TestLLtype(TwoJitsTests, LLJitMixin):
    pass
