from pypy.objspace.flow.model import summary
from pypy.rlib.jit import hint, we_are_jitted
from pypy.jit.hintannotator.policy import HintAnnotatorPolicy
from pypy.jit.hintannotator.test.test_annotator import AbstractAnnotatorTest


P_HOTPATH = HintAnnotatorPolicy(oopspec=True,
                                novirtualcontainer=True,
                                hotpath=True)

class TestHotPath(AbstractAnnotatorTest):
    type_system = 'lltype'

    def hannotate(self, func, argtypes, policy=P_HOTPATH):
        # change default policy
        AbstractAnnotatorTest.hannotate(self, func, argtypes, policy=policy)

    def test_simple_loop(self):
        def ll_function(n):
            n1 = n * 2
            total = 0
            while n1 > 0:
                hint(None, can_enter_jit=True)
                hint(None, global_merge_point=True)
                if we_are_jitted():
                    total += 1000
                total += n1
                n1 -= 1
            return total

        def main(n, m):
            return ll_function(n * m)

        self.hannotate(main, [int, int])
        graphs = self.hannotator.translator.graphs
        assert len(graphs) == 1
        assert ll_function is graphs[0].func
        assert 'int_mul' not in summary(graphs[0])
