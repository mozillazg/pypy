from pypy.objspace.flow.model import summary
from pypy.rlib.jit import JitDriver, we_are_jitted
from pypy.jit.hintannotator.policy import HintAnnotatorPolicy
from pypy.jit.hintannotator.test.test_annotator import AbstractAnnotatorTest


P_HOTPATH = HintAnnotatorPolicy(oopspec=True,
                                novirtualcontainer=True,
                                hotpath=True)

class TestHotPath(AbstractAnnotatorTest):
    type_system = 'lltype'

    def hannotate(self, func, argtypes, policy=P_HOTPATH, backendoptimize=True):
        # change default policy
        AbstractAnnotatorTest.hannotate(self, func, argtypes, policy=policy,
                                        backendoptimize=backendoptimize)

    def test_simple_loop(self):
        myjitdriver = JitDriver([], ['n1', 'total'])

        def ll_function(n):
            n1 = n * 2
            total = 0
            while True:
                myjitdriver.jit_merge_point(n1=n1, total=total)
                if n1 <= 0:
                    break
                if we_are_jitted():
                    total += 1000
                total += n1
                n1 -= 1
                myjitdriver.can_enter_jit(n1=n1, total=total)
            return total

        def main(n, m):
            return ll_function(n * m)

        self.hannotate(main, [int, int])
        graphs = self.hannotator.translator.graphs
        assert len(graphs) == 1
        assert ll_function is graphs[0].func
        assert 'int_mul' not in summary(graphs[0])

    def test_call(self):
        myjitdriver = JitDriver([], ['count', 'x', 'y'])

        def add(count, x, y):
            result = x + y
            myjitdriver.can_enter_jit(count=count, x=x, y=y)
            return result
        add._dont_inline_ = True
        def sub(x, y):
            return x - y
        sub._dont_inline_ = True
        def main(count, x, y):
            while True:
                myjitdriver.jit_merge_point(count=count, x=x, y=y)
                count -= 1
                if not count:
                    break
                if count % 3 == 0:
                    x = add(count, x, y)
                else:
                    y = sub(x, y)
        self.hannotate(main, [int, int, int])
