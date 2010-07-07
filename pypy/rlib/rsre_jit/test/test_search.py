from pypy.rlib.rsre_jit import rsre
from pypy.rlib.rsre_jit.test.test_match import get_code


class TestSearch:

    def test_code1(self):
        r_code1 = get_code(r'[abc][def][ghi]')
        res = rsre.search(r_code1, "fooahedixxx")
        assert res is None
        res = rsre.search(r_code1, "fooahcdixxx")
        assert res is not None
        assert res.span() == (5, 8)

    def test_code2(self):
        r_code2 = get_code(r'<item>\s*<title>(.*?)</title>')
        res = rsre.search(r_code2, "foo bar <item>  <title>abc</title>def")
        assert res is not None
        assert res.span() == (8, 34)

    def test_pure_literal(self):
        r_code3 = get_code(r'foobar')
        res = rsre.search(r_code3, "foo bar foobar baz")
        assert res is not None
        assert res.span() == (8, 14)
