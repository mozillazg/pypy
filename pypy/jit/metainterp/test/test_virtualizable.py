import py
from pypy.rpython.lltypesystem import lltype, lloperation, rclass, llmemory
from pypy.rpython.annlowlevel import llhelper
from pypy.jit.metainterp.policy import StopAtXPolicy
from pypy.rlib.jit import JitDriver
from pypy.jit.metainterp.test.test_basic import LLJitMixin, OOJitMixin
from pypy.rpython.lltypesystem.rvirtualizable2 import VABLERTIPTR

promote_virtualizable = lloperation.llop.promote_virtualizable
debug_print = lloperation.llop.debug_print

# ____________________________________________________________

class ExplicitVirtualizableTests:

    def test_preexisting_access(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'xy'],
                                virtualizables = ['xy'])
        def setup():
            xy = lltype.malloc(XY)
            xy.vable_rti = lltype.nullptr(VABLERTIPTR.TO)
            return xy
        def f(n):
            xy = setup()
            xy.x = 10
            while n > 0:
                myjitdriver.can_enter_jit(xy=xy, n=n)
                myjitdriver.jit_merge_point(xy=xy, n=n)
                promote_virtualizable(lltype.Void, xy, 'x')
                x = xy.x
                xy.x = x + 1
                n -= 1
        self.meta_interp(f, [5])
        self.check_loops(getfield_gc__4=0, setfield_gc__4=0)

    def test_preexisting_access_2(self):
        def setup():
            xy = lltype.malloc(XY)
            xy.vable_rti = lltype.nullptr(VABLERTIPTR.TO)
            return xy
        def f(n):
            xy = setup()
            xy.x = 100
            while n > 0:
                promote_virtualizable(lltype.Void, xy, 'x')
                x = xy.x
                xy.x = x + 1
                n -= 1
            while n > -8:
                promote_virtualizable(lltype.Void, xy, 'x')
                x = xy.x
                xy.x = x + 10
                n -= 1
            return xy.x
        res = self.meta_interp(f, [5])
        assert res == 185
        self.check_loops(getfield__4=0, setfield__4=0)

    def test_two_paths_access(self):
        def setup():
            xy = lltype.malloc(XY)
            xy.vable_rti = lltype.nullptr(VABLERTIPTR.TO)
            return xy
        def f(n):
            xy = setup()
            xy.x = 100
            while n > 0:
                promote_virtualizable(lltype.Void, xy, 'x')
                x = xy.x
                if n <= 10:
                    x += 1000
                xy.x = x + 1
                n -= 1
            return xy.x
        res = self.meta_interp(f, [18])
        assert res == 10118
        self.check_loops(getfield__4=0, setfield__4=0)


class ImplicitVirtualizableTests:

    def test_simple_implicit(self):
        class Frame(object):
            _virtualizable2_ = True
            def __init__(self, x, y):
                self.x = x
                self.y = y

        class SomewhereElse:
            pass
        somewhere_else = SomewhereElse()

        def f(n):
            frame = Frame(n, 0)
            somewhere_else.top_frame = frame        # escapes
            while frame.x > 0:
                frame.y += frame.x
                frame.x -= 1
            return somewhere_else.top_frame.y

        res = self.meta_interp(f, [10], exceptions=False)
        assert res == 55
        self.check_loops(getfield__4=0, setfield__4=0)

    def test_external_read(self):
        py.test.skip("Fails")
        class Frame(object):
            _virtualizable2_ = True
        class SomewhereElse:
            pass
        somewhere_else = SomewhereElse()

        def g():
            result = somewhere_else.top_frame.y     # external read
            debug_print(lltype.Void, '-+-+-+-+- external read:', result)
            return result

        def f(n):
            frame = Frame()
            frame.x = n
            frame.y = 10
            somewhere_else.top_frame = frame
            while frame.x > 0:
                frame.x -= g()
                frame.y += 1
            return frame.x

        res = self.meta_interp(f, [123], exceptions=False,
                               policy=StopAtXPolicy(g))
        assert res == f(123)
        self.check_loops(getfield_int=0, setfield_int=0)

    def test_external_write(self):
        py.test.skip("Fails")
        class Frame(object):
            _virtualizable2_ = True
        class SomewhereElse:
            pass
        somewhere_else = SomewhereElse()

        def g():
            result = somewhere_else.top_frame.y + 1
            debug_print(lltype.Void, '-+-+-+-+- external write:', result)
            somewhere_else.top_frame.y = result      # external read/write

        def f(n):
            frame = Frame()
            frame.x = n
            frame.y = 10
            somewhere_else.top_frame = frame
            while frame.x > 0:
                g()
                frame.x -= frame.y
            return frame.y

        res = self.meta_interp(f, [240], exceptions=False,
                               policy=StopAtXPolicy(g))
        assert res == f(240)
        self.check_loops(getfield_int=0, setfield_int=0)

    def test_list_implicit(self):
        class Frame(object):
            _virtualizable2_ = True

        def f(n):
            frame = Frame()
            while n > 0:
                frame.lst = []
                frame.lst.append(n - 10)
                n = frame.lst[-1]
            return n + len(frame.lst)

        res = self.meta_interp(f, [53], exceptions=False)
        assert res == -6
        self.check_loops(getfield_ptr=0, setfield_ptr=0, call__4=0)

    def test_single_list_implicit(self):
        py.test.skip("in-progress")
        class Frame(object):
            _virtualizable2_ = True

        def f(n):
            frame = Frame()
            frame.lst = [100, n]
            while n > 0:
                n = frame.lst.pop()
                frame.lst.append(n - 10)
            return frame.lst.pop()

        res = self.meta_interp(f, [53], exceptions=False)
        assert res == -17
        self.check_loops(getfield_ptr=0, setfield_ptr=0, call__4=0)


##class TestOOtype(ExplicitVirtualizableTests,
##                 ImplicitVirtualizableTests,
##                 OOJitMixin):
##    pass

class TestLLtype(ExplicitVirtualizableTests,
                 ImplicitVirtualizableTests,
                 LLJitMixin):
    pass
