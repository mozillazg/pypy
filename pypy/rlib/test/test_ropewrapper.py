import py
from pypy.rlib.ropewrapper import RopeUnicode, RopeString

class AbstractTest(object):

    def test_construction(self):
        s = self.const("abc")
        assert len(s) == 3
        assert s[0] == self.const("a")
        assert s[1] == self.const("b")
        assert s[2] == self.const("c")

    def test_negative_index(self):
        s = self.const("abc") * 10000
        for i in range(len(s)):
            assert s[-i - 1] == s[len(s) - 1 - i]

    def test_add(self):
        s1 = self.const("abc")
        s2 = self.const("def")
        s = s1 + s2
        assert s[0] == self.const("a")
        assert s[1] == self.const("b")
        assert s[2] == self.const("c")
        assert s[3] == self.const("d")
        assert s[4] == self.const("e")
        assert s[5] == self.const("f")

    def test_mul(self):
        t = self.const("abc")
        l = [t * 5, 5 * t]
        for s in l:
            for i in range(5):
                assert s[i * 3 + 0] == self.const("a")
                assert s[i * 3 + 1] == self.const("b")
                assert s[i * 3 + 2] == self.const("c")

    def test_slice(self):
        s = self.const("abcd") * 100 + self.const("efghi") * 100
        assert s[1::1] == self.const("bcd" + "abcd" * 99 + "efghi" * 100)
        assert s[1:-1:1] == self.const("bcd" + "abcd" * 99 +
                                       "efghi" * 99 + "efgh")

    def test_compare(self):
        s1 = self.const("abc")
        s2 = self.const("abc")
        assert s1 == s2
        assert not s1 != s2

    def test_iteration(self):
        s = self.const("abcdefghijkl")
        i = 0
        for c in s:
            assert c == s[i]
            i += 1
        assert i == len(s)

    def test_hash(self):
        s1 = self.const("abc")
        s2 = self.const("abc")
        assert hash(s1) == hash(s2)
    
    def test_str(self):
        s1 = self.const("abc")
        assert str(s1) == "abc"


class AbstractRopeTest(object):
    def test_add_long(self):
        s1 = self.const("a")
        s2 = self.const("b") * (2 ** 30)
        s3 = s1 + s2
        assert len(s3) == 2 ** 30 + 1
        assert s3[0] == "a"
        assert s3[1] == "b"
        assert s3[5] == "b"
        assert s3[-1] == "b"

class TestString(AbstractTest, AbstractRopeTest):
    const = RopeString

class TestPythonString(AbstractTest):
    const = str

class TestUnicode(AbstractTest, AbstractRopeTest):
    const = RopeUnicode

class TestPythonUnicode(AbstractTest):
    const = unicode

class AbstractTestCoercion(object):
    def test_encode(self):
        u = self.constunicode(u"\uffff")
        s = u.encode("utf-8")
        assert s == self.conststr("\xef\xbf\xbf")
        s = u.encode("utf-16")
        assert s == self.conststr('\xff\xfe\xff\xff')
        py.test.raises(UnicodeEncodeError, u.encode, "latin-1")
        py.test.raises(UnicodeEncodeError, u.encode, "ascii")

    def test_encode_errors(self):
        u = self.constunicode(u"b\uffffa\xff")
        s = u.encode("latin-1", "replace")
        assert s == self.conststr('b?a\xff')
        s = u.encode("latin-1", "ignore")
        assert s == self.conststr('ba\xff')
        s = u.encode("ascii", "replace")
        assert s == self.conststr('b?a?')
        s = u.encode("ascii", "ignore")
        assert s == self.conststr('ba')

    def test_decode(self):
        u = self.conststr("abc")
        s = u.decode("utf-8")
        assert u == self.constunicode(u"abc")
        s = u.decode("latin-1")
        assert u == self.constunicode(u"abc")
        s = u.decode("ascii")
        assert u == self.constunicode(u"abc")
        s = self.conststr("\xff")
        u = s.decode("latin-1")
        assert u == self.constunicode(u"\xff")
        py.test.raises(UnicodeDecodeError, s.decode, "ascii")

    def test_decode_errors(self):
        s = self.conststr("a\xffb")
        u = s.decode("ascii", "replace")
        assert u == self.constunicode(u"a\ufffdb")
        u = s.decode("ascii", "ignore")
        assert u == self.constunicode(u"ab")



    def test_add_coercion(self):
        s1 = self.conststr("abc")
        s2 = self.constunicode("def")
        s = s1 + s2
        assert isinstance(s, self.constunicode)
        assert s == self.constunicode("abcdef")
        s = s2 + s1
        assert isinstance(s, self.constunicode)
        assert s == self.constunicode("defabc")

    def test_add_coercion_decodes(self):
        s1 = self.conststr("\xff")
        s2 = self.constunicode("a")
        py.test.raises(UnicodeDecodeError, "s1 + s2")
        py.test.raises(UnicodeDecodeError, "s2 + s1")

class TestPythonCoercion(AbstractTestCoercion):
    conststr = str
    constunicode = unicode

class TestRopesCoercion(AbstractTestCoercion):
    conststr = RopeString
    constunicode = RopeUnicode

    def test_add_coercion_long(self):
        s1 = self.conststr("a")
        s2 = self.constunicode("b") * (2 ** 30)
        s3 = s1 + s2
        assert len(s3) == 2 ** 30 + 1
        assert s3[0] == "a"
        assert s3[1] == "b"
        assert s3[5] == "b"
        assert s3[-1] == "b"
