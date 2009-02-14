import py
from pypy.rlib.jit import JitDriver, hint
from pypy.jit.metainterp.policy import StopAtXPolicy
from pypy.jit.metainterp.test.test_basic import OOJitMixin, LLJitMixin


class ToyLanguageTests:

    def test_tiny1(self):
        myjitdriver = JitDriver(greens = ['s', 'pc'],
                                reds = ['y', 'acc'])

        def ll_plus_minus(s, x, y):
            acc = x
            pc = 0
            while pc < len(s):
                myjitdriver.can_enter_jit(y=y, pc=pc, acc=acc, s=s)
                myjitdriver.jit_merge_point(y=y, pc=pc, acc=acc, s=s)
                op = s[pc]
                if op == '+':
                    acc += y
                elif op == '-':
                    acc -= y
                pc += 1
            return acc

        codes = ["++++++++++", "+-++---+-++-"]
        def main(n, x, y):
            code = codes[n]
            return ll_plus_minus(code, x, y)

        res = self.meta_interp(main, [0, 100, 2])
        assert res == 120

    def test_tlr(self):
        from pypy.jit.tl.tlr import interpret, SQUARE

        codes = ["", SQUARE]
        def main(n, a):
            code = codes[n]
            return interpret(code, a)

        res = self.meta_interp(main, [1, 10])
        assert res == 100

    def test_tl_base(self):
        from pypy.jit.tl.tl import interp_without_call
        from pypy.jit.tl.tlopcode import compile

        code = compile('''
                PUSH 1   #  accumulator
                PUSH 7   #  N

            start:
                PICK 0
                PUSH 1
                LE
                BR_COND exit

                SWAP
                PICK 1
                MUL
                SWAP
                PUSH 1
                SUB
                PUSH 1
                BR_COND start

            exit:
                POP
                RETURN
        ''')
        
        codes = ["", code]
        def main(n, inputarg):
            code = codes[n]
            return interp_without_call(code, inputarg=inputarg)

        res = self.meta_interp(main, [1, 6])
        # we could eventually get away without setitems at all I think
        # we're missing once guard_no_exception at the end I think
        self.check_loops({'merge_point':1, 'guard_value':1, 'getitem':2,
                          'setitem':4, 'guard_no_exception':2, 'int_mul':1,
                          'int_sub':1, 'int_is_true':1, 'int_le':1,
                          'guard_false':1})
        assert res == 5040


class TestOOtype(ToyLanguageTests, OOJitMixin):
    pass

class TestLLtype(ToyLanguageTests, LLJitMixin):
    pass
