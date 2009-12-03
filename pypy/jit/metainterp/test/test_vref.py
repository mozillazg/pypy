from pypy.rlib.jit import JitDriver, dont_look_inside, virtual_ref
from pypy.jit.metainterp.test.test_basic import LLJitMixin, OOJitMixin


class VRefTests:

    def test_simple_no_access(self):
        myjitdriver = JitDriver(greens = [], reds = ['n'])
        #
        class XY:
            pass
        class ExCtx:
            pass
        exctx = ExCtx()
        #
        @dont_look_inside
        def externalfn():
            return 1
        #
        def f(n):
            while n > 0:
                myjitdriver.can_enter_jit(n=n)
                myjitdriver.jit_merge_point(n=n)
                xy = XY()
                exctx.topframeref = virtual_ref(xy)
                n -= externalfn()
                exctx.topframeref = None
        #
        self.meta_interp(f, [15])
        self.check_loops(new_with_vtable=0)


class TestLLtype(VRefTests, LLJitMixin):
    pass
