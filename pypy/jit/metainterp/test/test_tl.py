import py
from pypy.rlib.jit import JitDriver
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

    def setup_class(cls):
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

        code2 = compile('''
                PUSHARG
            start:
                PUSH 1
                SUB
                PICK 0
                PUSH 1
                LE
                BR_COND exit
                PUSH 1
                BR_COND start
            exit:
                RETURN
        ''')
        
        codes = [code, code2]
        def main(n, inputarg):
            code = codes[n]
            return interp_without_call(code, inputarg=inputarg)
        cls.main = main

    def test_tl_base(self):
        res = self.meta_interp(self.main.im_func, [0, 6], listops=True)
        assert res == 5040
        self.check_loops({'merge_point':1,
                          'int_mul':1, 'jump':1,
                          'int_sub':1, 'int_is_true':1, 'int_le':1,
                          'guard_false':1, 'guard_value':1})

    def test_tl_2(self):
        res = self.meta_interp(self.main.im_func, [1, 10], listops=True)
        assert res == self.main.im_func(1, 10)
        self.check_loops({'merge_point':1, 'int_sub':1, 'int_le':1,
                         'int_is_true':1, 'guard_false':1, 'jump':1,
                          'guard_value':1})

    def test_example(self):
        jitdriver = JitDriver(greens = ['code', 'i'], reds = ['v1', 'v2', 'v3'])
        
        class IntObject(object):
            def __init__(self, value):
                self.value = value

            def add(self, other):
                return IntObject(self.value + other.value)

            def gt(self, other):
                return self.value > other.value

        def store_into_variable(num, v1, v2, v3, value_to_store):
            if num == 0:
                return value_to_store, v2, v3
            elif num == 1:
                return v1, value_to_store, v3
            elif num == 2:
                return v1, v2, value_to_store
            else:
                raise Exception("Wrong num")

        def load_variable(num, v1, v2, v3):
            if num == 0:
                return v1
            elif num == 1:
                return v2
            elif num == 2:
                return v3
            else:
                raise Exception("Wrong num")

        def interpret(code, i0, i1, i2):
            v1 = IntObject(i0)
            v2 = IntObject(i1)
            v3 = IntObject(i2)
            i = 0
            while i < len(code):
                jitdriver.jit_merge_point(code=code, i=i, v1=v1, v2=v2, v3=v3)
                if code[i] == ADD:
                    a = load_variable(code[i + 1], v1, v2, v3)
                    b = load_variable(code[i + 2], v1, v2, v3)
                    res_num = code[i + 3]
                    res = a.add(b)
                    v1, v2, v3 = store_into_variable(res_num, v1, v2, v3,
                                                     res)
                    i += 4
                elif code[i] == JUMP_IF_GT:
                    a = load_variable(code[i + 1], v1, v2, v3)
                    b = load_variable(code[i + 2], v1, v2, v3)
                    where = code[i + 3]
                    if a.gt(b):
                        i = where
                        jitdriver.can_enter_jit(code=code, i=i, v1=v1, v2=v2,
                                                v3=v3)
                    else:
                        i += 4
                elif code[i] == JUMP:
                    i = code[i + 1]
                    jitdriver.can_enter_jit(code=code, i=i, v1=v1, v2=v2, v3=v3)
                else:
                    raise Exception("bytecode corruption")
            return v1.value

        ADD = 0
        JUMP = 1
        JUMP_IF_GT = 2

        code = [
            ADD, 0, 1, 0,
            ADD, 0, 1, 0,
            ADD, 0, 1, 0,
            JUMP_IF_GT, 0, 2, 18,
            JUMP, 0
        ]

        # v0 += v1
        # v0 += v1
        # v0 += v1
        # if v1 > v2: jump 18 (after the end of the loop)
        # jump 0

        def runner(num, i0, i1, i2):
            return interpret([code, []][num], i0, i1, i2)

        assert interpret(code, 0, 1, 20) == 21
        res = self.meta_interp(runner, [0, 0, 1, 20])
        assert res == 21

class TestOOtype(ToyLanguageTests, OOJitMixin):
    pass

class TestLLtype(ToyLanguageTests, LLJitMixin):
    pass
