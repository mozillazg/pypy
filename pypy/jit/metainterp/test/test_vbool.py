from test.test_basic import LLJitMixin, OOJitMixin


class BoolTests:

    def test_int_is_true(self):
        lst = [17] + [0] * 21

        def f(n):
            while n > 0:
                n -= 3
                if lst[n]:
                    return 123456
            return n
        res = self.meta_interp(f, [20])
        assert res == -1
        self.check_loops(int_is_true=0)

        lst = [17] * 20 + [0]
        def f(n):
            i = 0
            while n > 0:
                n -= 3
                if not lst[n]:
                    return 123456
            return n
        res = self.meta_interp(f, [19])
        assert res == -2
        self.check_loops(int_is_true=0)

    def test_oononzero(self):
        class A:
            pass
        lst = [A()] + [None] * 21

        def f(n):
            while n > 0:
                n -= 3
                if lst[n]:
                    return 123456
            return n
        res = self.meta_interp(f, [20])
        assert res == -1
        self.check_loops(oononzero=0, ooiszero=0)

        lst = [A()] * 20 + [None]
        def f(n):
            i = 0
            while n > 0:
                n -= 3
                if not lst[n]:
                    return 123456
            return n
        res = self.meta_interp(f, [19])
        assert res == -2
        self.check_loops(oononzero=0, ooiszero=0)

    def test_oononzero_resume(self):
        class A:
            def __init__(self, x):
                self.x = x
        lst = [A(i) for i in [0, 0, 0, 1, 1, 1]] + [None]

        def f():
            n = 0
            a = lst[0]
            while a:
                if a.x:
                    pass
                n += 1
                a = lst[n]
            return n
        res = self.meta_interp(f, [])
        assert res == 6
        self.check_loops(oononzero=0, ooiszero=0)


class TestOOtype(BoolTests, OOJitMixin):
    pass

class TestLLtype(BoolTests, LLJitMixin):
    pass
