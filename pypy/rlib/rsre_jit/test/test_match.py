import _sre, re, sre_compile
from pypy.rlib.rsre_jit import rsre


def get_code(regexp):
    class GotIt(Exception):
        pass
    def my_compile(pattern, flags, code, *args):
        print code
        raise GotIt(code)
    saved = _sre.compile
    try:
        _sre.compile = my_compile
        try:
            sre_compile.compile(regexp, 0)
        except GotIt, e:
            pass
        else:
            raise ValueError("did not reach _sre.compile()!")
    finally:
        _sre.compile = saved
    return e.args[0]

def get_code_and_re(regexp):
    return get_code(regexp), re.compile(regexp)

def test_get_code_repetition():
    c1 = get_code(r"a+")
    c2 = get_code(r"a+")
    assert c1 == c2


class TestMatch:

    def test_or(self):
        r = get_code(r"a|bc|def")
        assert rsre.match(r, "a")
        assert rsre.match(r, "bc")
        assert rsre.match(r, "def")
        assert not rsre.match(r, "ghij")

    def test_any(self):
        r = get_code(r"ab.cd")
        assert rsre.match(r, "abXcdef")
        assert not rsre.match(r, "ab\ncdef")
        assert not rsre.match(r, "abXcDef")

    def test_any_repetition(self):
        r = get_code(r"ab.*cd")
        assert rsre.match(r, "abXXXXcdef")
        assert rsre.match(r, "abcdef")
        assert not rsre.match(r, "abX\nXcdef")
        assert not rsre.match(r, "abXXXXcDef")

    def test_any_all(self):
        r = get_code(r"(?s)ab.cd")
        assert rsre.match(r, "abXcdef")
        assert rsre.match(r, "ab\ncdef")
        assert not rsre.match(r, "ab\ncDef")

    def test_any_all_repetition(self):
        r = get_code(r"(?s)ab.*cd")
        assert rsre.match(r, "abXXXXcdef")
        assert rsre.match(r, "abcdef")
        assert rsre.match(r, "abX\nXcdef")
        assert not rsre.match(r, "abX\nXcDef")

    def test_assert(self):
        r = get_code(r"abc(?=def)(.)")
        res = rsre.match(r, "abcdefghi")
        assert res is not None and res.get_mark(1) == 4
        assert not rsre.match(r, "abcdeFghi")

    def test_assert_not(self):
        r = get_code(r"abc(?!def)(.)")
        res = rsre.match(r, "abcdeFghi")
        assert res is not None and res.get_mark(1) == 4
        assert not rsre.match(r, "abcdefghi")

    def test_lookbehind(self):
        r = get_code(r"([a-z]*)(?<=de)")
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
        r = get_code(r"([a-z]*)(?<!dd)")
        assert found("ade") == 3
        assert found("adefg") == 5
        assert found("abcdd") == 4
        assert found("abddd") == 3
        assert found("adddd") == 2
        assert found("ddddd") == 1
        assert found("abXde") == 2

    def test_at(self):
        r = get_code(r"abc$")
        assert rsre.match(r, "abc")
        assert not rsre.match(r, "abcd")
        assert not rsre.match(r, "ab")

    def test_repeated_set(self):
        r = get_code(r"[a0x]+f")
        assert rsre.match(r, "a0af")
        assert not rsre.match(r, "a0yaf")

    def test_category(self):
        r = get_code(r"[\sx]")
        assert rsre.match(r, "x")
        assert rsre.match(r, " ")
        assert not rsre.match(r, "n")

    def test_groupref(self):
        r = get_code(r"(xx+)\1+$")     # match non-prime numbers of x
        assert not rsre.match(r, "xx")
        assert not rsre.match(r, "xxx")
        assert     rsre.match(r, "xxxx")
        assert not rsre.match(r, "xxxxx")
        assert     rsre.match(r, "xxxxxx")
        assert not rsre.match(r, "xxxxxxx")
        assert     rsre.match(r, "xxxxxxxx")
        assert     rsre.match(r, "xxxxxxxxx")

    def test_groupref_ignore(self):
        r = get_code(r"(?i)(xx+)\1+$")     # match non-prime numbers of x
        assert not rsre.match(r, "xX")
        assert not rsre.match(r, "xxX")
        assert     rsre.match(r, "Xxxx")
        assert not rsre.match(r, "xxxXx")
        assert     rsre.match(r, "xXxxxx")
        assert not rsre.match(r, "xxxXxxx")
        assert     rsre.match(r, "xxxxxxXx")
        assert     rsre.match(r, "xxxXxxxxx")

    def test_in_ignore(self):
        r = get_code(r"(?i)[a-f]")
        assert rsre.match(r, "b")
        assert rsre.match(r, "C")
        assert not rsre.match(r, "g")
        r = get_code(r"(?i)[a-f]+$")
        assert rsre.match(r, "bCdEf")
        assert not rsre.match(r, "g")
        assert not rsre.match(r, "aaagaaa")

    def test_not_literal(self):
        r = get_code(r"[^a]")
        assert rsre.match(r, "A")
        assert not rsre.match(r, "a")
        r = get_code(r"[^a]+$")
        assert rsre.match(r, "Bx123")
        assert not rsre.match(r, "--a--")

    def test_not_literal_ignore(self):
        r = get_code(r"(?i)[^a]")
        assert rsre.match(r, "G")
        assert not rsre.match(r, "a")
        assert not rsre.match(r, "A")
        r = get_code(r"(?i)[^a]+$")
        assert rsre.match(r, "Gx123")
        assert not rsre.match(r, "--A--")

    def test_repeated_single_character_pattern(self):
        r = get_code(r"foo(?:(?<=foo)x)+$")
        assert rsre.match(r, "foox")

    def test_flatten_marks(self):
        r = get_code(r"a(b)c((d)(e))+$")
        res = rsre.match(r, "abcdedede")
        assert res.flatten_marks() == [0, 9, 1, 2, 7, 9, 7, 8, 8, 9]
        assert res.flatten_marks() == [0, 9, 1, 2, 7, 9, 7, 8, 8, 9]

    def test_bug1(self):
        # REPEAT_ONE inside REPEAT
        r = get_code(r"(?:.+)?B")
        assert rsre.match(r, "AB") is not None
        r = get_code(r"(?:AA+?)+B")
        assert rsre.match(r, "AAAB") is not None
        r = get_code(r"(?:AA+)+?B")
        assert rsre.match(r, "AAAB") is not None
        r = get_code(r"(?:AA+?)+?B")
        assert rsre.match(r, "AAAB") is not None
        # REPEAT inside REPEAT
        r = get_code(r"(?:(?:xy)+)?B")
        assert rsre.match(r, "xyB") is not None
        r = get_code(r"(?:xy(?:xy)+?)+B")
        assert rsre.match(r, "xyxyxyB") is not None
        r = get_code(r"(?:xy(?:xy)+)+?B")
        assert rsre.match(r, "xyxyxyB") is not None
        r = get_code(r"(?:xy(?:xy)+?)+?B")
        assert rsre.match(r, "xyxyxyB") is not None

    def test_assert_group(self):
        r = get_code(r"abc(?=(..)f)(.)")
        res = rsre.match(r, "abcdefghi")
        assert res is not None
        assert res.span(2) == (3, 4)
        assert res.span(1) == (3, 5)

    def test_assert_not_group(self):
        r = get_code(r"abc(?!(de)f)(.)")
        res = rsre.match(r, "abcdeFghi")
        assert res is not None
        assert res.span(2) == (3, 4)
        # this I definitely classify as Horrendously Implementation Dependent.
        # CPython answers (3, 5).
        assert res.span(1) == (-1, -1)
