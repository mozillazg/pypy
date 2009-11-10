import autopath
import py
from pypy.translator.oosupport.test_template.runtest import BaseTestRunTest
from pypy.translator.avm2.test.runtest import AVM2Test

class TestRunTest(BaseTestRunTest, AVM2Test):
    
    def test_big_arglist(self):
        def fn(a0, a1, a2, a3, a4, a5, a6, a7, a8, a9):
            return a0
        res = self.interpret(fn, [42]*10)
        assert res == 42
