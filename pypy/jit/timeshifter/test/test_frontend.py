from pypy.rlib.objectmodel import we_are_jitted, _is_early_constant
from pypy.rpython.test.test_llinterp import interpret
from pypy.jit.timeshifter.test.test_timeshift import TimeshiftingTests

class TestFrontend(TimeshiftingTests):

    def test_we_are_jitted(self):
        def f():
            if we_are_jitted():
                return 42
            return 0

        assert f() == 0
        res = interpret(f, [])
        assert res == 0

        res = self.timeshift(f, [])
        assert res == 42

