"""Tests for multiple JitDrivers."""
from pypy.rlib.jit import JitDriver
from pypy.jit.metainterp.test.test_basic import LLJitMixin, OOJitMixin


class MultipleJitDriversTests:

    def test_simple(self):
        myjitdriver1 = JitDriver(greens=[], reds=['n', 'm'])
        myjitdriver2 = JitDriver(greens=['g'], reds=['r'])
        #
        def loop1(n, m):
            while n > 0:
                myjitdriver1.can_enter_jit(n=n, m=m)
                myjitdriver1.jit_merge_point(n=n, m=m)
                n -= m
            return n
        #
        def loop2(g, r):
            while r > 0:
                myjitdriver2.can_enter_jit(g=g, r=r)
                myjitdriver2.jit_merge_point(g=g, r=r)
                r += loop1(r, g) - 1
            return r
        #
        res = self.meta_interp(loop2, [4, 40], repeat=7)
        assert res == loop2(4, 40)


class TestLLtype(MultipleJitDriversTests, LLJitMixin):
    pass

class TestOOtype(MultipleJitDriversTests, OOJitMixin):
    pass
