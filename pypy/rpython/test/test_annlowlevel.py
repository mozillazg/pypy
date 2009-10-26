
""" Few tests for annlowlevel helpers
"""

import os
from pypy.tool.udir import udir
from pypy.rpython.test.tool import BaseRtypingTest, LLRtypeMixin, OORtypeMixin
from pypy.rpython.lltypesystem.rstr import mallocstr, mallocunicode
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.annlowlevel import hlstr, llstr, oostr
from pypy.rpython.annlowlevel import hlunicode, llunicode


class AnnLowLevelTests(BaseRtypingTest):

    def test_register_atexit(self):
        from pypy.annotation import model as annmodel
        from pypy.rpython.extregistry import ExtRegistryEntry
        def callback():
            pass
        class CallbackEntry(ExtRegistryEntry):
            _about_ = callback
            def compute_result_annotation(self):
                return annmodel.s_None
            def specialize_call(self, hop):
                annhelper = hop.rtyper.getannmixlevel()
                annhelper.register_atexit(atexit)
                return hop.inputconst(lltype.Void, None)
        def f(n):
            callback()
            return n * 5
        def atexit():
            fd = os.open(tmpfn, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0666)
            os.close(fd)
        tmpfn = str(udir.join('%s.test_register_atexit' %
                              self.__class__.__name__))
        res = self.interpret(f, [5])
        assert res == 25
        assert os.path.exists(tmpfn)


class TestLLType(AnnLowLevelTests, LLRtypeMixin):
    def test_hlstr(self):
        s = mallocstr(3)
        s.chars[0] = "a"
        s.chars[1] = "b"
        s.chars[2] = "c"
        assert hlstr(s) == "abc"

    def test_llstr(self):
        s = llstr("abc")
        assert len(s.chars) == 3
        assert s.chars[0] == "a"
        assert s.chars[1] == "b"
        assert s.chars[2] == "c"

    def test_llstr_compile(self):
        def f(arg):
            s = llstr(hlstr(arg))
            return len(s.chars)

        res = self.interpret(f, [self.string_to_ll("abc")])
        assert res == 3
    
    def test_hlunicode(self):
        s = mallocunicode(3)
        s.chars[0] = u"a"
        s.chars[1] = u"b"
        s.chars[2] = u"c"
        assert hlunicode(s) == u"abc"

    def test_llunicode(self):
        s = llunicode(u"abc")
        assert len(s.chars) == 3
        assert s.chars[0] == u"a"
        assert s.chars[1] == u"b"
        assert s.chars[2] == u"c"

    def test_llunicode_compile(self):
        def f(arg):
            s = llunicode(hlunicode(arg))
            return len(s.chars)

        res = self.interpret(f, [self.unicode_to_ll(u"abc")])
        assert res == 3


class TestOOType(AnnLowLevelTests, OORtypeMixin):
    def test_hlstr(self):
        s = ootype.make_string("abc")
        assert hlstr(s) == "abc"

    def test_oostr(self):
        s = oostr("abc")
        assert ootype.typeOf(s) == ootype.String
        assert s._str == "abc"

    def test_oostr_compile(self):
        def f(arg):
            s = oostr(hlstr(arg))
            return s.ll_strlen()

        res = self.interpret(f, [self.string_to_ll("abc")])
        assert res == 3
