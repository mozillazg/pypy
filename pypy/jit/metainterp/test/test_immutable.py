from pypy.jit.metainterp.test.test_basic import LLJitMixin, OOJitMixin
from pypy.rlib.jit import JitDriver


class ImmutableFieldsTests:

    def test_fields(self):
        class X(object):
            _immutable_fields_ = ["x"]

            def __init__(self, x):
                self.x = x

        def f(x):
            y = X(x)
            return y.x + 5
        res = self.interp_operations(f, [23])
        assert res == 28
        self.check_operations_history(getfield_gc=0, getfield_gc_pure=1, int_add=1)

    def test_fields_subclass(self):
        class X(object):
            _immutable_fields_ = ["x"]

            def __init__(self, x):
                self.x = x

        class Y(X):
            _immutable_fields_ = ["y"]

            def __init__(self, x, y):
                X.__init__(self, x)
                self.y = y

        def f(x, y):
            X(x)     # force the field 'x' to be on class 'X'
            z = Y(x, y)
            return z.x + z.y + 5
        res = self.interp_operations(f, [23, 11])
        assert res == 39
        self.check_operations_history(getfield_gc=0, getfield_gc_pure=2,
                                      int_add=2)

        def f(x, y):
            # this time, the field 'x' only shows up on subclass 'Y'
            z = Y(x, y)
            return z.x + z.y + 5
        res = self.interp_operations(f, [23, 11])
        assert res == 39
        self.check_operations_history(getfield_gc=0, getfield_gc_pure=2,
                                      int_add=2)

    def test_array(self):
        class X(object):
            _immutable_fields_ = ["y[*]"]

            def __init__(self, x):
                self.y = x
        def f(index):
            l = [1, 2, 3, 4]
            l[2] = 30
            a = X(l)
            return a.y[index]
        res = self.interp_operations(f, [2], listops=True)
        assert res == 30
        self.check_operations_history(getfield_gc=0, getfield_gc_pure=1,
                            getarrayitem_gc=0, getarrayitem_gc_pure=1)


    def test_array_in_immutable(self):
        class X(object):
            _immutable_ = True
            _immutable_fields_ = ["lst[*]"]

            def __init__(self, lst, y):
                self.lst = lst
                self.y = y

        def f(x, index):
            y = X([x], x+1)
            return y.lst[index] + y.y + 5
        res = self.interp_operations(f, [23, 0], listops=True)
        assert res == 23 + 24 + 5
        self.check_operations_history(getfield_gc=0, getfield_gc_pure=2,
                            getarrayitem_gc=0, getarrayitem_gc_pure=1,
                            int_add=3)


    def test_green_field(self):
        myjitdriver = JitDriver(greens=['ctx.x'], reds=['ctx'])
        class Ctx(object):
            _immutable_fields_ = ['x']
            def __init__(self, x, y):
                self.x = x
                self.y = y
        def f(x, y):
            ctx = Ctx(x, y)
            while 1:
                myjitdriver.can_enter_jit(ctx=ctx)
                myjitdriver.jit_merge_point(ctx=ctx)
                ctx.y -= 1
                if ctx.y < 0:
                    return ctx.y
        def g(y):
            return f(5, y) + f(6, y)
        #
        res = self.meta_interp(g, [7])
        assert res == -2
        self.check_loop_count(2)


class TestLLtypeImmutableFieldsTests(ImmutableFieldsTests, LLJitMixin):
    pass

class TestOOtypeImmutableFieldsTests(ImmutableFieldsTests, OOJitMixin):
   pass
