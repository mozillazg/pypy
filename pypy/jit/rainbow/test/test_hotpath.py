import py
import re
from pypy.rlib.jit import JitDriver, hint, JitHintError
from pypy.jit.rainbow.test import test_interpreter
from pypy.jit.rainbow.hotpath import HotRunnerDesc
from pypy.jit.hintannotator.policy import HintAnnotatorPolicy
from pypy.rpython.llinterp import LLInterpreter
from pypy import conftest

def make_hot_policy(policy):
    if not policy.hotpath:
        policy = policy.copy(oopspec                = True,
                             novirtualcontainer     = True,
                             hotpath                = True,
                             entrypoint_returns_red = False)
    return policy

P_HOTPATH = make_hot_policy(HintAnnotatorPolicy())

class Exit(Exception):
    def __init__(self, result):
        self.result = result

def summary_loops(graph):
    # Find all operations that are inside a loop.
    # Ignore the 'default' path of exitswitches, because they are
    # part of the pseudo-loop that jumps back to the exitswitch
    # after compiling more code.
    def visit(block):
        if block not in stackpos:
            stackpos[block] = len(blockstack)
            blockstack.append(block)
            for link in block.exits:
                if getattr(link, 'exitcase', None) != 'default':
                    visit(link.target)
            blockstack.pop()
            stackpos[block] = None
        else:
            if stackpos[block] is not None:   # back-edge
                for b in blockstack[stackpos[block]:]:
                    blocks_in_loop[b] = True
    blockstack = []
    stackpos = {}
    blocks_in_loop = {}
    visit(graph.startblock)
    # count operations
    insns = {}
    for block in blocks_in_loop:
        for op in block.operations:
            if op.opname != 'same_as':
                insns[op.opname] = insns.get(op.opname, 0) + 1
    return insns

# ____________________________________________________________

class HotPathTest(test_interpreter.InterpretationTest):
    type_system = 'lltype'
    simplify_virtualizable_accesses = False

    def interpret(self, main, ll_values, opt_consts=[], **kwds):
        py.test.skip("old-style test, port me")
    def interpret_raises(self, Exception, main, ll_values, opt_consts=[]):
        py.test.skip("old-style test, port me")

    def run(self, main, main_args, threshold, policy=P_HOTPATH, small=False):
        # xxx caching of tests doesn't work - do we care?
        policy = make_hot_policy(policy)
        self._serialize(main, main_args, policy=policy, backendoptimize=True)
        self._rewrite(threshold, small=small)
        return self._run(main, main_args)

    def _rewrite(self, threshold, small):
        assert len(self.hintannotator.jitdriverclasses) == 1
        jitdrivercls = self.hintannotator.jitdriverclasses.keys()[0]    # hack
        jitdrivercls.getcurrentthreshold = staticmethod(lambda : threshold) #..
        self.hotrunnerdesc = HotRunnerDesc(self.hintannotator, self.rtyper,
                                       self.jitcode, self.RGenOp, self.writer,
                                       jitdrivercls,
                                       self.translate_support_code)
        self.hotrunnerdesc.rewrite_all()
        if self.simplify_virtualizable_accesses:
            from pypy.jit.rainbow import graphopt
            graphopt.simplify_virtualizable_accesses(self.writer)
        if small and conftest.option.view:
            self.rtyper.annotator.translator.view()

    def _run(self, main, main_args):
        graph = self.rtyper.annotator.translator.graphs[0]
        assert graph.func is main
        llinterp = LLInterpreter(
            self.rtyper, exc_data_ptr=self.writer.exceptiondesc.exc_data_ptr)
        return llinterp.eval_graph(graph, main_args)

    def get_traces(self):
        return self.hotrunnerdesc.interpreter.debug_traces

    def check_traces(self, expected):
        if self.translate_support_code:
            return    # XXX it would be nice to check traces in this case too
        traces = self.get_traces()
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

    def get_residual_graph(self):
        return self.hotrunnerdesc.residual_graph

    def check_nothing_compiled_at_all(self):
        assert not hasattr(self.hotrunnerdesc, 'residual_graph')

    def check_insns(self, *args, **kwds):
        if self.translate_support_code:
            return    # XXX it would be nice to check insns in this case too
        test_interpreter.InterpretationTest.check_insns(self, *args, **kwds)

    def check_oops(self, *args, **kwds):
        if self.translate_support_code:
            return    # XXX it would be nice to check insns in this case too
        test_interpreter.InterpretationTest.check_oops(self, *args, **kwds)

    def check_insns_excluding_return(self, expected=None, **counts):
        # the return is currently implemented by a direct_call(exitfnptr)
        if expected is not None:
            expected.setdefault('direct_call', 0)
            expected['direct_call'] += 1
        if 'direct_call' in counts:
            counts['direct_call'] += 1
        self.check_insns(expected, **counts)

    def check_insns_in_loops(self, expected=None, **counts):
        if self.translate_support_code:
            return    # XXX it would be nice to check insns in this case too
        graph = self.get_residual_graph()
        self.insns_in_loops = summary_loops(graph)
        if expected is not None:
            assert self.insns_in_loops == expected
        for opname, count in counts.items():
            assert self.insns_in_loops.get(opname, 0) == count


class TestHotPath(HotPathTest):

    def test_simple_loop(self):
        # there are no greens in this test
        class MyJitDriver(JitDriver):
            greens = []
            reds = ['n1', 'total']

        def ll_function(n):
            n1 = n * 2
            total = 0
            while True:
                MyJitDriver.jit_merge_point(n1=n1, total=total)
                total += n1
                if n1 <= 1:
                    break
                n1 -= 1
                MyJitDriver.can_enter_jit(n1=n1, total=total)
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
            "jit_compile",
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
            "jit_resume Bool path False in ll_function",
            "done at jit_merge_point",
            # execution continues purely in machine code, from the "n1 <= 1"
            # test which triggered the "jit_resume"
            "resume_machine_code",
            # finally, go back to the fallback interp when "n1 <= 1" is True
            "fallback_interp",
            "fb_raise Exit"])

    def test_greens(self):
        class MyJitDriver(JitDriver):
            greens = ['code', 'pc']
            reds = ['accum', 'data', 'buffer']

        def ll_function(code, buffer, data):
            accum = 0
            pc = 0
            while True:
                MyJitDriver.jit_merge_point(code=code, pc=pc, accum=accum,
                                            data=data, buffer=buffer)
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
                        MyJitDriver.can_enter_jit(code=code, pc=pc,
                                                  accum=accum, data=data,
                                                  buffer=buffer)

        def main(demo, arg):
            if demo == 1:
                code = 'RSIS{S*SD}S'    # factorial
            elif demo == 2:
                code = 'ISRDD{ISR%?SDD*}S'  # prime number tester (for arg>=2)
            else:
                raise ValueError
            try:
                ll_function(code, arg, 0)
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
                "jit_compile * struct rpy_string {...} 5",
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
                "jit_resume Bool path True in ll_function",
                "done at jit_merge_point",
            # continue running 100% in the machine code as long as necessary
                "resume_machine_code",
            # at the end, use the fallbac interp to follow the exit path
                "fallback_interp",
                "fb_leave * struct rpy_string {...} 10 0 3628800 10",
            # finally, we interpret the final 'S' character
            # which gives us the final answer
            ])

        res = self.run(main, [2, 127], threshold=3, small=True)
        assert res == 1
        assert len(self.get_traces()) < 20

    def test_simple_return(self):
        class MyJitDriver(JitDriver):
            greens = []
            reds = ['n', 'total']

        def ll_function(n):
            total = 0
            if n <= 0:
                return -1
            while True:
                MyJitDriver.jit_merge_point(n=n, total=total)
                total += n
                if n <= 1:
                    return total
                n -= 1
                MyJitDriver.can_enter_jit(n=n, total=total)

        res = self.run(ll_function, [0], threshold=3, small=True)
        assert res == -1
        self.check_traces([])

        res = self.run(ll_function, [3], threshold=3, small=True)
        assert res == (3*4)/2
        self.check_traces(['jit_not_entered 2 3',
                           'jit_not_entered 1 5'])

        res = self.run(ll_function, [50], threshold=3, small=True)
        assert res == (50*51)/2
        assert len(self.get_traces()) < 20

    def test_hint_errors(self):
        class MyJitDriver(JitDriver):
            greens = []
            reds = ['n']

        def ll_function(n):
            MyJitDriver.jit_merge_point(n=n)
            MyJitDriver.can_enter_jit(foobar=n)
        py.test.raises(JitHintError, self.run, ll_function, [5], 3)

        def ll_function(n):
            MyJitDriver.jit_merge_point(n=n)   # wrong color
            hint(n, concrete=True)
        py.test.raises(JitHintError, self.run, ll_function, [5], 3)

    def test_on_enter_jit(self):
        class MyJitDriver(JitDriver):
            greens = []
            reds = ['n']
            def on_enter_jit(self):
                self.n += 100     # doesn't make sense, just for testing

        def ll_function(n):
            MyJitDriver.jit_merge_point(n=n)
            MyJitDriver.can_enter_jit(n=n)
            return n + 5

        res = self.run(ll_function, [2], threshold=1, small=True)
        assert res == 107
        self.check_traces([
            "jit_compile",
            "done at hp_return",
            "run_machine_code 2",
            ])

    def test_on_enter_jit_many_vars(self):
        class MyJitDriver(JitDriver):
            greens = ['void1', 'm']
            reds = ['void2', 'n']
            def on_enter_jit(self):
                self.n += self.m     # doesn't make sense, just for testing
                # note that the green 'self.m' cannot be modified
                # (changes would not be reloaded into the 'm' var currently)

        def ll_function(n, m):
            MyJitDriver.jit_merge_point(n=n, m=m, void1=None, void2=None)
            MyJitDriver.can_enter_jit(n=n, m=m, void1=None, void2=None)
            hint(m, concrete=True)
            return n + 5

        res = self.run(ll_function, [2, 200], threshold=1, small=True)
        assert res == 207
        self.check_traces([
            "jit_compile 200",
            "done at hp_return",
            "run_machine_code 200 2",
            ])

    def test_hp_tlr(self):
        from pypy.jit.tl import tlr

        def main(code, n):
            if code == 1:
                bytecode = tlr.SQUARE
            else:
                bytecode = chr(tlr.RETURN_A)
            return tlr.hp_interpret(bytecode, n)

        res = self.run(main, [1, 71], threshold=3)
        assert res == 5041
        self.check_traces([
            "jit_not_entered * stru...} 10 70 * array [ 70, 71, 71 ]",
            "jit_not_entered * stru...} 10 69 * array [ 69, 71, 142 ]",
            "jit_compile * stru...} 10",
        # we first see the promotion of len(regs) in on_enter_jit()
            "pause at promote in TLRJitDriver.on_enter_jit_Hv",
        # followed by two fallback runs
            "run_machine_code * stru...} 10 68 * array [ 68, 71, 213 ]",
            "fallback_interp",
            "fb_leave * stru...} 10 68 * array [ 68, 71, 213 ]",
            "run_machine_code * stru...} 10 67 * array [ 67, 71, 284 ]",
            "fallback_interp",
            "fb_leave * stru...} 10 67 * array [ 67, 71, 284 ]",
        # the third time, we resume compiling for len(regs) == 3
            "run_machine_code * stru...} 10 66 * array [ 66, 71, 355 ]",
            "jit_resume Signed path 3 in TLRJitDriver.on_enter_jit_Hv",
        # pause at the "int_is_true" from the JUMP_IF_A opcode
            "pause at hotsplit in hp_interpret",
        # two fallback runs off this hotsplit
            "resume_machine_code",
            "fallback_interp",
            "fb_leave * stru...} 10 65 * array [ 65, 71, 426 ]",
            "run_machine_code * stru...} 10 65 * array [ 65, 71, 426 ]",
            "fallback_interp",
            "fb_leave * stru...} 10 64 * array [ 64, 71, 497 ]",
        # the third time, compile the path "stay in the loop"
            "run_machine_code * stru...} 10 64 * array [ 64, 71, 497 ]",
            "jit_resume Bool path True in hp_interpret",
            "done at jit_merge_point",
        # the rest is running 100% in machine code
            "resume_machine_code",
        # fallback interp for the exit path
            "fallback_interp",
            "fb_leave * stru...} 27 0 * array [ 0, 71, 5041 ]",
            ])
        # check that the residual graph's inner loop has no direct_call (as
        # would be the case if the 'regs' list was not properly virtualized)
        self.check_insns_in_loops({'int_add': 2,
                                   'int_is_true': 1})

    def test_hp_tiny2(self):
        from pypy.jit.tl.tiny2_hotpath import interpret, FACTORIAL, FIBONACCI_SINGLE
        from pypy.jit.tl.tiny2_hotpath import IntBox, StrBox, repr
        from pypy.jit.tl.targettiny2hotpath import MyHintAnnotatorPolicy

        def main(case, n):
            if case == 1:
                bytecode = FACTORIAL
                args = [IntBox(n)]
            elif case == 2:
                bytecode = FIBONACCI_SINGLE
                args = [IntBox(1), IntBox(1), IntBox(n)]
            elif case == 3:
                bytecode = "{ #1 #1 1 SUB ->#1 #1 }".split(" ")
                args = [StrBox(str(n))]
            else:
                assert 0, "unknown case"
            stack = interpret(bytecode, args)
            return repr(stack)

        POLICY = MyHintAnnotatorPolicy()
        #res = self.run(main, [1, 11], threshold=2, policy=POLICY)
        #assert ''.join(res.chars) == "The factorial of 11 is 39916800"
        # nothing is forced
        self.check_insns_in_loops(malloc=0)

        res = self.run(main, [2, 20], threshold=2, policy=POLICY)
        assert ''.join(res.chars) == "6765"
        self.check_insns_in_loops(malloc=0)

        res = self.run(main, [3, 40], threshold=10, policy=POLICY)
        assert ''.join(res.chars) == " ".join([str(n) for n in range(40, 0, -1)])
        # XXX should check something about the produced code as well, but no
        # clue what

    def test_loop_with_more_and_more_structs(self):
        py.test.skip("shows problem with current merging logic")
        class MyJitDriver(JitDriver):
            greens = []
            reds = ['n1', 'res']

        class List(object):
            def __init__(self, value, prev):
                self.value = value
                self.prev = prev

        def ll_function(n):
            n1 = n * 2
            res = None
            while True:
                MyJitDriver.jit_merge_point(n1=n1, res=res)
                if n1 <= 1:
                    break
                n1 -= 1
                res = List(n1, res)
                MyJitDriver.can_enter_jit(n1=n1, res=res)
            final = []
            while res:
                final.append(str(res.value))
                res = res.prev
            return " ".join(final)
        res = self.run(ll_function, [40], threshold=2)
        assert "".join(res.chars) == " ".join([str(i) for i in range(1, 80)])
        self.check_insns(malloc=1)
