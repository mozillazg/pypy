import py
from pypy.rlib.jit import jit_merge_point, can_enter_jit
from pypy.jit.rainbow.test import test_interpreter
from pypy.jit.rainbow.hotpath import EntryPointsRewriter
from pypy.jit.hintannotator.policy import HintAnnotatorPolicy
from pypy.rpython.llinterp import LLInterpreter
from pypy import conftest

P_HOTPATH = HintAnnotatorPolicy(oopspec=True,
                                novirtualcontainer=True,
                                hotpath=True)

class Exit(Exception):
    def __init__(self, result):
        self.result = result

class TestHotPath(test_interpreter.InterpretationTest):
    type_system = 'lltype'

    def run(self, main, main_args, threshold, policy=P_HOTPATH, small=False):
        self.serialize(main, main_args, policy=policy, backendoptimize=True)
        rewriter = EntryPointsRewriter(self.hintannotator, self.rtyper,
                                       self.jitcode, self.RGenOp, self.writer,
                                       threshold, self.translate_support_code)
        self.rewriter = rewriter
        rewriter.rewrite_all()
        if small and conftest.option.view:
            self.rtyper.annotator.translator.view()

        graph = self.rtyper.annotator.translator.graphs[0]
        assert graph.func is main
        llinterp = LLInterpreter(
            self.rtyper, exc_data_ptr=self.writer.exceptiondesc.exc_data_ptr)
        return llinterp.eval_graph(graph, main_args)

    def check_traces(self, expected):
        py.test.skip("traces in progress")


    def test_simple_loop(self):
        # there are no greens in this test
        def ll_function(n):
            n1 = n * 2
            total = 0
            while True:
                jit_merge_point(red=(n1, total))
                total += n1
                if n1 <= 1:
                    break
                n1 -= 1
                can_enter_jit(red=(n1, total))
            raise Exit(total)

        def main(n, m):
            try:
                ll_function(n * m)
            except Exit, e:
                return e.result

        res = self.run(main, [2, 5], threshold=8, small=True)
        assert res == main(2, 5)
        self.check_traces([
            # running non-JITted leaves the initial profiling traces
            # recorded by jit_may_enter().  We see the values of n1 and total.
            "jit_not_entered 20 0",
            "jit_not_entered 19 20",
            "jit_not_entered 18 39",
            "jit_not_entered 17 57",
            "jit_not_entered 16 74",
            "jit_not_entered 15 90",
            "jit_not_entered 14 105",
            "jit_not_entered 13 119",
            # on the start of the next iteration, compile the 'total += n1'
            "jit_enter",
            "pause at hotsplit",
            # execute the compiled machine code until the 'n1 <= 1'.
            # It finishes in the fallback interpreter 7 times
            "run_machine_code 12 132", "fallback_interp", "fb_leave 11 144",
            "run_machine_code 11 144", "fallback_interp", "fb_leave 10 155",
            "run_machine_code 10 155", "fallback_interp", "fb_leave 9 165",
            "run_machine_code 9 165", "fallback_interp", "fb_leave 8 174",
            "run_machine_code 8 174", "fallback_interp", "fb_leave 7 182",
            "run_machine_code 7 182", "fallback_interp", "fb_leave 6 189",
            "run_machine_code 6 189", "fallback_interp", "fb_leave 5 195",
            "run_machine_code 5 195",
            # now that we know which path is hot (i.e. "staying in the loop"),
            # it gets compiled
            "jit_resume",
            "done at jit_merge_point",
            # execution continues purely in machine code, from the "n1 <= 1"
            # test which triggered the "jit_resume"
            "resume_machine_code",
            # finally, go back to the fallback interp when "n1 <= 1" is True
            "fallback_interp",
            "fb_raise Exit"])
