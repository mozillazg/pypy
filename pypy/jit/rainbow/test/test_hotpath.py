from pypy.rlib.jit import jit_merge_point, can_enter_jit, we_are_jitted
from pypy.jit.rainbow.test import test_interpreter
from pypy.jit.hintannotator.policy import HintAnnotatorPolicy
from pypy.rpython.llinterp import LLInterpreter

P_HOTPATH = HintAnnotatorPolicy(oopspec=True,
                                novirtualcontainer=True,
                                hotpath=True)


class TestHotPath(test_interpreter.InterpretationTest):
    type_system = 'lltype'

    def run(self, main, main_args, threshold, policy=P_HOTPATH):
        self.serialize(main, main_args, policy=policy, backendoptimize=True)
        graph = self.rtyper.annotator.translator.graphs[0]
        assert graph.func is main
        llinterp = LLInterpreter(
            self.rtyper, exc_data_ptr=self.writer.exceptiondesc.exc_data_ptr)
        return llinterp.eval_graph(graph, main_args)

    def test_simple_loop(self):
        def ll_function(n):
            n1 = n * 2
            total = 0
            while n1 > 0:
                can_enter_jit(red=(n1, total))
                jit_merge_point(red=(n1, total))
                if we_are_jitted():
                    total += 1000
                total += n1
                n1 -= 1
            return total

        def main(n, m):
            return ll_function(n * m)

        res = self.run(main, [2, 5], threshold=7)
        assert res == 210 + 13*1000
