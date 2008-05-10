
from pypy.rpython.test.tool import BaseRtypingTest, LLRtypeMixin, OORtypeMixin
from pypy.rlib.rstring import StringBuilder, UnicodeBuilder

class BaseTestStringBuilder(BaseRtypingTest):
    def test_simple(self):
        def func():
            s = StringBuilder()
            s.append("a")
            s.append("abc")
            return s.build()
        res = self.ll_to_string(self.interpret(func, []))
        assert res == "aabc"

    def test_overallocation(self):
        def func():
            s = StringBuilder(4)
            s.append("abcd")
            s.append("defg")
            s.append("rty")
            return s.build()
        res = self.ll_to_string(self.interpret(func, []))
        assert res == "abcddefgrty"

    def test_unicode(self):
        def func():
            s = UnicodeBuilder()
            s.append(u'a')
            s.append(u'abc')
            s.append(u'abcdef')
            return s.build()
        res = self.ll_to_unicode(self.interpret(func, []))
        assert res == 'aabcabcdef'
        assert isinstance(res, unicode)


class TestLLtype(BaseTestStringBuilder, LLRtypeMixin):
    pass

class TestOOtype(BaseTestStringBuilder, OORtypeMixin):
    pass
