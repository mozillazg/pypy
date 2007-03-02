import py

from pypy.objspace.std.test import test_stringobject, test_unicodeobject
from pypy.conftest import gettestobjspace

class AppTestRopeObject(test_stringobject.AppTestStringObject):

    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withrope": True})

    def test_mul_overflow(self):
        import sys
        raises(OverflowError, '"abcdefg" * (sys.maxint // 2)')

class AppTestRopeUnicode(object):

    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withrope": True})

    def test_startswith(self):
        assert "abc".startswith("a", 0, 2147483647)

class AppTestUnicodeRopeStdOnly(test_unicodeobject.AppTestUnicodeStringStdOnly):

    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withrope": True})

class AppTestUnicodeRope(test_unicodeobject.AppTestUnicodeString):

    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withrope": True})
