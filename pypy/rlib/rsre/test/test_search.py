from pypy.rlib.rsre import rsre


# <item>\s*<title>(.*?)</title>
r_code1 = [17, 18, 1, 21, 131091, 6, 6, 60, 105, 116, 101, 109, 62, 0,
0, 0, 0, 0, 0, 19, 60, 19, 105, 19, 116, 19, 101, 19, 109, 19, 62, 29,
9, 0, 65535, 15, 4, 9, 2, 0, 1, 19, 60, 19, 116, 19, 105, 19, 116, 19,
108, 19, 101, 19, 62, 21, 0, 31, 5, 0, 65535, 2, 1, 21, 1, 19, 60, 19,
47, 19, 116, 19, 105, 19, 116, 19, 108, 19, 101, 19, 62, 1]


class TestSearch:

    def test_simple(self):
        state = rsre.SimpleStringState("foo<item>  <title>abc</title>def")
        res = state.search(r_code1)
        assert res is True
        groups = state.create_regs(1)
        assert groups[0] == (3, 29)
        assert groups[1] == (18, 21)


if __name__ == '__main__':
    import re, _sre
    def my_compile(pattern, flags, code, *args):
        print code
    _sre.compile = my_compile
    re.compile(r'<item>\s*<title>(.*?)</title>')
