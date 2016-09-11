
from rpython.jit.metainterp.test.support import LLJitMixin
from rpython.rlib import jit

class CallTest(object):
    def test_indirect_call(self):
        @jit.dont_look_inside
        def f1(x):
            return x + 1

        @jit.dont_look_inside
        def f2(x):
            return x + 2

        @jit.dont_look_inside
        def choice(i):
            if i:
                return f1
            return f2

        def f(i):
            func = choice(i)
            return func(i)

        res = self.interp_operations(f, [3])
        assert res == f(3)

    def test_cond_call(self):
        def f(l, n):
            l.append(n)

        def main(n):
            l = []
            jit.conditional_call(n == 10, f, l, n)
            return len(l)

        assert self.interp_operations(main, [10]) == 1
        assert self.interp_operations(main, [5]) == 0

    def test_cond_call_disappears(self):
        driver = jit.JitDriver(greens = [], reds = ['n'])

        def f(n):
            raise ValueError

        def main(n):
            while n > 0:
                driver.jit_merge_point(n=n)
                jit.conditional_call(False, f, 10)
                n -= 1
            return 42

        assert self.meta_interp(main, [10]) == 42
        self.check_resops(guard_no_exception=0)

    def test_cond_call_i(self):
        @jit.elidable
        def f(n):
            return n * 200

        def main(n):
            return jit.conditional_call_elidable(n, 10, f, n)

        assert self.interp_operations(main, [10]) == 2000
        assert self.interp_operations(main, [15]) == 15

    def test_cond_call_r(self):
        @jit.elidable
        def f(n):
            return [n]

        def main(n):
            if n == 10:
                l = []
            else:
                l = None
            l = jit.conditional_call_elidable(l, None, f, n)
            return len(l)

        assert self.interp_operations(main, [10]) == 0
        assert self.interp_operations(main, [5]) == 1

    def test_cond_call_constant_in_pyjitpl(self):
        @jit.elidable
        def f(a, b):
            return a + b
        def main(n):
            # this is completely constant-folded because the arguments
            # to f() are constants.
            return jit.conditional_call_elidable(n, 23, f, 40, 2)

        assert main(12) == 12                            # because 12 != 23
        assert self.interp_operations(main, [12]) == 12  # because 12 != 23
        self.check_operations_history(finish=1)   # empty history
        assert self.interp_operations(main, [23]) == 42  # because 23 == 23
        self.check_operations_history(finish=1)   # empty history


class TestCall(LLJitMixin, CallTest):
    pass
