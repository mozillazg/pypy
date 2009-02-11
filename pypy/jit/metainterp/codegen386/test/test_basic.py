import py
from codegen386.runner import CPU386
from pyjitpl import ll_meta_interp
from test import test_basic
from pypy.jit.hintannotator.policy import StopAtXPolicy


class Jit386Mixin(test_basic.JitMixin):
    type_system = 'lltype'

    def check_jumps(self, maxcount):
        pass

    @staticmethod
    def meta_interp(fn, args, **kwds):
        return ll_meta_interp(fn, args, CPUClass=CPU386, **kwds)


class TestBasic(Jit386Mixin, test_basic.BasicTests):
    # for the individual tests see
    # ====> ../../test/test_basic.py
    def test_bug(self):
        class X(object):
            pass
        def f(n):
            while n > -100:
                x = X()
                x.arg = 5
                if n <= 0: break
                n -= x.arg
                x.arg = 6   # prevents 'x.arg' from being annotated as constant
            return n
        res = self.meta_interp(f, [31], specialize=False)
        assert res == -4
