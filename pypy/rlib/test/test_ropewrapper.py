from pypy.rlib.ropewrapper import RopeUnicode, RopeString

class AbstractTest(object):

    def test_construction(self):
        s = self.const("abc")
        assert len(s) == 3
        assert s[0] == self.const("a")
        assert s[1] == self.const("b")
        assert s[2] == self.const("c")

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
        import pdb; pdb.set_trace()
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
        # XXX rope iteration is working but should use a custom iterator
        # e.g. define an __iter__ method
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


class TestString(AbstractTest):
    const = RopeString

class TestPythonString(AbstractTest):
    const = str

class TestUnicode(AbstractTest):
    const = RopeUnicode

class TestPythonUnicode(AbstractTest):
    const = unicode


