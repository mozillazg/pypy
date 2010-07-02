import _sre, re
import rsre


def get_code(regexp):
    class GotIt(Exception):
        pass
    def my_compile(pattern, flags, code, *args):
        raise GotIt(code)
    saved = _sre.compile
    try:
        _sre.compile = my_compile
        try:
            re.compile(regexp)
        except GotIt, e:
            pass
    finally:
        _sre.compile = saved
    return e.args[0], re.compile(regexp)


class TestMatch:

    def test_any(self):
        r, _ = get_code(r"ab.cd")
        assert rsre.match(r, "abXcdef")
        assert not rsre.match(r, "ab\ncdef")
        assert not rsre.match(r, "abXcDef")

    def test_any_repetition(self):
        r, _ = get_code(r"ab.*cd")
        assert rsre.match(r, "abXXXXcdef")
        assert rsre.match(r, "abcdef")
        assert not rsre.match(r, "abX\nXcdef")
        assert not rsre.match(r, "abXXXXcDef")

    def test_any_all(self):
        r, _ = get_code(r"(?s)ab.cd")
        assert rsre.match(r, "abXcdef")
        assert rsre.match(r, "ab\ncdef")
        assert not rsre.match(r, "ab\ncDef")

    def test_any_all_repetition(self):
        r, _ = get_code(r"(?s)ab.*cd")
        assert rsre.match(r, "abXXXXcdef")
        assert rsre.match(r, "abcdef")
        assert rsre.match(r, "abX\nXcdef")
        assert not rsre.match(r, "abX\nXcDef")

    def test_assert(self):
        r, _ = get_code(r"abc(?=def)(.)")
        res = rsre.match(r, "abcdefghi")
        assert res is not None and res.get_mark(1) == 4
        assert not rsre.match(r, "abcdeFghi")

    def test_assert_not(self):
        r, _ = get_code(r"abc(?!def)(.)")
        res = rsre.match(r, "abcdeFghi")
        assert res is not None and res.get_mark(1) == 4
        assert not rsre.match(r, "abcdefghi")

    def test_lookbehind(self):
        r, _ = get_code(r"([a-z]*)(?<=de)")
        assert rsre.match(r, "ade")
        res = rsre.match(r, "adefg")
        assert res is not None and res.get_mark(1) == 3
        assert not rsre.match(r, "abc")
        assert not rsre.match(r, "X")
        assert not rsre.match(r, "eX")

    def test_negative_lookbehind(self):
        def found(s):
            res = rsre.match(r, s)
            assert res is not None
            return res.get_mark(1)
        r, _ = get_code(r"([a-z]*)(?<!dd)")
        assert found("ade") == 3
        assert found("adefg") == 5
        assert found("abcdd") == 4
        assert found("abddd") == 3
        assert found("adddd") == 2
        assert found("ddddd") == 1
        assert found("abXde") == 2

    def test_at(self):
        r, _ = get_code(r"abc$")
        assert rsre.match(r, "abc")
        assert not rsre.match(r, "abcd")
        assert not rsre.match(r, "ab")

    def test_category(self):
        r, _ = get_code(r"ab\dcd")
        assert rsre.match(r, "ab0cd")
        assert rsre.match(r, "ab9cd")
        assert not rsre.match(r, "abXcd")
        assert not rsre.match(r, "ab+cd")
