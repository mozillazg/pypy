
import py
from codegen386.runner import CPU386
from pyjitpl import ll_meta_interp
from test.test_send import SendTests
from codegen386.test.test_basic import Jit386Mixin
from pypy.jit.hintannotator.policy import StopAtXPolicy

class TestSend(Jit386Mixin, SendTests):
    # for the individual tests see
    # ====> ../../test/test_send.py
    def test_call_with_additional_args(self):
        def externfn(a, b, c, d):
            return a + b*10 + c*100 + d*1000
        def f(a, b, c, d):
            return externfn(a, b, c, d)
        res = self.meta_interp(f, [1, 2, 3, 4], policy=StopAtXPolicy(externfn))
        assert res == 4321

    
