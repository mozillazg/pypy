from pypy.rlib.jit import jit_merge_point, can_enter_jit, we_are_jitted
from pypy.jit.rainbow.test import test_interpreter
from pypy.jit.rainbow.hotpath import EntryPointsRewriter
from pypy.jit.hintannotator.policy import HintAnnotatorPolicy
from pypy.rpython.llinterp import LLInterpreter

P_HOTPATH = HintAnnotatorPolicy(oopspec=True,
                                novirtualcontainer=True,
                                hotpath=True)


class TestHotPath(test_interpreter.InterpretationTest):
    type_system = 'lltype'

    def run(self, main, main_args, threshold, policy=P_HOTPATH):
        self.serialize(main, main_args, policy=policy, backendoptimize=True)
        rewriter = EntryPointsRewriter(self.hintannotator, self.rtyper,
                                       self.jitcode, self.RGenOp, self.writer,
                                       threshold, self.translate_support_code)
        self.rewriter = rewriter
        rewriter.rewrite_all()
        graph = self.rtyper.annotator.translator.graphs[0]
        assert graph.func is main
        llinterp = LLInterpreter(
            self.rtyper, exc_data_ptr=self.writer.exceptiondesc.exc_data_ptr)
        return llinterp.eval_graph(graph, main_args)

    def test_simple_loop(self):
        class Exit(Exception):
            def __init__(self, result):
                self.result = result

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
            raise Exit(total)

        def main(n, m):
            try:
                ll_function(n * m)
            except Exit, e:
                return e.result

        res = self.run(main, [2, 5], threshold=7)
        assert res == 210 + 14*1000
