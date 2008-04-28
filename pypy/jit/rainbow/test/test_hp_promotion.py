import py
from pypy.rpython.lltypesystem import lltype
from pypy.rlib.jit import JitDriver, hint, JitHintError
from pypy.jit.rainbow.test import test_hotpath


class TestHotPromotion(test_hotpath.HotPathTest):

    def interpret(self, main, ll_values, opt_consts=[]):
        py.test.skip("fix this test")
    def interpret_raises(self, Exception, main, ll_values, opt_consts=[]):
        py.test.skip("fix this test")

    def test_easy_case(self):
        myjitdriver = JitDriver(greens = ['n'],
                                reds = [])
        def ll_two(k):
            return (k+1)*2
        def ll_function(n):
            myjitdriver.jit_merge_point(n=n)
            myjitdriver.can_enter_jit(n=n)
            hint(n, concrete=True)
            n = hint(n, variable=True)     # n => constant red box
            k = hint(n, promote=True)      # no-op
            k = ll_two(k)
            return hint(k, variable=True)

        res = self.run(ll_function, [20], threshold=1)
        assert res == 42
        self.check_insns_excluding_return({})

    def test_simple_promotion(self):
        myjitdriver = JitDriver(greens = [],
                                reds = ['n'])
        def ll_two(k):
            return (k+1)*2
        def ll_function(n):
            myjitdriver.jit_merge_point(n=n)
            myjitdriver.can_enter_jit(n=n)
            k = hint(n, promote=True)
            k = ll_two(k)
            return hint(k, variable=True)

        res = self.run(ll_function, [20], threshold=1)
        assert res == 42
        self.check_insns(int_add=0, int_mul=0)

    def test_many_promotions(self):
        myjitdriver = JitDriver(greens = [],
                                reds = ['n', 'total'])
        def ll_two(k):
            return k*k
        def ll_function(n, total):
            while n > 0:
                myjitdriver.jit_merge_point(n=n, total=total)
                myjitdriver.can_enter_jit(n=n, total=total)
                k = hint(n, promote=True)
                k = ll_two(k)
                total += hint(k, variable=True)
                n -= 1
            return total

        res = self.run(ll_function, [10, 0], threshold=1)
        assert res == ll_function(10, 0)
        self.check_insns(int_add=10, int_mul=0)

        # the same using the fallback interp instead of compiling each case
        res = self.run(ll_function, [10, 0], threshold=3)
        assert res == ll_function(10, 0)
        self.check_insns(int_add=0, int_mul=0)
        self.check_traces([
            "jit_not_entered 10 0",
            "jit_not_entered 9 100",
            "jit_compile",
            "pause at promote in ll_function",
            "run_machine_code 8 181", "fallback_interp", "fb_leave 7 245",
            "run_machine_code 7 245", "fallback_interp", "fb_leave 6 294",
            "run_machine_code 6 294", "fallback_interp", "fb_leave 5 330",
            "run_machine_code 5 330", "fallback_interp", "fb_leave 4 355",
            "run_machine_code 4 355", "fallback_interp", "fb_leave 3 371",
            "run_machine_code 3 371", "fallback_interp", "fb_leave 2 380",
            "run_machine_code 2 380", "fallback_interp", "fb_leave 1 384",
            "run_machine_code 1 384", "fallback_interp", "fb_return 385"
            ])

    def test_promote_after_call(self):
        myjitdriver = JitDriver(greens = [],
                                reds = ['n'])
        S = lltype.GcStruct('S', ('x', lltype.Signed))
        def ll_two(k, s):
            if k > 5:
                s.x = 20
            else:
                s.x = k
        def ll_function(n):
            myjitdriver.jit_merge_point(n=n)
            myjitdriver.can_enter_jit(n=n)
            s = lltype.malloc(S)
            ll_two(n, s)
            k = hint(n, promote=True)
            k *= 17
            return hint(k, variable=True) + s.x

        res = self.run(ll_function, [4], threshold=1)
        assert res == 4*17 + 4
        self.check_insns(int_mul=0, int_add=0)

    def test_promote_after_yellow_call(self):
        myjitdriver = JitDriver(greens = [],
                                reds = ['n', 'i'])
        S = lltype.GcStruct('S', ('x', lltype.Signed))
        def ll_two(k, s):
            if k > 5:
                s.x = 20*k
                return 7
            else:
                s.x = 10*k
                return 9
            
        def ll_function(n):
            i = 10
            while i > 0:
                i -= 1
                myjitdriver.jit_merge_point(n=n, i=i)
                myjitdriver.can_enter_jit(n=n, i=i)
                s = lltype.malloc(S)
                c = ll_two(n, s)
                k = hint(s.x, promote=True)
                k += c
                res = hint(k, variable=True)
            return res

        res = self.run(ll_function, [4], threshold=2)
        assert res == 49
        self.check_insns(int_add=0)

    def test_promote_inside_call(self):
        myjitdriver = JitDriver(greens = [],
                                reds = ['n', 'i'])
        def ll_two(n):
            k = hint(n, promote=True)
            k *= 17
            return hint(k, variable=True)
        def ll_function(n):
            i = 1024
            while i > 0:
                i >>= 1
                myjitdriver.jit_merge_point(n=n, i=i)
                myjitdriver.can_enter_jit(n=n, i=i)
                res = ll_two(n + 1) - 1
            return res

        res = self.run(ll_function, [10], threshold=2)
        assert res == 186
        self.check_insns(int_add=1, int_mul=0, int_sub=0)

    def test_promote_inside_call2(self):
        myjitdriver = JitDriver(greens = [],
                                reds = ['n', 'm', 'i'])
        def ll_two(n):
            k = hint(n, promote=True)
            k *= 17
            return k
        def ll_function(n, m):
            i = 1024
            while i > 0:
                i >>= 1
                myjitdriver.jit_merge_point(n=n, m=m, i=i)
                myjitdriver.can_enter_jit(n=n, m=m, i=i)
                if not n:
                    return -41
                if m:
                    res = 42
                else:
                    res = ll_two(n + 1) - 1
            return res

        res = self.run(ll_function, [10, 0], threshold=2)
        assert res == 186
        self.check_insns(int_add=1, int_mul=0, int_sub=0)

        res = self.run(ll_function, [0, 0], threshold=2)
        assert res == -41
        self.check_nothing_compiled_at_all()

        res = self.run(ll_function, [1, 1], threshold=2)
        assert res == 42
        self.check_insns_in_loops({'int_is_true': 2,
                                   'int_gt': 1,
                                   'int_rshift': 1})

    def test_two_promotions(self):
        myjitdriver = JitDriver(greens = [],
                                reds = ['n', 'm', 'i'])
        def ll_function(n, m):
            i = 1024
            while i > 0:
                i >>= 1
                myjitdriver.jit_merge_point(n=n, m=m, i=i)
                myjitdriver.can_enter_jit(n=n, m=m, i=i)
                n1 = hint(n, promote=True)
                m1 = hint(m, promote=True)
                s1 = n1 + m1
                res = hint(s1, variable=True)
            return res

        res = self.run(ll_function, [40, 2], threshold=2)
        assert res == 42
        self.check_insns(int_add=0)

    def test_merge_then_promote(self):
        S = lltype.GcStruct('S', ('x', lltype.Signed))
        def ll_two(n):
            s = lltype.malloc(S)
            if n < 0:
                s.x = 10
            else:
                s.x = 20
            k = hint(s.x, promote=True)
            k *= 17
            return hint(k, variable=True)
        def ll_function(n):
            hint(None, global_merge_point=True)
            return ll_two(n)

        res = self.interpret(ll_function, [3])
        assert res == 340
        self.check_insns(int_lt=1, int_mul=0)

    def test_vstruct_unfreeze(self):
        S = lltype.GcStruct('S', ('x', lltype.Signed))
        def ll_two(k):
            return (k+1)*2
        def ll_function(n):
            hint(None, global_merge_point=True)
            s = lltype.malloc(S)
            s.x = n
            k = hint(n, promote=True)
            k = ll_two(k)
            return hint(k, variable=True) + s.x

        # easy case: no promotion needed
        res = self.interpret(ll_function, [20], [0])
        assert res == 62
        self.check_insns({})

        # the real test: with promotion
        res = self.interpret(ll_function, [20])
        assert res == 62
        self.check_insns(int_add=0, int_mul=0)

    def test_more_promotes(self):
        myjitdriver = JitDriver(greens = [],
                                reds = ['n', 'm', 'i', 's'])
        S = lltype.GcStruct('S', ('x', lltype.Signed), ('y', lltype.Signed))
        def ll_two(s, i, m):
            if i > 4:
                s.x += i
                return 10
            else:
                s.y = i
                return s.x + m
        def ll_three(s, k):
            k = hint(k, promote=True)
            if s.x > 6:
                k *= hint(s.y, promote=True)
                return k
            else:
                return hint(1, concrete=True)
        def ll_function(n, m):
            s = lltype.malloc(S)
            s.x = 0
            s.y = 0
            i = 0
            while i < n:
                myjitdriver.jit_merge_point(n=n, m=m, i=i, s=s)
                myjitdriver.can_enter_jit(n=n, m=m, i=i, s=s)
                k = ll_two(s, i, m)
                if m & 1:
                    k *= 3
                else:
                    s.y += 1
                j = ll_three(s, k)
                j = hint(j, variable=True)
                i += j
            return s.x + s.y * 17

        res = self.run(ll_function, [100, 2], threshold=3)
        assert res == ll_function(100, 2)

    def test_mixed_merges(self):
        def ll_function(x, y, z, k):
            if x:
               while x > 0:
                   hint(None, global_merge_point=True)
                   if y < 0:
                       y = -y
                       hint(None, reverse_split_queue=True)
                       return y
                   else:
                       n = 10
                       while n:
                           n -= 1
                       y = hint(y, promote=True)
                       y *= 2
                       y = hint(y, variable=True)
                   x -= 1
            else:
                if z < 0:
                    z = -z
                else:
                    k = 3
                y = y + z*k
            return y

        res = self.interpret(ll_function, [6, 3, 2, 2], [3])

        assert res == ll_function(6, 3, 2, 2)

    def test_green_across_global_mp(self):
        myjitdriver = JitDriver(greens = ['n1', 'n2'],
                                reds = ['total', 'n3', 'n4'])
        def ll_function(n1, n2, n3, n4, total):
            while n2:
                myjitdriver.jit_merge_point(n1=n1, n2=n2, n3=n3, n4=n4,
                                            total=total)
                myjitdriver.can_enter_jit(n1=n1, n2=n2, n3=n3, n4=n4,
                                          total=total)
                total += n4
                total *= n2
                hint(n3, concrete=True)
                hint(n2, concrete=True)
                hint(n1, concrete=True)
                n2 -= 1
            return total
        def main(n2, n4, total):
            return ll_function(None, n2, None, n4, total)

        if not self.translate_support_code:
            # one case is enough if translating the support code
            res = self.run(main, [7, 3, 100], threshold=2)
            assert res == main(7, 3, 100)

        res = self.run(main, [7, 3, 100], threshold=1)
        assert res == main(7, 3, 100)

    def test_remembers_across_mp(self):
        def ll_function(x, flag):
            hint(None, global_merge_point=True)
            hint(x.field, promote=True)
            m = x.field
            if flag:
                m += 1 * flag
            else:
                m += 2 + flag
            hint(x.field, promote=True)
            return m + x.field

        S = lltype.GcStruct('S', ('field', lltype.Signed),
                            hints={'immutable': True})

        def struct_S(string):
            s = lltype.malloc(S)
            s.field = int(string)
            return s
        ll_function.convert_arguments = [struct_S, int]

        res = self.interpret(ll_function, ["20", 0])
        assert res == 42
        self.check_flexswitches(1)

    def test_virtual_list_copy(self):
        myjitdriver = JitDriver(greens = [],
                                reds = ['x', 'y', 'repeat'])
        def ll_function(x, y):
            repeat = 10
            while repeat > 0:
                repeat -= 1
                myjitdriver.jit_merge_point(x=x, y=y, repeat=repeat)
                myjitdriver.can_enter_jit(x=x, y=y, repeat=repeat)
                l = [y] * x
                size = len(l)
                size = hint(size, promote=True)
                vl = [0] * size
                i = 0
                while i < size:
                    hint(i, concrete=True)
                    vl[i] = l[i]
                    i = i + 1
                res = len(vl)
            return res
        res = self.run(ll_function, [6, 11], threshold=2)
        assert res == 6
        self.check_oops(**{'newlist': 1, 'list.len': 1})
            
    def test_promote_bug_1(self):
        def ll_function(x, y, z):
            a = 17
            while True:
                hint(None, global_merge_point=True)
                y += 1

                if a != 17:
                    z = -z
                
                if z > 0:
                    b = 1 - z
                else:
                    b = 2
                y = -y
                if b == 2:
                    hint(z, promote=True)
                    return y + z + a
                a += z

        assert ll_function(1, 5, 8) == 22
        res = self.interpret(ll_function, [1, 5, 8])
        assert res == 22

    def test_raise_result_mixup(self):
        py.test.skip("convert_arguments not supported")
        def w(x):
            pass
        class E(Exception):
            def __init__(self, x):
                self.x = x
        def o(x):
            if x < 0:
                e = E(x)
                w(e)
                raise e                
            return x
        def ll_function(c, x):
            i = 0
            while True:
                hint(None, global_merge_point=True)
                op = c[i]
                hint(op, concrete=True)
                if op == 'e':
                    break
                elif op == 'o':
                    x = o(x)
                    x = hint(x, promote=True)
                    i = x
            r = hint(i, variable=True)
            return r
        ll_function.convert_arguments = [LLSupport.to_rstr, int]
        
        assert ll_function("oe", 1) == 1

        res = self.interpret(ll_function, ["oe", 1], [],
                             policy=StopAtXPolicy(w))
        res == 1

    def test_raise_result_mixup_some_more(self):
        py.test.skip("convert_arguments not supported")
        def w(x):
            if x > 1000:
                return None
            else:
                return E(x)
        class E(Exception):
            def __init__(self, x):
                self.x = x
        def o(x):
            if x < 0:
                e = w(x)
                raise e                
            return x
        def ll_function(c, x):
            i = 0
            while True:
                hint(None, global_merge_point=True)
                op = c[i]
                hint(op, concrete=True)
                if op == 'e':
                    break
                elif op == 'o':
                    x = o(x)
                    x = hint(x, promote=True)
                    i = x
            r = hint(i, variable=True)
            return r
        ll_function.convert_arguments = [LLSupport.to_rstr, int]
        
        assert ll_function("oe", 1) == 1

        res = self.interpret(ll_function, ["oe", 1], [],
                             policy=StopAtXPolicy(w))
        res == 1

    def test_exception_after_promotion(self):
        def ll_function(n, m):
            hint(None, global_merge_point=True)
            hint(m, promote=True)
            if m == 0:
                raise ValueError
            return n
        self.interpret_raises(ValueError, ll_function, [1, 0])

    def test_promote_in_yellow_call(self):
        def ll_two(n):
            n = hint(n, promote=True)
            return n + 2
            
        def ll_function(n):
            hint(None, global_merge_point=True)
            c = ll_two(n)
            return hint(c, variable=True)

        res = self.interpret(ll_function, [4])
        assert res == 6
        self.check_insns(int_add=0)

    def test_more_promote_in_yellow_call(self):
        def ll_two(n):
            n = hint(n, promote=True)
            return n + 2
            
        def ll_function(n):
            hint(None, global_merge_point=True)
            if n > 5:
                c = n
            else:
                c = ll_two(n)
            return hint(c, variable=True)

        res = self.interpret(ll_function, [4])
        assert res == 6
        self.check_insns(int_add=0)

    def test_two_promotions_in_call(self):
        def ll_two(n, m):
            if n < 1:
                return m
            else:
                return n

        def ll_one(n, m):
            n = ll_two(n, m)
            n = hint(n, promote=True)
            m = hint(m, promote=True)
            return hint(n + m, variable=True)

        def ll_function(n, m):
            hint(None, global_merge_point=True)
            c = ll_one(n, m)
            return c

        res = self.interpret(ll_function, [4, 7])
        assert res == 11
        self.check_insns(int_add=0)
