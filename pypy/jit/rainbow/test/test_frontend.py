import py
from pypy.rlib.jit import we_are_jitted, _is_early_constant, hint
from pypy.rpython.test.test_llinterp import interpret
from pypy.jit.rainbow.test.test_interpreter import InterpretationTest

class TestFrontend(InterpretationTest):
    type_system = "lltype"

    def test_we_are_jitted(self):
        def g(n):
            return n + 5
        def f(m):
            if we_are_jitted():
                return 42
            # the following path should not be seen by the hint-annotator
            # and killed from the red-green graphs by 'hannotator.simplify()'
            return g(m)

        assert f(5) == 10
        res = interpret(f, [5])
        assert res == 10

        res = self.interpret(f, [5])
        assert res == 42

    def test_is_early_constant(self):
        def f(x):
            if _is_early_constant(x):
                return 42
            return 0

        res = self.interpret(f, [5])
        assert res == 0
        res = self.interpret(f, [5], [0])
        assert res == 42

    def test_is_early_constant_for_green(self):
        def g(x):
            if _is_early_constant(x):
                return 42
            hint(x, concrete=True)
            return 0
        
        res = self.interpret(g, [5])
        assert res == 42        
