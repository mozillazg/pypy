import py
from pyjitpl import ll_meta_interp, get_stats
from rpyjitpl import rpython_ll_meta_interp
from test import test_basic


class TestBasic:

    def test_dummy(self):
        def f(x):
            return x
        res = ll_meta_interp(f, [42])
        assert res == 42
        res = rpython_ll_meta_interp(f, [42], loops=0)
        assert res == 42

    def test_basic(self):
        def f(x, y):
            return x + y
        res = ll_meta_interp(f, [40, 2])
        assert res == 42
        res = rpython_ll_meta_interp(f, [40, 2], loops=0)
        assert res == 42

    def test_if(self):
        def f(x, y, z):
            if x:
                return y
            else:
                return z
        res = ll_meta_interp(f, [1, 40, 2])
        assert res == 40
        res = ll_meta_interp(f, [1, 40, 2])
        assert res == 40
        res = rpython_ll_meta_interp(f, [1, 40, 2], loops=0)
        assert res == 40
        res = rpython_ll_meta_interp(f, [0, 40, 2], loops=0)
        assert res == 2

    def test_loop_1(self):
        def f(i):
            total = 0
            while i > 3:
                total += i
                i -= 1
            return total * 10
        res = ll_meta_interp(f, [10])
        assert res == 490
        res = rpython_ll_meta_interp(f, [10], loops=1)
        assert res == 490

    def test_loop_2(self):
        def f(i):
            total = 0
            while i > 3:
                total += i
                if i >= 10:
                    i -= 2
                i -= 1
            return total * 10
        res = ll_meta_interp(f, [17])
        assert res == (17+14+11+8+7+6+5+4) * 10
        res = rpython_ll_meta_interp(f, [17], loops=2)
        assert res == (17+14+11+8+7+6+5+4) * 10

    def test_ptr_very_simple(self):
        class A:
            pass
        a = A()
        def f(i):
            a.i = i
            return a.i + 2
        res = ll_meta_interp(f, [17])
        assert res == 19
        res = rpython_ll_meta_interp(f, [17])
        assert res == 19

    def test_ptr_simple(self):
        class A:
            pass
        def f(i):
            a = A()
            a.i = i
            return a.i + 2
        res = ll_meta_interp(f, [17])
        assert res == 19
        res = rpython_ll_meta_interp(f, [17], loops=0)
        assert res == 19


class LLInterpJitMixin:
    type_system = 'lltype'
    meta_interp = staticmethod(rpython_ll_meta_interp)
    basic = False

    def check_history(self, expected=None, **check):
        pass
    def check_loops(self, expected=None, **check):
        pass
    def check_loop_count(self, count):
        pass
    def check_jumps(self, maxcount):
        pass

class TestLLBasic(test_basic.BasicTests, LLInterpJitMixin):
    pass
