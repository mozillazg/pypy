
from pypy.translator.avm2.test.runtest import AVM2Test
from pypy.rpython.test.test_rint import BaseTestRint

class TestAVM2Int(AVM2Test, BaseTestRint):
    def test_char_constant(self):
        def dummyfn(i):
            return chr(i)
        _ = self.interpret(dummyfn, [ord(' ')])
        assert _ == ' '
        _ = self.interpret(dummyfn, [ord('a')])
        assert _ == 'a'

    def test_rarithmetic(self):
        pass # it doesn't make sense here

    div_mod_iteration_count = 20

