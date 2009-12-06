import py
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rlib.jit import JitDriver, dont_look_inside
from pypy.rlib.jit import virtual_ref, virtual_ref_finish
from pypy.rlib.objectmodel import compute_unique_id
from pypy.jit.metainterp.test.test_basic import LLJitMixin, OOJitMixin
from pypy.jit.metainterp.resoperation import rop
from pypy.jit.metainterp.virtualref import JIT_VIRTUAL_REF


class VRefTests:

    def test_make_vref_simple(self):
        class X:
            pass
        class ExCtx:
            pass
        exctx = ExCtx()
        #
        def f():
            exctx.topframeref = vref = virtual_ref(X())
            exctx.topframeref = None
            virtual_ref_finish(vref)
            return 1
        #
        self.interp_operations(f, [])
        self.check_operations_history(virtual_ref=1)

    def test_make_vref_guard(self):
        if not isinstance(self, TestLLtype):
            py.test.skip("purely frontend test")
        #
        class X:
            def __init__(self, n):
                self.n = n
        class ExCtx:
            pass
        exctx = ExCtx()
        #
        @dont_look_inside
        def external(n):
            if n > 100:
                return exctx.topframeref().n
            return n
        def enter(n):
            exctx.topframeref = virtual_ref(X(n + 10))
        def leave():
            virtual_ref_finish(exctx.topframeref)
            exctx.topframeref = None
        def f(n):
            enter(n)
            n = external(n)
            # ^^^ the point is that X() should be kept alive here
            leave()
            return n
        #
        res = self.interp_operations(f, [5])
        assert res == 5
        self.check_operations_history(virtual_ref=1, guard_not_forced=1)
        #
        [guard_op] = [op for op in self.metainterp.history.operations
                         if op.opnum == rop.GUARD_NOT_FORCED]
        bxs1 = [box for box in guard_op.fail_args
                  if str(box._getrepr_()).endswith('.X')]
        assert len(bxs1) == 1
        bxs2 = [box for box in guard_op.fail_args
                  if str(box._getrepr_()).endswith('JitVirtualRef')]
        assert len(bxs2) == 1
        #
        self.metainterp.rebuild_state_after_failure(guard_op.descr,
                                                    guard_op.fail_args[:])
        assert len(self.metainterp.framestack) == 1
        assert len(self.metainterp.virtualref_boxes) == 2
        assert self.metainterp.virtualref_boxes[0].value == bxs1[0].value
        assert self.metainterp.virtualref_boxes[1].value == bxs2[0].value

    def test_make_vref_and_force(self):
        jitdriver = JitDriver(greens = [], reds = ['total', 'n'])
        #
        class X:
            pass
        class ExCtx:
            pass
        exctx = ExCtx()
        #
        @dont_look_inside
        def force_me():
            return exctx.topframeref().n
        #
        def f(n):
            total = 0
            while total < 300:
                jitdriver.can_enter_jit(total=total, n=n)
                jitdriver.jit_merge_point(total=total, n=n)
                x = X()
                x.n = n + 123
                exctx.topframeref = virtual_ref(x)
                total += force_me() - 100
                virtual_ref_finish(exctx.topframeref)
                exctx.topframeref = None
            return total
        #
        res = self.meta_interp(f, [-4])
        assert res == 16 * 19
        self.check_loops({})      # because we aborted tracing

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
        def externalfn(n):
            if n > 1000:
                return compute_unique_id(exctx.topframeref())
            return 1
        #
        def f(n):
            while n > 0:
                myjitdriver.can_enter_jit(n=n)
                myjitdriver.jit_merge_point(n=n)
                xy = XY()
                xy.next1 = XY()
                xy.next2 = XY()
                exctx.topframeref = virtual_ref(xy)
                n -= externalfn(n)
                virtual_ref_finish(exctx.topframeref)
                exctx.topframeref = None
        #
        self.meta_interp(f, [15])
        self.check_loops(new_with_vtable=1)     # the vref, not the XYs

    def test_simple_force_always(self):
        myjitdriver = JitDriver(greens = [], reds = ['n'])
        #
        class XY:
            pass
        class ExCtx:
            pass
        exctx = ExCtx()
        #
        @dont_look_inside
        def externalfn(n):
            m = exctx.topframeref().n
            assert m == n
            return 1
        #
        def f(n):
            while n > 0:
                myjitdriver.can_enter_jit(n=n)
                myjitdriver.jit_merge_point(n=n)
                xy = XY()
                xy.n = n
                exctx.topframeref = virtual_ref(xy)
                n -= externalfn(n)
                virtual_ref_finish(exctx.topframeref)
                exctx.topframeref = None
        #
        self.meta_interp(f, [15])
        self.check_loops({})     # because we aborted tracing

    def test_simple_force_sometimes(self):
        myjitdriver = JitDriver(greens = [], reds = ['n'])
        #
        class XY:
            pass
        class ExCtx:
            pass
        exctx = ExCtx()
        #
        @dont_look_inside
        def externalfn(n):
            if n == 13:
                exctx.m = exctx.topframeref().n
            return 1
        #
        def f(n):
            while n > 0:
                myjitdriver.can_enter_jit(n=n)
                myjitdriver.jit_merge_point(n=n)
                xy = XY()
                xy.n = n
                exctx.topframeref = virtual_ref(xy)
                n -= externalfn(n)
                virtual_ref_finish(exctx.topframeref)
                exctx.topframeref = None
            return exctx.m
        #
        res = self.meta_interp(f, [30])
        assert res == 13


class TestLLtype(VRefTests, LLJitMixin):
    pass
