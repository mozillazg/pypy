import py
from pypy.rlib.jit import JitDriver, dont_look_inside, we_are_jitted
from pypy.jit.codewriter.policy import StopAtXPolicy
from pypy.rpython.ootypesystem import ootype
from pypy.jit.metainterp.test.test_basic import LLJitMixin, OOJitMixin


class StringTests:
    def test_eq_residual(self):
        jitdriver = JitDriver(greens = [], reds = ['n', 'i', 's'])
        global_s = "hello"
        def f(n, b, s):
            if b:
                s += "ello"
            else:
                s += "allo"
            i = 0
            while n > 0:
                jitdriver.can_enter_jit(s=s, n=n, i=i)
                jitdriver.jit_merge_point(s=s, n=n, i=i)
                n -= 1 + (s == global_s)
                i += 1
            return i
        res = self.meta_interp(f, [10, True, 'h'], listops=True)
        assert res == 5
        self.check_loops(**{self.CALL: 1, self.CALL_PURE: 0})

    def test_eq_folded(self):
        jitdriver = JitDriver(greens = ['s'], reds = ['n', 'i'])
        global_s = "hello"
        def f(n, b, s):
            if b:
                s += "ello"
            else:
                s += "allo"
            i = 0
            while n > 0:
                jitdriver.can_enter_jit(s=s, n=n, i=i)
                jitdriver.jit_merge_point(s=s, n=n, i=i)
                n -= 1 + (s == global_s)
                i += 1
            return i
        res = self.meta_interp(f, [10, True, 'h'], listops=True)
        assert res == 5
        self.check_loops(**{self.CALL: 0, self.CALL_PURE: 0})

    def test_newstr(self):
        jitdriver = JitDriver(greens = [], reds = ['n', 'm'])
        def f(n, m):
            while True:
                jitdriver.can_enter_jit(m=m, n=n)
                jitdriver.jit_merge_point(m=m, n=n)
                bytecode = 'adlfkj' + chr(n)
                res = bytecode[n]
                m -= 1
                if m < 0:
                    return ord(res)
        res = self.meta_interp(f, [6, 10])
        assert res == 6

    def test_newunicode(self):
        jitdriver = JitDriver(greens = [], reds = ['n', 'm'])
        def f(n, m):
            while True:
                jitdriver.can_enter_jit(m=m, n=n)
                jitdriver.jit_merge_point(m=m, n=n)
                bytecode = u'adlfkj' + unichr(n)
                res = bytecode[n]
                m -= 1
                if m < 0:
                    return ord(res)
        res = self.meta_interp(f, [6, 10])
        assert res == 6

    def test_char2string_pure(self):
        for dochr in [chr, ]: #unichr]:
            jitdriver = JitDriver(greens = [], reds = ['n'])
            @dont_look_inside
            def escape(x):
                pass
            def f(n):
                while n > 0:
                    jitdriver.can_enter_jit(n=n)
                    jitdriver.jit_merge_point(n=n)
                    s = dochr(n)
                    if not we_are_jitted():
                        s += s     # forces to be a string
                    if n > 100:
                        escape(s)
                    n -= 1
                return 42
            self.meta_interp(f, [6])
            self.check_loops(newstr=0, strsetitem=0, strlen=0,
                             newunicode=0, unicodesetitem=0, unicodelen=0)

    def test_char2string_escape(self):
        for dochr in [chr, ]: #unichr]:
            jitdriver = JitDriver(greens = [], reds = ['n', 'total'])
            @dont_look_inside
            def escape(x):
                return ord(x[0])
            def f(n):
                total = 0
                while n > 0:
                    jitdriver.can_enter_jit(n=n, total=total)
                    jitdriver.jit_merge_point(n=n, total=total)
                    s = dochr(n)
                    if not we_are_jitted():
                        s += s    # forces to be a string
                    total += escape(s)
                    n -= 1
                return total
            res = self.meta_interp(f, [6])
            assert res == 21

    def test_char2string2char(self):
        for dochr in [chr, ]: #unichr]:
            jitdriver = JitDriver(greens = [], reds = ['m', 'total'])
            def f(m):
                total = 0
                while m > 0:
                    jitdriver.can_enter_jit(m=m, total=total)
                    jitdriver.jit_merge_point(m=m, total=total)
                    string = dochr(m)
                    if m > 100:
                        string += string    # forces to be a string
                    # read back the character
                    c = string[0]
                    total += ord(c)
                    m -= 1
                return total
            res = self.meta_interp(f, [6])
            assert res == 21
            self.check_loops(newstr=0, strgetitem=0, strsetitem=0, strlen=0,
                             newunicode=0, unicodegetitem=0, unicodesetitem=0,
                             unicodelen=0)

    def test_slice_startonly(self):
        if 1:     # xxx unicode
            jitdriver = JitDriver(greens = [], reds = ['m', 'total'])
            def f(m):
                total = 0
                while m >= 0:
                    jitdriver.can_enter_jit(m=m, total=total)
                    jitdriver.jit_merge_point(m=m, total=total)
                    string = 's0dgkwn349tXOGIEQR!'[m:]
                    c = string[2*m]
                    total += ord(c)
                    m -= 1
                return total
            res = self.meta_interp(f, [6])
            assert res == sum(map(ord, 'sgn9OE!'))
            py.test.xfail()
            self.check_loops(call=0, call_pure=0,
                             newstr=0, strgetitem=1, strsetitem=0, strlen=0)

    def test_strconcat_pure(self):
        for somestr in ["abc", ]: #u"def"]:
            jitdriver = JitDriver(greens = [], reds = ['m', 'n'])
            @dont_look_inside
            def escape(x):
                pass
            mylist = [somestr+str(i) for i in range(10)]
            def f(n, m):
                while m >= 0:
                    jitdriver.can_enter_jit(m=m, n=n)
                    jitdriver.jit_merge_point(m=m, n=n)
                    s = mylist[n] + mylist[m]
                    if m > 100:
                        escape(s)
                    m -= 1
                return 42
            self.meta_interp(f, [6, 7])
            self.check_loops(newstr=0, strsetitem=0,
                             newunicode=0, unicodesetitem=0,
                             call=0, call_pure=0)

    def test_strconcat_escape(self):
        for somestr in ["abc", ]: #u"def"]:
            jitdriver = JitDriver(greens = [], reds = ['m', 'n'])
            @dont_look_inside
            def escape(x):
                pass
            mylist = [somestr+str(i) for i in range(10)]
            def f(n, m):
                while m >= 0:
                    jitdriver.can_enter_jit(m=m, n=n)
                    jitdriver.jit_merge_point(m=m, n=n)
                    s = mylist[n] + mylist[m]
                    escape(s)
                    m -= 1
                return 42
            self.meta_interp(f, [6, 7])
            self.check_loops(newstr=0, strsetitem=0,
                             newunicode=0, unicodesetitem=0,
                             call=2, call_pure=0)   # ll_strconcat, escape

    def test_strconcat_guard_fail(self):
        for somestr in ["abc", ]: #u"def"]:
            jitdriver = JitDriver(greens = [], reds = ['m', 'n'])
            @dont_look_inside
            def escape(x):
                pass
            mylist = [somestr+str(i) for i in range(12)]
            def f(n, m):
                while m >= 0:
                    jitdriver.can_enter_jit(m=m, n=n)
                    jitdriver.jit_merge_point(m=m, n=n)
                    s = mylist[n] + mylist[m]
                    if m & 1:
                        escape(s)
                    m -= 1
                return 42
            self.meta_interp(f, [6, 10])
            self.check_loops(newstr=0, strsetitem=0,
                             newunicode=0, unicodesetitem=0)


class TestOOtype(StringTests, OOJitMixin):
    CALL = "oosend"
    CALL_PURE = "oosend_pure"

class TestLLtype(StringTests, LLJitMixin):
    CALL = "call"
    CALL_PURE = "call_pure"
