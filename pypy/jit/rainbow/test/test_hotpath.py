import py
import re
from pypy.rlib.jit import jit_merge_point, can_enter_jit, hint
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
        traces = self.rewriter.interpreter.debug_traces
        i = 0
        for trace, expect in zip(traces + ['--end of traces--'],
                                 expected + ['--end of traces--']):
            # '...' in the expect string stands for any sequence of characters
            regexp = '.*'.join(map(re.escape, expect.split('...'))) + '$'
            # 'trace' is a DebugTrace instance, reduce it to a string
            match = re.match(regexp, str(trace))
            assert match, ("debug_trace[%d] mismatch:\n"
                           "       got: %s\n"
                           "  expected: %s" % (i, trace, expect))
            i += 1


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
            "jit_not_entered 19 20",
            "jit_not_entered 18 39",
            "jit_not_entered 17 57",
            "jit_not_entered 16 74",
            "jit_not_entered 15 90",
            "jit_not_entered 14 105",
            "jit_not_entered 13 119",
            # on the start of the next iteration, compile the 'total += n1'
            "jit_compile 12 132",
            "pause at hotsplit in ll_function",
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
            "jit_resume bool_path False in ll_function",
            "done at jit_merge_point",
            # execution continues purely in machine code, from the "n1 <= 1"
            # test which triggered the "jit_resume"
            "resume_machine_code",
            # finally, go back to the fallback interp when "n1 <= 1" is True
            "fallback_interp",
            "fb_raise Exit"])

    def test_greens(self):
        def ll_function(code, buffer):
            data = 0
            accum = 0
            pc = 0
            while True:
                jit_merge_point(green=(code, pc), red=(accum, data, buffer))
                if pc == len(code):
                    raise Exit(accum)
                c = code[pc]
                pc += 1
                c = hint(c, concrete=True)
                if c == 'I':
                    accum += 1                   # increment
                elif c == 'D':
                    accum -= 1                   # decrement
                elif c == 'S':
                    accum, data = data, accum    # swap
                elif c == 'W':
                    buffer = accum               # write
                elif c == 'R':
                    accum = buffer               # read
                elif c == '*':
                    accum *= data
                elif c == '%':
                    accum %= data
                elif c == '?':
                    accum = int(bool(accum))
                elif c == '{':
                    if accum == 0:               # loop while != 0
                        while code[pc] != '}':
                            pc += 1
                        pc += 1
                elif c == '}':
                    if accum != 0:
                        pc -= 2                      # end of loop
                        assert pc >= 0
                        while code[pc] != '{':
                            pc -= 1
                            assert pc >= 0
                        pc += 1
                        can_enter_jit(green=(code, pc), red=(accum,
                                                             data, buffer))

        def main(demo, arg):
            if demo == 1:
                code = 'RSIS{S*SD}S'    # factorial
            elif demo == 2:
                code = 'ISRDD{ISR%?SDD*}S'  # prime number tester (for arg>=2)
            else:
                raise ValueError
            try:
                ll_function(code, arg)
            except Exit, e:
                return e.result

        assert main(1, 10) == 10*9*8*7*6*5*4*3*2*1
        assert ([main(2, n)
                 for n in [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]]
                ==        [1, 1, 0, 1, 0, 1, 0, 0,  0,  1,  0,  1,  0,  0])

        res = self.run(main, [1, 10], threshold=3, small=True)
        assert res == main(1, 10)
        self.check_traces([
            # start compiling the 3rd time we loop back
                "jit_not_entered * struct rpy_string {...} 5 9 10 10",
                "jit_not_entered * struct rpy_string {...} 5 8 90 10",
                "jit_compile * struct rpy_string {...} 5 7 720 10",
            # stop compiling at the red split ending an extra iteration
                "pause at hotsplit in ll_function",
            # run it, finishing twice through the fallback interp
                "run_machine_code * struct rpy_string {...} 5 7 720 10",
                "fallback_interp",
                "fb_leave * struct rpy_string {...} 5 6 5040 10",
                "run_machine_code * struct rpy_string {...} 5 6 5040 10",
                "fallback_interp",
                "fb_leave * struct rpy_string {...} 5 5 30240 10",
                "run_machine_code * struct rpy_string {...} 5 5 30240 10",
            # the third time, compile the hot path, which closes the loop
            # in the generated machine code
                "jit_resume bool_path True in ll_function",
                "done at jit_merge_point",
            # continue running 100% in the machine code as long as necessary
                "resume_machine_code",
            # at the end, use the fallbac interp to follow the exit path
                "fallback_interp",
                "fb_leave * struct rpy_string {...} 10 0 3628800 10",
            # finally, we interpret the final 'S' character
            # which gives us the final answer
            ])
