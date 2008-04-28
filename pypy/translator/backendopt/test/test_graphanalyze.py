from pypy.translator.backendopt.graphanalyze import ImpurityAnalyzer
from pypy.translator.translator import TranslationContext
from pypy.rpython.test.tool import LLRtypeMixin, OORtypeMixin
from pypy.conftest import option

class BaseTestImpurityAnalyzer(object):
    type_system = None

    def translate(self, func, sig):
        t = TranslationContext()
        self.translator = t
        t.buildannotator().build_types(func, sig)
        t.buildrtyper(type_system=self.type_system).specialize()
        if option.view:
            t.view()
        return ImpurityAnalyzer(t)

    def test_simple_pure(self):
        def nothing_much(x):
            return (x+17) * 2
        impurity = self.translate(nothing_much, [int])
        res = impurity.analyze_direct_call(self.translator.graphs[0])
        assert res is False     # not impure

    def test_simple_impure(self):
        class Global:
            pass
        glob = Global()
        def has_side_effects(x):
            glob.foo = x
        impurity = self.translate(has_side_effects, [int])
        res = impurity.analyze_direct_call(self.translator.graphs[0])
        assert res is True     # impure

    def test_simple_raising(self):
        def raising(x):
            if x < 0:
                raise ValueError
        impurity = self.translate(raising, [int])
        res = impurity.analyze_direct_call(self.translator.graphs[0])
        assert res is True     # impure

    def test_larger_example(self):
        def myint_internal(case, start=0):
            if case == 1:
                s = "foobar"
            else:
                s = "dummy"
            if start >= len(s):
                return -1
            res = 0
            while start < len(s):
                c = s[start]
                n = ord(c) - ord('0')
                if not (0 <= n <= 9):
                    return -1
                res = res * 10 + n
                start += 1
            return res
        impurity = self.translate(myint_internal, [int, int])
        res = impurity.analyze_direct_call(self.translator.graphs[0])
        assert res is False     # not impure

class TestLLType(LLRtypeMixin, BaseTestImpurityAnalyzer):
    pass

class TestOOType(OORtypeMixin, BaseTestImpurityAnalyzer):
    pass
