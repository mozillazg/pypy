import py
from pypy.translator.cli.test.runtest import CliTest
from pypy.rpython.test.test_rstr import BaseTestRstr

class TestCliString(CliTest, BaseTestRstr):

    EMPTY_STRING_HASH = 0

    def test_char_isxxx(self):
        def fn(s):
            return (s.isspace()      |
                    s.isdigit() << 1 |
                    s.isalpha() << 2 |
                    s.isalnum() << 3 |
                    s.isupper() << 4 |
                    s.islower() << 5)
        # need to start from 1, because we cannot pass '\x00' as a command line parameter        
        for i in range(1, 128):
            ch = chr(i)
            res = self.interpret(fn, [ch])
            assert res == fn(ch)

    def test_unichar_const(self):
        py.test.skip("CLI interpret doesn't support unicode for input arguments")
    test_unichar_eq = test_unichar_const
    test_unichar_ord = test_unichar_const
    test_unichar_hash = test_unichar_const

    def test_upper(self):
        py.test.skip("CLI doens't support backquotes inside string literals")
    test_lower = test_upper

    def test_replace_TyperError(self):
        pass # it doesn't make sense here

    def test_hlstr(self):
        py.test.skip("CLI tests can't have string as input arguments")

    def test_hash_value(self):
        # make that hash are computed by value and not by reference
        def fn(x, y):
            s1 = ''.join([x, 'e', 'l', 'l', 'o'])
            s2 = ''.join([y, 'e', 'l', 'l', 'o'])
            return (hash(s1) == hash(s2)) and (s1 is not s2)
        assert self.interpret(fn, ['h', 'h']) == True

    def test_int_formatting(self):
        def fn(answer):
            return 'the answer is %s' % answer
        assert self.ll_to_string(self.interpret(fn, [42])) == 'the answer is 42'

    def test_getitem_exc(self):
        py.test.skip('fixme!')

