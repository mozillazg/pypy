import autopath
import py
from pypy.translator.avm.test.runtest import AVM1Test
from pypy.rpython.test.test_rint import BaseTestRint

class TestAVM1Int(AVM1Test, BaseTestRint):
    def test_char_constant(self):
        def dummyfn(i):
            return chr(i)
        self.interpret(dummyfn, [ord(' ')], ' ')
        self.interpret(dummyfn, [ord('a')], 'a')
        self.do_test()

    def test_rarithmetic(self):
        pass # it doesn't make sense here

    div_mod_iteration_count = 20


if __name__ == "__main__":
    TestAVM1Int().test_char_constant()
