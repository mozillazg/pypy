import py

from pypy.objspace.std.test import test_stringobject, test_unicodeobject
from pypy.conftest import gettestobjspace

class AppTestRopeObject(test_stringobject.AppTestStringObject):

    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withrope": True})

    def test_mul_overflow(self):
        import sys
        raises(OverflowError, '"abcdefg" * (sys.maxint // 2)')

    def test_split_bug(self):
        s = '/home/arigo/svn/pypy/branch/rope-branch/pypy/bin'
        s += '/pypy'
        lst = s.split('/')
        assert lst == ['', 'home', 'arigo', 'svn', 'pypy',
                       'branch', 'rope-branch', 'pypy', 'bin', 'pypy']

    def test_ord(self):
        s = ''
        s += '0'
        assert ord(s) == 48
        raises(TypeError, ord, '')
        s += '3'
        raises(TypeError, ord, s)

    def test_hash_twice(self):
        # check that we have the same hash as CPython for at least 31 bits
        # (but don't go checking CPython's special case -1)
        # check twice to catch hash cache problems`
        s1 = 'hello'
        s2 = 'hello world!'
        assert hash(s1) & 0x7fffffff == 0x347697fd
        assert hash(s1) & 0x7fffffff == 0x347697fd
        assert hash(s2) & 0x7fffffff == 0x2f0bb411
        assert hash(s2) & 0x7fffffff == 0x2f0bb411


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
