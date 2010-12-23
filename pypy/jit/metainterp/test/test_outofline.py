
import py
from pypy.rlib.jit import JitDriver, dont_look_inside, hint
from pypy.jit.metainterp.test.test_basic import LLJitMixin

class OutOfLineTests(object):
    def test_getfield_jit_invariant(self):
        class A(object):
            _jit_invariant_fields_ = ['x']

        a1 = A()
        a1.x = 5
        a2 = A()
        a2.x = 8

        def f(x):
            if x:
                a = a1
            else:
                a = a2
            return a.x
        res = self.interp_operations(f, [-3])
        self.check_operations_history(getfield_gc = 0)

    def test_setfield_jit_invariant(self):
        class A(object):
            _jit_invariant_fields_ = ['x']

        myjitdriver = JitDriver(greens = [], reds = ['i', 'total'])
        
        a = A()

        @dont_look_inside
        def g(i):
            if i == 5:
                a.x = 2

        def f():
            a.x = 1
            i = 0
            total = 0
            while i < 20:
                myjitdriver.can_enter_jit(i=i, total=total)
                myjitdriver.jit_merge_point(i=i, total=total)
                g(i)
                i += a.x
                total += i
            return total

        assert self.meta_interp(f, []) == f()
        self.check_loop_count(2)
        self.check_history(getfield_gc=0, getfield_gc_pure=0)

    def test_jit_invariant_bridge(self):
        class A(object):
            _jit_invariant_fields_ = ['x']

        myjitdriver = JitDriver(greens = [], reds = ['i', 'total'])
        
        a = A()

        @dont_look_inside
        def g(i):
            if i == 5:
                a.x = 2

        def f():
            a.x = 1
            i = 0
            total = 0
            while i < 40:
                myjitdriver.can_enter_jit(i=i, total=total)
                myjitdriver.jit_merge_point(i=i, total=total)
                g(i)
                i += a.x
                if i > 18:
                    i += 1
                total += i
            return total

        assert self.meta_interp(f, []) == f()
        self.check_loop_count(3)
        self.check_history(getfield_gc=0, getfield_gc_pure=0)        

    def test_jit_invariant_entry_bridge(self):
        class A(object):
            _jit_invariant_fields_ = ['x']

        myjitdriver = JitDriver(greens = [], reds = ['i', 'total', 'a'])
        
        def f(a):
            i = 0
            total = 0
            while i < 30:
                myjitdriver.can_enter_jit(i=i, total=total, a=a)
                myjitdriver.jit_merge_point(i=i, total=total, a=a)
                a = hint(a, promote=True)
                total += a.x
                if i > 11:
                    i += 1
                i += 1
            return total

        def main():
            total = 0
            a = A()
            a.x = 1
            total += f(a)
            a.x = 2
            total += f(a)
            return total

        assert self.meta_interp(main, []) == main()
        self.check_loop_count(4)
        self.check_history(getfield_gc=0, getfield_gc_pure=0)

    def test_jit_invariant_invalidate_bridge(self):
        class A(object):
            _jit_invariant_fields_ = ['x']

        driver = JitDriver(greens = [], reds = ['i', 'total', 'a'])

        @dont_look_inside
        def g(a, i):
            if i == 25:
                a.x = 2

        def f():
            i = 0
            a = A()
            a.x = 1
            total = 0
            while i < 40:
                driver.can_enter_jit(i=i, total=total, a=a)
                driver.jit_merge_point(i=i, total=total, a=a)
                i += 1
                a = hint(a, promote=True)
                if i % 2:
                    total += a.x
                    g(a, i)
                total += 1
            return total

        assert self.meta_interp(f, []) == f()

    def test_jit_invariant_invalidate_call_asm(self):
        py.test.skip("Fails")
        myjitdriver1 = JitDriver(greens=[], reds=['n', 'a'])
        myjitdriver2 = JitDriver(greens=['g'], reds=['r', 'a'])

        #
        class A(object):
            _jit_invariant_fields_ = ['x']

            def __init__(self, x):
                self.x = x

        @dont_look_inside
        def possibly_invalidate(r, a):
            if r == 30:
                if a.x == 2:
                    a.x = 1
                else:
                    a.x = 2
            print r
        
        def loop1(n, a):
            while n > 0:
                myjitdriver1.can_enter_jit(n=n, a=a)
                myjitdriver1.jit_merge_point(n=n, a=a)
                a = hint(a, promote=True)
                n -= a.x
            return n
        #
        def loop2(g, r):
            a = A(1)
            while r > 0:
                myjitdriver2.can_enter_jit(g=g, r=r, a=a)
                myjitdriver2.jit_merge_point(g=g, r=r, a=a)
                a = hint(a, promote=True)
                r += loop1(r, a) + (-1)
                possibly_invalidate(r, a)
            return r
        #
        res = self.meta_interp(loop2, [4, 40], repeat=7, inline=True)
        assert res == loop2(4, 40)
        # we expect only one int_sub, corresponding to the single
        # compiled instance of loop1()
        self.check_loops(int_sub=1)

class TestLLtype(OutOfLineTests, LLJitMixin):
    pass
