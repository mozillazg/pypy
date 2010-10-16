from pypy.jit.metainterp.test import test_basic
from pypy.rlib.nonconst import NonConstant
from pypy.rlib.debug import make_sure_not_modified
from pypy.rlib.rsre.test.test_match import get_code
from pypy.rlib.rsre import rsre_core
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.annlowlevel import llstr, hlstr

def entrypoint1(r, string):
    r = array2list(r)
    string = hlstr(string)
    make_sure_not_modified(r)
    match = rsre_core.match(r, string)
    if match is None:
        return -1
    else:
        return match.match_end

def list2array(lst):
    a = lltype.malloc(lltype.GcArray(lltype.Signed), len(lst))
    for i, x in enumerate(lst):
        a[i] = x
    return a

def array2list(a):
    return [a[i] for i in range(len(a))]


def test_jit_unroll_safe():
    # test that the decorators are applied in the right order
    assert not hasattr(rsre_core.sre_match, '_jit_unroll_safe_')
    for m in rsre_core.sre_match._specialized_methods_:
        assert m._jit_unroll_safe_


class TestJitRSre(test_basic.LLJitMixin):

    def meta_interp_match(self, pattern, string):
        r = get_code(pattern)
        return self.meta_interp(entrypoint1, [list2array(r), llstr(string)],
                                listcomp=True, backendopt=True)

    def test_simple_match_1(self):
        res = self.meta_interp_match(r"ab*bbbbbbbc", "abbbbbbbbbcdef")
        assert res == 11

    def test_simple_match_2(self):
        res = self.meta_interp_match(r".*abc", "xxabcyyyyyyyyyyyyy")
        assert res == 5

    def test_match_minrepeat_1(self):
        res = self.meta_interp_match(r".*?abc", "xxxxxxxxxxxxxxabc")
        assert res == 17

    #def test_match_maxuntil_1(self):
    #    res = self.meta_interp_match(r"(ab)*c", "ababababababababc")
    #    assert res == 17

    def test_branch_1(self):
        res = self.meta_interp_match(r".*?(ab|x)c", "xxxxxxxxxxxxxxabc")
        assert res == 17

    def test_match_minrepeat_2(self):
        s = ("xxxxxxxxxxabbbbbbbbbb" +
             "xxxxxxxxxxabbbbbbbbbb" +
             "xxxxxxxxxxabbbbbbbbbb" +
             "xxxxxxxxxxabbbbbbbbbbc")
        res = self.meta_interp_match(r".*?ab+?c", s)
        assert res == len(s)
