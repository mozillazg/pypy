import autopath
import py
from pypy.translator.avm.test.runtest import AVM1Test
from pypy.rpython.test.test_rint import BaseTestRint
from pypy.rlib.rarithmetic import r_longlong

class TestAVM1Int(AVM1Test, BaseTestRint):
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
    
    def test_div_mod(self):
        import random

        for inttype in (int, r_longlong):

            # def d(x, y):
            #     return x/y

            # for i in range(self.div_mod_iteration_count):
            #     x = inttype(random.randint(-100000, 100000))
            #     y = inttype(random.randint(-100000, 100000))
            #     if not y: continue
            #     res = self.interpret(d, [x, y])
            #     print "x:", x, "y:", y, "result in Flash:", res, "result in Python:", d(x, y)
            #     assert res == d(x, y)
                
            def m(x, y):
                return x%y
            
            for i in range(self.div_mod_iteration_count):
                x = inttype(random.randint(-100000, 100000))
                y = inttype(random.randint(-100000, 100000))
                if not y: continue
                res = self.interpret(m, [x, y])
                print "x:", x, "y:", y, "result in Flash:", res, "result in Python:", m(x, y)
                assert res == m(x, y)
    
    
if __name__=="__main__":
    TestAVM1Int().test_div_mod()
