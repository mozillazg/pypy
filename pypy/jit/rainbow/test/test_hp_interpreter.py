import py
from pypy.rpython.lltypesystem import lltype
from pypy.rlib.jit import JitDriver, hint, JitHintError
from pypy.rlib.debug import ll_assert
from pypy.rlib.objectmodel import keepalive_until_here
from pypy.jit.hintannotator.policy import HintAnnotatorPolicy, StopAtXPolicy
from pypy.jit.rainbow.test import test_hotpath
from pypy.rlib.rarithmetic import ovfcheck

import sys

# ------------------------------------------------------------------------
# A note about these tests.  Their portal function is generally structured
# like this:
#
#    i = 1024
#    while i > 0:
#        i >>= 1
#        ...real test code here...
#        MyJitDriver.jit_merge_point(...)
#        MyJitDriver.can_enter_jit(...)
#
# and we use a threshold of 2, typically.  This ensures that in a single
# call, the test code is run in all three ways:
#  - first it runs directly
#  - then we start the JIT but immediately pause at the 'i > 0' check,
#      so that the real test code runs in the fallback interp
#  - then we JIT everything
# ------------------------------------------------------------------------


class TestHotInterpreter(test_hotpath.HotPathTest):

    def test_loop_convert_const_to_redbox(self):
        class MyJitDriver(JitDriver):
            greens = ['x']
            reds = ['y', 'tot']
        def ll_function(x, y):
            tot = 0
            while x:    # conversion from green '0' to red 'tot'
                hint(x, concrete=True)
                tot += y
                x -= 1
                MyJitDriver.jit_merge_point(x=x, y=y, tot=tot)
                MyJitDriver.can_enter_jit(x=x, y=y, tot=tot)
            return tot

        res = self.run(ll_function, [7, 2], threshold=1)
        assert res == 14
        self.check_insns_excluding_return({'int_add': 6})

    def test_ifs(self):
        class MyJitDriver(JitDriver):
            greens = ['green']
            reds = ['x', 'y', 'i']
        def f(green, x, y):
            i = 1024
            while i > 0:
                i >>= 1
                MyJitDriver.jit_merge_point(green=green, x=x, y=y, i=i)
                MyJitDriver.can_enter_jit(green=green, x=x, y=y, i=i)
                green = hint(green, concrete=True)
                if x:                # red if, and compiling pause
                    res = 100
                else:
                    res = 1
                if y > 5:            # red if
                    res += 50
                if green:            # green if
                    res *= x + y
                else:
                    res *= x - y
            return res
        for g in [0, 1]:
            for x in [0, 1]:
                for y in [4, 77]:
                    res = self.run(f, [g, x, y], threshold=3)
                    assert res == f(g, x, y)

    def test_simple_opt_const_propagation2(self):
        class MyJitDriver(JitDriver):
            greens = ['x', 'y']
            reds = []
        def ll_function(x, y):
            MyJitDriver.jit_merge_point(x=x, y=y)
            MyJitDriver.can_enter_jit(x=x, y=y)
            hint(x, concrete=True)
            hint(y, concrete=True)
            x = hint(x, variable=True)
            y = hint(y, variable=True)
            return x + (-y)
        res = self.run(ll_function, [5, -7], threshold=2)
        assert res == 12
        self.check_nothing_compiled_at_all()
        res = self.run(ll_function, [5, -7], threshold=1)
        assert res == 12
        self.check_insns_excluding_return({})

    def test_loop_folding(self):
        class MyJitDriver(JitDriver):
            greens = ['x', 'y']
            reds = []
        def ll_function(x, y):
            MyJitDriver.jit_merge_point(x=x, y=y)
            MyJitDriver.can_enter_jit(x=x, y=y)
            hint(x, concrete=True)
            hint(y, concrete=True)
            x = hint(x, variable=True)
            y = hint(y, variable=True)
            tot = 0
            while x:
                tot += y
                x -= 1
            return tot
        res = self.run(ll_function, [7, 2], threshold=2)
        assert res == 14
        self.check_nothing_compiled_at_all()
        res = self.run(ll_function, [7, 2], threshold=1)
        assert res == 14
        self.check_insns_excluding_return({})

    def test_loop_merging(self):
        def ll_function(x, y):
            tot = 0
            while x:
                tot += y
                x -= 1
            return tot
        res = self.interpret(ll_function, [7, 2], [])
        assert res == 14
        self.check_insns(int_add = 2,
                         int_is_true = 2)

        res = self.interpret(ll_function, [7, 2], [0])
        assert res == 14
        self.check_insns(int_add = 2,
                         int_is_true = 1)

        res = self.interpret(ll_function, [7, 2], [1])
        assert res == 14
        self.check_insns(int_add = 1,
                         int_is_true = 2)

        res = self.interpret(ll_function, [7, 2], [0, 1])
        assert res == 14
        self.check_insns(int_add = 1,
                         int_is_true = 1)

    def test_loop_merging2(self):
        def ll_function(x, y):
            tot = 0
            while x:
                if tot < 3:
                    tot *= y
                else:
                    tot += y
                x -= 1
            return tot
        res = self.interpret(ll_function, [7, 2])
        assert res == 0

    def test_two_loops_merging(self):
        def ll_function(x, y):
            tot = 0
            while x:
                tot += y
                x -= 1
            while y:
                tot += y
                y -= 1
            return tot
        res = self.interpret(ll_function, [7, 3], [])
        assert res == 27
        self.check_insns(int_add = 3,
                         int_is_true = 3)

    def test_convert_greenvar_to_redvar(self):
        def ll_function(x, y):
            hint(x, concrete=True)
            return x - y
        res = self.interpret(ll_function, [70, 4], [0])
        assert res == 66
        self.check_insns(int_sub = 1)
        res = self.interpret(ll_function, [70, 4], [0, 1])
        assert res == 66
        self.check_insns({})

    def test_green_across_split(self):
        def ll_function(x, y):
            hint(x, concrete=True)
            if y > 2:
                z = x - y
            else:
                z = x + y
            return z
        res = self.interpret(ll_function, [70, 4], [0])
        assert res == 66
        self.check_insns(int_add = 1,
                         int_sub = 1)

    def test_merge_const_before_return(self):
        def ll_function(x):
            if x > 0:
                y = 17
            else:
                y = 22
            x -= 1
            y += 1
            return y+x
        res = self.interpret(ll_function, [-70], [])
        assert res == 23-71
        self.check_insns({'int_gt': 1, 'int_add': 2, 'int_sub': 2})

    def test_merge_3_redconsts_before_return(self):
        def ll_function(x):
            if x > 2:
                y = hint(54, variable=True)
            elif x > 0:
                y = hint(17, variable=True)
            else:
                y = hint(22, variable=True)
            x -= 1
            y += 1
            return y+x
        res = self.interpret(ll_function, [-70], [])
        assert res == ll_function(-70)
        res = self.interpret(ll_function, [1], [])
        assert res == ll_function(1)
        res = self.interpret(ll_function, [-70], [])
        assert res == ll_function(-70)

    def test_merge_const_at_return(self):
        def ll_function(x):
            if x > 0:
                return 17
            else:
                return 22
        res = self.interpret(ll_function, [-70], [])
        assert res == 22
        self.check_insns({'int_gt': 1})

    def test_arith_plus_minus(self):
        class MyJitDriver(JitDriver):
            greens = ['encoded_insn', 'nb_insn']
            reds = ['i', 'x', 'y', 'acc']
        def ll_plus_minus(encoded_insn, nb_insn, x, y):
            i = 1024
            while i > 0:
                i >>= 1
                hint(nb_insn, concrete=True)
                acc = x
                pc = 0
                while pc < nb_insn:
                    op = (encoded_insn >> (pc*4)) & 0xF
                    op = hint(op, concrete=True)
                    if op == 0xA:
                        acc += y
                    elif op == 0x5:
                        acc -= y
                    pc += 1
                MyJitDriver.jit_merge_point(encoded_insn=encoded_insn,
                                            nb_insn=nb_insn, x=x, y=y, i=i,
                                            acc=acc)
                MyJitDriver.can_enter_jit(encoded_insn=encoded_insn,
                                          nb_insn=nb_insn, x=x, y=y, i=i,
                                          acc=acc)
            return acc
        assert ll_plus_minus(0xA5A, 3, 32, 10) == 42
        res = self.run(ll_plus_minus, [0xA5A, 3, 32, 10], threshold=2)
        assert res == 42
        self.check_insns_in_loops({'int_add': 2, 'int_sub': 1,
                                   'int_gt': 1, 'int_rshift': 1})

    def test_call_3(self):
        class MyJitDriver(JitDriver):
            greens = []
            reds = ['i', 'y', 'res']
        def ll_add_one(x):
            return x + 1
        def ll_two(x):
            return ll_add_one(ll_add_one(x)) - x
        def ll_function(y):
            i = 1024
            while i > 0:
                i >>= 1
                res = ll_two(y) * y
                MyJitDriver.jit_merge_point(y=y, i=i, res=res)
                MyJitDriver.can_enter_jit(y=y, i=i, res=res)
            return res
        res = self.run(ll_function, [5], threshold=2)
        assert res == 10
        self.check_insns_in_loops({'int_add': 2, 'int_sub': 1, 'int_mul': 1,
                                   'int_gt': 1, 'int_rshift': 1})

    def test_call_mixed_color_args(self):
        class MyJitDriver(JitDriver):
            greens = ['g1', 'g2']
            reds = ['r1', 'r2', 'i', 'res']

        def ll_grr(a, b, c): return a + 3*b + 7*c
        def ll_rgr(a, b, c): return a + 3*b + 7*c
        def ll_rrg(a, b, c): return a + 3*b + 7*c
        def ll_ggr(a, b, c): return a + 3*b + 7*c
        def ll_grg(a, b, c): return a + 3*b + 7*c
        def ll_rgg(a, b, c): return a + 3*b + 7*c
        
        def ll_function(g1, g2, r1, r2):
            i = 1024
            while i > 0:
                i >>= 1
                res = (ll_grr(g1, r1, r2) * 1 +
                       ll_rgr(r1, g2, r2) * 10 +
                       ll_rrg(r2, r1, g1) * 100 +
                       ll_ggr(g1, g2, r2) * 1000 +
                       ll_grg(g2, r2, g1) * 10000 +
                       ll_rgg(r1, g2, g1) * 100000)
                hint(g1, concrete=True)
                hint(g2, concrete=True)
                MyJitDriver.jit_merge_point(g1=g1, g2=g2, r1=r1, r2=r2,
                                            i=i, res=res)
                MyJitDriver.can_enter_jit(g1=g1, g2=g2, r1=r1, r2=r2,
                                          i=i, res=res)
            return res
        res = self.run(ll_function, [1, 2, 4, 8], threshold=2)
        assert res == ll_function(1, 2, 4, 8)

    def test_void_call(self):
        class MyJitDriver(JitDriver):
            greens = []
            reds = ['y', 'i']
        S = lltype.GcStruct('S', ('x', lltype.Signed))
        def ll_do_nothing(s, x):
            s.x = x + 1
        def ll_function(y):
            i = 1024
            while i > 0:
                i >>= 1
                s = lltype.malloc(S)
                ll_do_nothing(s, y)
                y = s.x
                MyJitDriver.jit_merge_point(y=y, i=i)
                MyJitDriver.can_enter_jit(y=y, i=i)
            return y

        res = self.run(ll_function, [3], threshold=2)
        assert res == ll_function(3)
        self.check_insns_in_loops({'int_add': 1,
                                   'int_gt': 1, 'int_rshift': 1})

    def test_green_return(self):
        class MyJitDriver(JitDriver):
            greens = ['x']
            reds = []
        def ll_function(x):
            MyJitDriver.jit_merge_point(x=x)
            MyJitDriver.can_enter_jit(x=x)
            return hint(x, concrete=True) + 1

        res = self.run(ll_function, [3], threshold=1)
        assert res == 4
        self.check_insns_excluding_return({})

    def test_void_return(self):
        class MyJitDriver(JitDriver):
            greens = ['x']
            reds = []
        def ll_function(x):
            MyJitDriver.jit_merge_point(x=x)
            MyJitDriver.can_enter_jit(x=x)
            hint(x, concrete=True)

        res = self.run(ll_function, [3], threshold=1)
        assert res is None
        self.check_insns_excluding_return({})

    def test_fbinterp_void_return(self):
        class MyJitDriver(JitDriver):
            greens = []
            reds = ['i']
        def ll_function():
            i = 1024
            while i > 0:
                i >>= 1
                MyJitDriver.jit_merge_point(i=i)
                MyJitDriver.can_enter_jit(i=i)

        res = self.run(ll_function, [], threshold=2)
        assert res is None
        self.check_insns_in_loops({'int_gt': 1, 'int_rshift': 1})

    def test_green_call(self):
        class MyJitDriver(JitDriver):
            greens = ['y']
            reds = ['i']
        def ll_boring(x):
            return
        def ll_add_one(x):
            return x+1
        def ll_function(y):
            i = 1024
            while i > 0:
                i >>= 1
                MyJitDriver.jit_merge_point(y=y, i=i)
                MyJitDriver.can_enter_jit(y=y, i=i)
                ll_boring(y)
                z = ll_add_one(y)
                z = hint(z, concrete=True)
            return z

        res = self.run(ll_function, [3], threshold=2)
        assert res == 4
        self.check_insns_in_loops({'int_gt': 1, 'int_rshift': 1})

    def test_recursive_call(self):
        def indirection(n, fudge):
            return ll_pseudo_factorial(n, fudge)
        def ll_pseudo_factorial(n, fudge):
            k = hint(n, concrete=True)
            if n <= 0:
                return 1
            return n * ll_pseudo_factorial(n - 1, fudge + n) - fudge
        res = self.interpret(indirection, [4, 2], [0])
        expected = ll_pseudo_factorial(4, 2)
        assert res == expected
        

    def test_simple_struct(self):
        S = lltype.GcStruct('helloworld', ('hello', lltype.Signed),
                                          ('world', lltype.Signed),
                            hints={'immutable': True})
        
        def ll_function(s):
            i = 1024
            while i > 0:
                i >>= 1
                s1 = s
                if MyJitDriver.case >= 2:
                    hint(s1, concrete=True)     # green
                    if MyJitDriver.case == 3:
                        s1 = hint(s1, variable=True)    # constant redbox
                #
                res = s1.hello * s1.world
                #
                MyJitDriver.jit_merge_point(s=s, i=i, res=res)
                MyJitDriver.can_enter_jit(s=s, i=i, res=res)
            return res

        def main(x, y):
            s1 = lltype.malloc(S)
            s1.hello = x
            s1.world = y
            return ll_function(s1)

        class MyJitDriver(JitDriver):
            greens = []
            reds = ['s', 'i', 'res']
            case = 1
        res = self.run(main, [6, 7], threshold=2)
        assert res == 42
        self.check_insns_in_loops({'getfield': 2, 'int_mul': 1,
                                   'int_gt': 1, 'int_rshift': 1})

        class MyJitDriver(JitDriver):
            greens = ['s']
            reds = ['i', 'res']
            case = 2
        res = self.run(main, [8, 9], threshold=2)
        assert res == 72
        self.check_insns_in_loops({'int_gt': 1, 'int_rshift': 1})

        class MyJitDriver(JitDriver):
            greens = ['s']
            reds = ['i', 'res']
            case = 3
        res = self.run(main, [10, 11], threshold=2)
        assert res == 110
        self.check_insns_in_loops({'int_gt': 1, 'int_rshift': 1})

    def test_simple_array(self):
        A = lltype.GcArray(lltype.Signed, 
                            hints={'immutable': True})
        def ll_function(a):
            i = 1024
            while i > 0:
                i >>= 1
                a1 = a
                if MyJitDriver.case >= 2:
                    hint(a1, concrete=True)     # green
                    if MyJitDriver.case == 3:
                        a1 = hint(a1, variable=True)    # constant redbox
                #
                res = a1[0] * a1[1] + len(a1)
                #
                MyJitDriver.jit_merge_point(a=a, i=i, res=res)
                MyJitDriver.can_enter_jit(a=a, i=i, res=res)
            return res

        def main(x, y):
            a = lltype.malloc(A, 2)
            a[0] = x
            a[1] = y
            return ll_function(a)

        class MyJitDriver(JitDriver):
            greens = []
            reds = ['a', 'i', 'res']
            case = 1
        res = self.run(main, [6, 7], threshold=2)
        assert res == 44
        self.check_insns_in_loops({'getarrayitem': 2, 'int_mul': 1,
                                   'getarraysize': 1, 'int_add': 1,
                                   'int_gt': 1, 'int_rshift': 1})

        class MyJitDriver(JitDriver):
            greens = ['a']
            reds = ['i', 'res']
            case = 2
        res = self.run(main, [8, 9], threshold=2)
        assert res == 74
        self.check_insns_in_loops({'int_gt': 1, 'int_rshift': 1})

        class MyJitDriver(JitDriver):
            greens = ['a']
            reds = ['i', 'res']
            case = 3
        res = self.run(main, [10, 11], threshold=2)
        assert res == 112
        self.check_insns_in_loops({'int_gt': 1, 'int_rshift': 1})

    def test_degenerated_before_return(self):
        S = lltype.GcStruct('S', ('n', lltype.Signed))
        T = lltype.GcStruct('T', ('s', S), ('n', lltype.Float))

        def ll_function(flag):
            t = lltype.malloc(T)
            t.s.n = 3
            s = lltype.malloc(S)
            s.n = 4
            if flag:
                s = t.s
            s.n += 1
            return s.n * t.s.n
        res = self.interpret(ll_function, [0], [])
        assert res == 5 * 3
        res = self.interpret(ll_function, [1], [])
        assert res == 4 * 4

    def test_degenerated_before_return_2(self):
        S = lltype.GcStruct('S', ('n', lltype.Signed))
        T = lltype.GcStruct('T', ('s', S), ('n', lltype.Float))

        def ll_function(flag):
            t = lltype.malloc(T)
            t.s.n = 3
            s = lltype.malloc(S)
            s.n = 4
            if flag:
                pass
            else:
                s = t.s
            s.n += 1
            return s.n * t.s.n
        res = self.interpret(ll_function, [1], [])
        assert res == 5 * 3
        res = self.interpret(ll_function, [0], [])
        assert res == 4 * 4

    def test_degenerated_at_return(self):
        S = lltype.GcStruct('S', ('n', lltype.Signed))
        T = lltype.GcStruct('T', ('s', S), ('n', lltype.Float))

        def ll_function(flag):
            t = lltype.malloc(T)
            t.n = 3.25
            t.s.n = 3
            s = lltype.malloc(S)
            s.n = 4
            if flag:
                s = t.s
            return s

        res = self.interpret(ll_function, [0], [])
        assert res.n == 4
        res = self.interpret(ll_function, [1], [])
        assert res.n == 3

    def test_degenerated_via_substructure(self):
        S = lltype.GcStruct('S', ('n', lltype.Signed))
        T = lltype.GcStruct('T', ('s', S), ('n', lltype.Float))

        def ll_function(flag):
            t = lltype.malloc(T)
            t.s.n = 3
            s = lltype.malloc(S)
            s.n = 7
            if flag:
                pass
            else:
                s = t.s
            t.s.n += 1
            return s.n * t.s.n
        res = self.interpret(ll_function, [1], [])
        assert res == 7 * 4
        res = self.interpret(ll_function, [0], [])
        assert res == 4 * 4

    def test_degenerate_with_voids(self):
        class MyJitDriver(JitDriver):
            greens = []
            reds = ['i', 'res']
        S = lltype.GcStruct('S', ('y', lltype.Void),
                                 ('x', lltype.Signed))
        def ll_function():
            i = 1024
            while i > 0:
                i >>= 1
                #
                res = lltype.malloc(S)
                res.x = 123
                #
                MyJitDriver.jit_merge_point(i=i, res=res)
                MyJitDriver.can_enter_jit(i=i, res=res)
            return res

        res = self.run(ll_function, [], threshold=2)
        assert res.x == 123
        self.check_insns_in_loops({'int_gt': 1, 'int_rshift': 1})

    def test_plus_minus(self):
        class MyJitDriver(JitDriver):
            greens = ['s']
            reds = ['x', 'y', 'i', 'acc']
        def ll_plus_minus(s, x, y):
            i = 1024
            while i > 0:
                i >>= 1
                #
                acc = x
                n = len(s)
                pc = 0
                while pc < n:
                    op = s[pc]
                    op = hint(op, concrete=True)
                    if op == '+':
                        acc += y
                    elif op == '-':
                        acc -= y
                    pc += 1
                #
                MyJitDriver.jit_merge_point(s=s, x=x, y=y, i=i, acc=acc)
                MyJitDriver.can_enter_jit(s=s, x=x, y=y, i=i, acc=acc)
            return acc

        def main(copies, x, y):
            s = "+%s+" % ("-" * copies,)
            return ll_plus_minus(s, x, y)
        
        res = self.run(main, [5, 0, 2], threshold=2)
        assert res == ll_plus_minus("+-----+", 0, 2)
        self.check_insns_in_loops({'int_add': 2, 'int_sub': 5,
                                   'int_gt': 1, 'int_rshift': 1})

    def test_red_virtual_container(self):
        # this checks that red boxes are able to be virtualized dynamically by
        # the compiler (the P_NOVIRTUAL policy prevents the hint-annotator from
        # marking variables in blue)
        class MyJitDriver(JitDriver):
            greens = []
            reds = ['n', 'i', 'res']
        S = lltype.GcStruct('S', ('n', lltype.Signed))
        def make(n):
            s = lltype.malloc(S)
            s.n = n
            return s
        def ll_function(n):
            i = 1024
            while i > 0:
                i >>= 1
                #
                s = make(n)
                res = s.n
                #
                MyJitDriver.jit_merge_point(n=n, i=i, res=res)
                MyJitDriver.can_enter_jit(n=n, i=i, res=res)
            return res
        res = self.run(ll_function, [42], threshold=2)
        assert res == 42
        self.check_insns_in_loops({'int_gt': 1, 'int_rshift': 1})


    def test_setarrayitem(self):
        class MyJitDriver(JitDriver):
            greens = []
            reds = ['i', 'res']
        A = lltype.GcArray(lltype.Signed)
        a = lltype.malloc(A, 2, immortal=True)
        def ll_function():
            i = 1024
            while i > 0:
                i >>= 1
                #
                a[0] = 1
                a[1] = 2
                res = a[0]+a[1]
                #
                MyJitDriver.jit_merge_point(i=i, res=res)
                MyJitDriver.can_enter_jit(i=i, res=res)
            return res
        res = self.run(ll_function, [], threshold=2)
        assert res == 3
        self.check_insns_in_loops({'setarrayitem': 2,
                                   'getarrayitem': 2, 'int_add': 1,
                                   'int_gt': 1, 'int_rshift': 1})

    def test_red_array(self):
        class MyJitDriver(JitDriver):
            greens = []
            reds = ['x', 'y', 'n', 'i', 'res']
        A = lltype.GcArray(lltype.Signed)
        def ll_function(x, y, n):
            i = 1024
            while i > 0:
                i >>= 1
                #
                a = lltype.malloc(A, 2)
                a[0] = x
                a[1] = y
                res = a[n]*len(a)
                n = 1 - n
                #
                MyJitDriver.jit_merge_point(x=x, y=y, n=n, i=i, res=res)
                MyJitDriver.can_enter_jit(x=x, y=y, n=n, i=i, res=res)
            return res

        res = self.run(ll_function, [21, -21, 0], threshold=2)
        assert res == 42
        self.check_insns_in_loops({'malloc_varsize': 1,
                                   'setarrayitem': 2, 'getarrayitem': 1,
                                   'getarraysize': 1, 'int_mul': 1,
                                   'int_sub': 1,
                                   'int_gt': 1, 'int_rshift': 1})

    def test_red_struct_array(self):
        class MyJitDriver(JitDriver):
            greens = []
            reds = ['x', 'y', 'n', 'i', 'res']
        S = lltype.Struct('s', ('x', lltype.Signed))
        A = lltype.GcArray(S)
        def ll_function(x, y, n):
            i = 1024
            while i > 0:
                i >>= 1
                #
                a = lltype.malloc(A, 2)
                a[0].x = x
                a[1].x = y
                res = a[n].x*len(a)
                n = 1 - n
                #
                MyJitDriver.jit_merge_point(x=x, y=y, n=n, i=i, res=res)
                MyJitDriver.can_enter_jit(x=x, y=y, n=n, i=i, res=res)
            return res

        res = self.run(ll_function, [21, -21, 0], threshold=2)
        assert res == 42
        self.check_insns_in_loops({'malloc_varsize': 1,
                                   'setinteriorfield': 2,
                                   'getinteriorfield': 1,
                                   'getarraysize': 1, 'int_mul': 1,
                                   'int_sub': 1,
                                   'int_gt': 1, 'int_rshift': 1})

    def test_red_varsized_struct(self):
        class MyJitDriver(JitDriver):
            greens = []
            reds = ['x', 'y', 'n', 'i', 'res']
        A = lltype.Array(lltype.Signed)
        S = lltype.GcStruct('S', ('foo', lltype.Signed), ('a', A))
        def ll_function(x, y, n):
            i = 1024
            while i > 0:
                i >>= 1
                #
                s = lltype.malloc(S, 3)
                s.foo = len(s.a)-1
                s.a[0] = x
                s.a[1] = y
                res = s.a[n]*s.foo
                n = 1 - n
                #
                MyJitDriver.jit_merge_point(x=x, y=y, n=n, i=i, res=res)
                MyJitDriver.can_enter_jit(x=x, y=y, n=n, i=i, res=res)
            return res

        res = self.run(ll_function, [21, -21, 0], threshold=2)
        assert res == 42
        self.check_insns(malloc_varsize=1,
                         getinteriorarraysize=1)

    def test_array_of_voids(self):
        class MyJitDriver(JitDriver):
            greens = []
            reds = ['n', 'i', 'res']
        A = lltype.GcArray(lltype.Void)
        def ll_function(n):
            i = 1024
            while i > 0:
                i >>= 1
                #
                a = lltype.malloc(A, 3)
                a[1] = None
                b = a[n]
                res = a, b
                # we mention 'b' to prevent the getarrayitem operation
                # from disappearing
                keepalive_until_here(b)
                #
                MyJitDriver.jit_merge_point(n=n, i=i, res=res)
                MyJitDriver.can_enter_jit(n=n, i=i, res=res)
            return res

        res = self.run(ll_function, [2], threshold=3)
        assert len(res.item0) == 3

    def test_red_propagate(self):
        S = lltype.GcStruct('S', ('n', lltype.Signed))
        def ll_function(n, k):
            s = lltype.malloc(S)
            s.n = n
            if k < 0:
                return -123
            return s.n * k
        res = self.interpret(ll_function, [3, 8], [])
        assert res == 24
        self.check_insns({'int_lt': 1, 'int_mul': 1})

    def test_red_subcontainer_escape(self):
        py.test.skip("broken")
        class MyJitDriver(JitDriver):
            greens = []
            reds = ['k', 'i', 'res']
        S = lltype.GcStruct('S', ('n', lltype.Signed))
        T = lltype.GcStruct('T', ('s', S), ('n', lltype.Signed))
        def ll_function(k):
            i = 1024
            while i > 0:
                i >>= 1
                #
                t = lltype.malloc(T)
                if k < 0:
                    s = lltype.cast_pointer(lltype.Ptr(S), t)
                else:
                    s = t.s
                s.n = k
                t.n = k*k
                res = s
                #
                MyJitDriver.jit_merge_point(k=k, i=i, res=res)
                MyJitDriver.can_enter_jit(k=k, i=i, res=res)
            return res

        res = self.run(ll_function, [7], threshold=2)
        assert res.n == 7
        assert lltype.cast_pointer(lltype.Ptr(T), res).n == 49
        self.check_insns_in_loops(malloc=1, setfield=2)

        res = self.run(ll_function, [-6], threshold=2)
        assert res.n == -6
        assert lltype.cast_pointer(lltype.Ptr(T), res).n == 36
        self.check_insns_in_loops(malloc=1, setfield=2)

    def test_red_subcontainer_cast(self):
        class MyJitDriver(JitDriver):
            greens = []
            reds = ['k', 'i', 'res']
        S = lltype.GcStruct('S', ('n', lltype.Signed))
        T = lltype.GcStruct('T', ('s', S), ('n', lltype.Float))
        def ll_function(k):
            i = 1024*1024
            while i > 0:
                i >>= 1
                #
                t = lltype.malloc(T)
                if k < 5:
                    s = lltype.cast_pointer(lltype.Ptr(S), t)
                else:
                    s = t.s
                s.n = k
                if k < 0:
                    res = -123
                else:
                    res = s.n * (k-1)
                keepalive_until_here(t)
                k += 1
                #
                MyJitDriver.jit_merge_point(k=k, i=i, res=res)
                MyJitDriver.can_enter_jit(k=k, i=i, res=res)
            return res
        res = self.run(ll_function, [-10], threshold=2)
        assert res == 10*9
        self.check_insns_in_loops(malloc=0, getfield=0, setfield=0)

    def test_merge_structures(self):
        S = lltype.GcStruct('S', ('n', lltype.Signed))
        T = lltype.GcStruct('T', ('s', lltype.Ptr(S)), ('n', lltype.Signed))

        def ll_function(flag):
            if flag:
                s = lltype.malloc(S)
                s.n = 1
                t = lltype.malloc(T)
                t.s = s
                t.n = 2
            else:
                s = lltype.malloc(S)
                s.n = 5
                t = lltype.malloc(T)
                t.s = s
                t.n = 6
            return t.n + t.s.n
        res = self.interpret(ll_function, [0], [])
        assert res == 5 + 6
        self.check_insns({'int_is_true': 1, 'int_add': 1})
        res = self.interpret(ll_function, [1], [])
        assert res == 1 + 2
        self.check_insns({'int_is_true': 1, 'int_add': 1})


    def test_green_with_side_effects(self):
        S = lltype.GcStruct('S', ('flag', lltype.Bool))
        s = lltype.malloc(S)
        s.flag = False
        def ll_set_flag(s):
            s.flag = True
        def ll_function():
            s.flag = False
            ll_set_flag(s)
            return s.flag
        res = self.interpret(ll_function, [], [])
        assert res == True
        self.check_insns({'setfield': 2, 'getfield': 1})

    def test_deepfrozen_interior(self):
        T = lltype.Struct('T', ('x', lltype.Signed))
        A = lltype.Array(T)
        S = lltype.GcStruct('S', ('a', A))
        s = lltype.malloc(S, 3, zero=True)
        s.a[2].x = 42
        def f(n):
            s1 = hint(s, variable=True)
            s1 = hint(s1, deepfreeze=True)
            return s1.a[n].x

        # malloc-remove the interior ptr
        res = self.interpret(f, [2], [0], backendoptimize=True)
        assert res == 42
        self.check_insns({})

    def test_compile_time_const_tuple(self):
        d = {(4, 5): 42, (6, 7): 12}
        def f(a, b):
            d1 = hint(d, deepfreeze=True)
            return d1[a, b]

        # malloc-remove the interior ptr
        res = self.interpret(f, [4, 5], [0, 1],
                             backendoptimize=True)
        assert res == 42
        self.check_insns({})

    def test_residual_red_call(self):
        class MyJitDriver(JitDriver):
            greens = []
            reds = ['i', 'x', 'res']
        def g(x):
            return x+1
        def f(x):
            i = 1024
            while i > 0:
                i >>= 1
                res = 2*g(x)
                MyJitDriver.jit_merge_point(x=x, i=i, res=res)
                MyJitDriver.can_enter_jit(x=x, i=i, res=res)
            return res

        res = self.run(f, [20], threshold=2, policy=StopAtXPolicy(g))
        assert res == 42
        self.check_insns_in_loops({'direct_call': 1, 'int_mul': 1,
                                   'int_gt': 1, 'int_rshift': 1})

    def test_residual_red_call_with_exc(self):
        class MyJitDriver(JitDriver):
            greens = []
            reds = ['i', 'x', 'res']

        def h(x):
            if x > 0:
                return x+1
            else:
                raise ValueError

        def g(x):
            return 2*h(x)

        def f(x):
            i = 1024
            while i > 0:
                i >>= 1
                try:
                    res = g(x)
                except ValueError:
                    res = 7
                MyJitDriver.jit_merge_point(x=x, i=i, res=res)
                MyJitDriver.can_enter_jit(x=x, i=i, res=res)
            return res

        stop_at_h = StopAtXPolicy(h)
        res = self.run(f, [20], threshold=2, policy=stop_at_h)
        assert res == 42
        self.check_insns_in_loops(int_add=0, int_mul=1)

        res = self.run(f, [-20], threshold=2, policy=stop_at_h)
        assert res == 7
        self.check_insns_in_loops(int_add=0, int_mul=0)

    def test_red_call_ignored_result(self):
        def g(n):
            return n * 7
        def f(n, m):
            g(n)   # ignore the result
            return m

        res = self.interpret(f, [4, 212], [])
        assert res == 212

    def test_simple_yellow_meth(self):
        class MyJitDriver(JitDriver):
            greens = []
            reds = ['flag', 'res', 'i']

        class Base(object):
            def m(self):
                return 21
            pass  # for inspect.getsource() bugs

        class Concrete(Base):
            def m(self):
                return 42
            pass  # for inspect.getsource() bugs

        def f(flag):
            i = 1024
            while i > 0:
                i >>= 1
                if flag:
                    o = Base()
                else:
                    o = Concrete()
                res = o.m()        # yellow call
                MyJitDriver.jit_merge_point(flag=flag, res=res, i=i)
                MyJitDriver.can_enter_jit(flag=flag, res=res, i=i)
            return res

        res = self.run(f, [0], threshold=2)
        assert res == 42
        self.check_insns_in_loops({'int_is_true': 1,
                                   'int_gt': 1, 'int_rshift': 1})

    def test_simple_red_meth(self):
        class MyJitDriver(JitDriver):
            greens = []
            reds = ['flag', 'res', 'i']

        class Base(object):
            def m(self, i):
                return 21 + i
            pass  # for inspect.getsource() bugs

        class Concrete(Base):
            def m(self, i):
                return 42 - i
            pass  # for inspect.getsource() bugs

        def f(flag):
            i = 1024
            while i > 0:
                i >>= 1
                if flag:
                    o = Base()
                else:
                    o = Concrete()
                res = o.m(i)        # red call
                MyJitDriver.jit_merge_point(flag=flag, res=res, i=i)
                MyJitDriver.can_enter_jit(flag=flag, res=res, i=i)
            return res

        res = self.run(f, [0], threshold=2)
        assert res == 42
        self.check_insns_in_loops({'int_is_true': 1, 'int_sub': 1,
                                   'int_gt': 1, 'int_rshift': 1})

    def test_simple_red_meth_vars_around(self):
        class MyJitDriver(JitDriver):
            greens = ['y']
            reds = ['flag', 'x', 'z', 'res', 'i']

        class Base(object):
            def m(self, n):
                raise NotImplementedError
            pass  # for inspect.getsource() bugs

        class Concrete(Base):
            def m(self, n):
                return 21*n
            pass  # for inspect.getsource() bugs

        def f(flag, x, y, z):
            i = 1024
            while i > 0:
                i >>= 1
                if flag:
                    o = Base()
                else:
                    o = Concrete()
                hint(y, concrete=True)
                res = (o.m(x)+y)-z
                MyJitDriver.jit_merge_point(flag=flag, res=res, i=i,
                                            x=x, y=y, z=z)
                MyJitDriver.can_enter_jit(flag=flag, res=res, i=i,
                                          x=x, y=y, z=z)
            return res

        res = self.run(f, [0, 2, 7, 5], threshold=2)
        assert res == 44
        self.check_insns_in_loops({'int_is_true': 1,
                                   'int_mul': 1, 'int_add': 1, 'int_sub': 1,
                                   'int_gt': 1, 'int_rshift': 1})

    def test_green_red_mismatch_in_call(self):
        class MyJitDriver(JitDriver):
            greens = ['x', 'y']
            reds = ['u', 'res', 'i']

        def add(a,b, u):
            return a+b

        def f(x, y, u):
            i = 1024
            while i > 0:
                i >>= 1
                r = add(x+1,y+1, u)
                z = x+y
                z = hint(z, concrete=True) + r  # this checks that 'r' is green
                res = hint(z, variable=True)
                MyJitDriver.jit_merge_point(x=x, y=y, u=u, res=res, i=i)
                MyJitDriver.can_enter_jit(x=x, y=y, u=u, res=res, i=i)
            return res

        res = self.run(f, [4, 5, 0], threshold=2)
        assert res == 20


    def test_recursive_with_red_termination_condition(self):
        py.test.skip('Does not terminate')
        def indirection(n):
            return ll_factorial
        def ll_factorial(n):
            if n <= 0:
                return 1
            return n * ll_factorial(n - 1)

        res = self.interpret(indirection, [5], [])
        assert res == 120
        
    def test_simple_indirect_call(self):
        class MyJitDriver(JitDriver):
            greens = ['flag']
            reds = ['v', 'res', 'i']

        def g1(v):
            return v * 2

        def g2(v):
            return v + 2

        def f(flag, v):
            i = 1024
            while i > 0:
                i >>= 1
                if hint(flag, concrete=True):
                    g = g1
                else:
                    g = g2
                res = g(v)
                MyJitDriver.jit_merge_point(flag=flag, v=v, res=res, i=i)
                MyJitDriver.can_enter_jit(flag=flag, v=v, res=res, i=i)
            return res

        res = self.run(f, [0, 40], threshold=2)
        assert res == 42
        self.check_insns_in_loops({'int_add': 1,
                                   'int_gt': 1, 'int_rshift': 1})

    def test_normalize_indirect_call(self):
        class MyJitDriver(JitDriver):
            greens = ['flag']
            reds = ['v', 'res', 'i']

        def g1(v):
            return -17

        def g2(v):
            return v + 2

        def f(flag, v):
            i = 1024
            while i > 0:
                i >>= 1
                if hint(flag, concrete=True):
                    g = g1
                else:
                    g = g2
                res = g(v)
                MyJitDriver.jit_merge_point(flag=flag, v=v, res=res, i=i)
                MyJitDriver.can_enter_jit(flag=flag, v=v, res=res, i=i)
            return res

        res = self.run(f, [0, 40], threshold=2)
        assert res == 42
        self.check_insns_in_loops({'int_add': 1,
                                   'int_gt': 1, 'int_rshift': 1})

        res = self.run(f, [1, 40], threshold=2)
        assert res == -17
        self.check_insns_in_loops({'int_gt': 1, 'int_rshift': 1})

    def test_normalize_indirect_call_more(self):
        class MyJitDriver(JitDriver):
            greens = ['flag']
            reds = ['v', 'res', 'i']

        def g1(v):
            if v >= 0:
                return -17
            else:
                return -155

        def g2(v):
            return v + 2

        def f(flag, v):
            i = 1024
            while i > 0:
                i >>= 1
                w = g1(v)
                if hint(flag, concrete=True):
                    g = g1
                else:
                    g = g2
                res = g(v) + w
                MyJitDriver.jit_merge_point(flag=flag, v=v, res=res, i=i)
                MyJitDriver.can_enter_jit(flag=flag, v=v, res=res, i=i)
            return res

        res = self.run(f, [0, 40], threshold=2)
        assert res == 25
        self.check_insns_in_loops({'int_add': 2, 'int_ge': 1,
                                   'int_gt': 1, 'int_rshift': 1})

        res = self.run(f, [1, 40], threshold=2)
        assert res == -34
        self.check_insns_in_loops({'int_ge': 2,
                                   'int_gt': 1, 'int_rshift': 1})

        res = self.run(f, [0, -1000], threshold=2)
        assert res == f(False, -1000)
        self.check_insns_in_loops({'int_add': 2, 'int_ge': 1,
                                   'int_gt': 1, 'int_rshift': 1})

        res = self.run(f, [1, -1000], threshold=2)
        assert res == f(True, -1000)
        self.check_insns_in_loops({'int_ge': 2,
                                   'int_gt': 1, 'int_rshift': 1})

    def test_green_char_at_merge(self):
        def f(c, x):
            c = chr(c)
            c = hint(c, concrete=True)
            if x:
                x = 3
            else:
                x = 1
            c = hint(c, variable=True)
            return len(c*x)

        res = self.interpret(f, [ord('a'), 1], [])
        assert res == 3

        res = self.interpret(f, [ord('b'), 0], [])
        assert res == 1

    def test_self_referential_structures(self):
        S = lltype.GcForwardReference()
        S.become(lltype.GcStruct('s',
                                 ('ps', lltype.Ptr(S))))

        def f(x):
            s = lltype.malloc(S)
            if x:
                s.ps = lltype.malloc(S)
            return s
        def count_depth(s):
            x = 0
            while s:
                x += 1
                s = s.ps
            return x
        
        res = self.interpret(f, [3], [])
        assert count_depth(res) == 2

    def test_known_nonzero(self):
        class MyJitDriver(JitDriver):
            greens = ['x']
            reds = ['y', 'res', 'i']
        S = lltype.GcStruct('s', ('x', lltype.Signed))
        global_s = lltype.malloc(S, immortal=True)
        global_s.x = 100

        def h(i):
            if i < 30:
                return global_s
            else:
                return lltype.nullptr(S)
        def g(s, y):
            if s:
                return s.x * 5
            else:
                return -12 + y
        def f(x, y):
            i = 1024
            while i > 0:
                i >>= 1
                #
                x = hint(x, concrete=True)
                if x == 1:
                    res = g(lltype.nullptr(S), y)
                elif x == 2:
                    res = g(global_s, y)
                elif x == 3:
                    s = lltype.malloc(S)
                    s.x = y
                    res = g(s, y)
                elif x == 4:
                    s = h(i)
                    res = g(s, y)
                else:
                    s = h(i)
                    if s:
                        res = g(s, y)
                    else:
                        res = 0
                #
                MyJitDriver.jit_merge_point(x=x, y=y, res=res, i=i)
                MyJitDriver.can_enter_jit(x=x, y=y, res=res, i=i)
            return res

        P = StopAtXPolicy(h)

        res = self.run(f, [1, 10], threshold=2, policy=P)
        assert res == -2
        self.check_insns_in_loops({'int_add': 1,
                                   'int_gt': 1, 'int_rshift': 1})

        res = self.run(f, [2, 10], threshold=2, policy=P)
        assert res == 500
        self.check_insns_in_loops({'getfield': 1, 'int_mul': 1,
                                   'int_gt': 1, 'int_rshift': 1})

        res = self.run(f, [3, 10], threshold=2, policy=P)
        assert res == 50
        self.check_insns_in_loops({'int_mul': 1,
                                   'int_gt': 1, 'int_rshift': 1})

        res = self.run(f, [4, 10], threshold=2, policy=P)
        assert res == 500
        self.check_insns_in_loops({'direct_call': 1, 'ptr_nonzero': 1,
                                   'getfield': 1, 'int_mul': 1,
                                   'int_add': 1,
                                   'int_gt': 1, 'int_rshift': 1})

        res = self.run(f, [5, 10], threshold=2, policy=P)
        assert res == 500
        self.check_insns_in_loops({'direct_call': 1, 'ptr_nonzero': 1,
                                   'getfield': 1, 'int_mul': 1,
                                   'int_gt': 1, 'int_rshift': 1})

    def test_debug_assert_ptr_nonzero(self):
        class MyJitDriver(JitDriver):
            greens = []
            reds = ['m', 'res', 'i']
        S = lltype.GcStruct('s', ('x', lltype.Signed))
        global_s = lltype.malloc(S)
        global_s.x = 42
        def h(flag):
            if flag:
                return global_s
            else:
                return lltype.nullptr(S)
        def g(s):
            # assumes that s is not null here
            ll_assert(bool(s), "please don't give me a null")
            return 5
        def f(m):
            i = 1024
            while i > 0:
                i >>= 1
                #
                s = h(m)
                n = g(s)
                if not s:
                    n *= m
                res = n
                #
                MyJitDriver.jit_merge_point(m=m, res=res, i=i)
                MyJitDriver.can_enter_jit(m=m, res=res, i=i)
            return res

        P = StopAtXPolicy(h)

        res = self.run(f, [17], threshold=2, policy=P)
        assert res == 5
        self.simplify_graph()   # to remove ptr_nonzero with unused result
        self.check_insns_in_loops(int_mul=0, ptr_iszero=0, ptr_nonzero=0)

    def test_indirect_red_call(self):
        class MyJitDriver(JitDriver):
            greens = []
            reds = ['n', 'x', 'res', 'i']
        def h1(n):
            return n*2
        def h2(n):
            return n*4
        l = [h1, h2]
        def f(n, x):
            i = 1024
            while i > 0:
                i >>= 1
                #
                h = l[n&1]
                res = h(n) + x
                #
                MyJitDriver.jit_merge_point(n=n, x=x, res=res, i=i)
                MyJitDriver.can_enter_jit(n=n, x=x, res=res, i=i)
            return res

        res = self.run(f, [7, 3], threshold=2)
        assert res == f(7,3)
        self.check_insns_in_loops(int_mul=1)    # call target eagerly promoted

    def test_indirect_red_call_with_exc(self):
        py.test.skip("only interesting if the call target is not promoted")
        def h1(n):
            if n < 0:
                raise ValueError
            return n*2
        def h2(n):
            if n < 0:
                raise ValueError
            return n*4
        l = [h1, h2]
        def g(n, x):
            h = l[n&1]
            return h(n) + x

        def f(n, x):
            hint(None, global_merge_point=True)
            try:
                return g(n, x)
            except ValueError:
                return -1111

        P = StopAtXPolicy()
        res = self.interpret(f, [7, 3], policy=P)
        assert res == f(7,3)
        self.check_insns(indirect_call=1)

        res = self.interpret(f, [-7, 3], policy=P)
        assert res == -1111
        self.check_insns(indirect_call=1)

    def test_indirect_gray_call(self):
        class MyJitDriver(JitDriver):
            greens = []
            reds = ['n', 'x', 'res', 'i']
        def h1(w, n):
            w[0] =  n*2
        def h2(w, n):
            w[0] = n*4
        l = [h1, h2]
        def f(n, x):
            i = 1024
            while i > 0:
                i >>= 1
                #
                w = [0]
                h = l[n&1]
                h(w, n)
                res = w[0] + x
                #
                MyJitDriver.jit_merge_point(n=n, x=x, res=res, i=i)
                MyJitDriver.can_enter_jit(n=n, x=x, res=res, i=i)
            return res

        res = self.run(f, [7, 3], threshold=2)
        assert res == f(7,3)

    def test_indirect_residual_red_call(self):
        class MyJitDriver(JitDriver):
            greens = []
            reds = ['n', 'x', 'res', 'i']
        def h1(n):
            return n*2
        def h2(n):
            return n*4
        l = [h1, h2]
        def f(n, x):
            i = 1024
            while i > 0:
                i >>= 1
                #
                h = l[n&1]
                res = h(n) + x
                #
                MyJitDriver.jit_merge_point(n=n, x=x, res=res, i=i)
                MyJitDriver.can_enter_jit(n=n, x=x, res=res, i=i)
            return res

        P = StopAtXPolicy(h1, h2)
        res = self.run(f, [7, 3], threshold=2, policy=P)
        assert res == f(7,3)
        self.check_insns_in_loops({'int_and': 1,
                                   'direct_call': 1,     # to list.getitem
                                   'indirect_call': 1,
                                   'int_add': 1,
                                   'int_gt': 1, 'int_rshift': 1})

    def test_indirect_residual_red_call_with_exc(self):
        class MyJitDriver(JitDriver):
            greens = []
            reds = ['n', 'x', 'res', 'i']
        def h1(n):
            if n < 0:
                raise ValueError
            return n*2
        def h2(n):
            return n*4
        l = [h1, h2]
        def f(n, x):
            i = 1024
            while i > 0:
                i >>= 1
                #
                h = l[n&1]
                try:
                    res = h(n) + x
                except ValueError:
                    res = -42
                #
                MyJitDriver.jit_merge_point(n=n, x=x, res=res, i=i)
                MyJitDriver.can_enter_jit(n=n, x=x, res=res, i=i)
            return res

        P = StopAtXPolicy(h1, h2)
        res = self.run(f, [7, 3], threshold=2, policy=P)
        assert res == f(7,3)

        res = self.run(f, [-2, 3], threshold=2, policy=P)
        assert res == f(-2, 3) == -42
        self.check_insns_in_loops(indirect_call=1, int_add=0, int_mul=0)

    def test_constant_indirect_red_call(self):
        class MyJitDriver(JitDriver):
            greens = ['m', 'n']
            reds = ['x', 'res', 'i']
        def h1(m, n, x):
            return x-2
        def h2(m, n, x):
            return x*4
        l = [h1, h2]
        def f(m, n, x):
            i = 1024
            while i > 0:
                i >>= 1
                #
                m = hint(m, concrete=True)
                hint(n, concrete=True)
                frozenl = hint(l, deepfreeze=True)
                h = frozenl[hint(n, variable=True) & 1]
                res = h(m, 5, x)
                #
                MyJitDriver.jit_merge_point(m=m, n=n, x=x, res=res, i=i)
                MyJitDriver.can_enter_jit(m=m, n=n, x=x, res=res, i=i)
            return res

        res = self.run(f, [1, 7, 3], threshold=2)
        assert res == f(1,7,3)
        self.check_insns_in_loops({'int_mul': 1,
                                   'int_gt': 1, 'int_rshift': 1})
        res = self.run(f, [1, 4, 113], threshold=2)
        assert res == f(1,4,113)
        self.check_insns_in_loops({'int_sub': 1,
                                   'int_gt': 1, 'int_rshift': 1})

    def test_constant_indirect_red_call_no_result(self):
        class MyJitDriver(JitDriver):
            greens = ['m', 'n']
            reds = ['x', 'res', 'i']
        class A:
            pass
        glob_a = A()
        def h1(m, n, x):
            glob_a.x = x-2
        def h2(m, n, x):
            glob_a.x = x*4
        l = [h1, h2]
        def f(m, n, x):
            i = 1024
            while i > 0:
                i >>= 1
                #
                m = hint(m, concrete=True)
                hint(n, concrete=True)
                frozenl = hint(l, deepfreeze=True)
                h = frozenl[hint(n, variable=True) & 1]
                h(m, 5, x)
                res = glob_a.x
                #
                MyJitDriver.jit_merge_point(m=m, n=n, x=x, res=res, i=i)
                MyJitDriver.can_enter_jit(m=m, n=n, x=x, res=res, i=i)
            return res

        res = self.run(f, [1, 7, 3], threshold=2)
        assert res == f(1,7,3)
        self.check_insns_in_loops(int_mul=1, int_sub=0, setfield=1, getfield=1)
        res = self.run(f, [1, 4, 113], threshold=2)
        assert res == f(1,4,113)
        self.check_insns_in_loops(int_mul=0, int_sub=1, setfield=1, getfield=1)

    def test_indirect_sometimes_residual_pure_red_call(self):
        class MyJitDriver(JitDriver):
            greens = ['n']
            reds = ['x', 'res', 'i']
        def h1(x):
            return x-2
        def h2(x):
            return x*4
        l = [h1, h2]
        def f(n, x):
            i = 1024
            while i > 0:
                i >>= 1
                #
                hint(n, concrete=True)
                frozenl = hint(l, deepfreeze=True)
                h = frozenl[n&1]
                res = h(x)
                #
                MyJitDriver.jit_merge_point(n=n, x=x, res=res, i=i)
                MyJitDriver.can_enter_jit(n=n, x=x, res=res, i=i)
            return res

        P = StopAtXPolicy(h1)
        P.oopspec = True
        res = self.run(f, [7, 3], threshold=2, policy=P)
        assert res == f(7,3)
        self.check_insns_in_loops({'int_mul': 1,
                                   'int_gt': 1, 'int_rshift': 1})
        res = self.run(f, [4, 113], threshold=2, policy=P)
        assert res == f(4,113)
        self.check_insns_in_loops({'direct_call': 1,
                                   'int_gt': 1, 'int_rshift': 1})

    def test_indirect_sometimes_residual_pure_but_fixed_red_call(self):
        class MyJitDriver(JitDriver):
            greens = ['n', 'x']
            reds = ['i', 'res']
        def h1(x):
            return x-2
        def h2(x):
            return x*4
        l = [h1, h2]
        def f(n, x):
            i = 1024
            while i > 0:
                i >>= 1
                #
                frozenl = hint(l, deepfreeze=True)
                h = frozenl[n&1]
                z = h(x)
                hint(z, concrete=True)
                res = hint(z, variable=True)
                #
                MyJitDriver.jit_merge_point(n=n, x=x, res=res, i=i)
                MyJitDriver.can_enter_jit(n=n, x=x, res=res, i=i)
            return res

        P = StopAtXPolicy(h1)
        P.oopspec = True
        res = self.run(f, [7, 3], threshold=2, policy=P)
        assert res == f(7,3)
        self.check_insns_in_loops({'int_gt': 1, 'int_rshift': 1})
        res = self.run(f, [4, 113], threshold=2, policy=P)
        assert res == f(4,113)
        self.check_insns_in_loops({'int_gt': 1, 'int_rshift': 1})

    def test_manual_marking_of_pure_functions(self):
        class MyJitDriver(JitDriver):
            greens = ['n']
            reds = ['i', 'res']
        d = {}
        def h1(s):
            try:
                return d[s]
            except KeyError:
                d[s] = r = s * 15
                return r
        h1._pure_function_ = True
        def f(n):
            i = 1024
            while i > 0:
                i >>= 1
                #
                hint(n, concrete=True)
                if n == 0:
                    s = 123
                else:
                    s = 567
                a = h1(s)
                res = hint(a, variable=True)
                #
                MyJitDriver.jit_merge_point(n=n, res=res, i=i)
                MyJitDriver.can_enter_jit(n=n, res=res, i=i)
            return res

        P = StopAtXPolicy(h1)
        P.oopspec = True
        res = self.run(f, [0], threshold=2, policy=P)
        assert res == 123 * 15
        self.check_insns_in_loops({'int_gt': 1, 'int_rshift': 1})
        res = self.run(f, [4], threshold=2, policy=P)
        assert res == 567 * 15
        self.check_insns_in_loops({'int_gt': 1, 'int_rshift': 1})


    def test_red_int_add_ovf(self):
        class MyJitDriver(JitDriver):
            greens = []
            reds = ['n', 'm', 'i', 'result']
        def f(n, m):
            i = 1024
            while i > 0:
                i >>= 1
                try:
                    result = ovfcheck(n + m)
                except OverflowError:
                    result = -42 + m
                MyJitDriver.jit_merge_point(n=n, m=m, i=i, result=result)
                MyJitDriver.can_enter_jit(n=n, m=m, i=i, result=result)
            return result + 1

        res = self.run(f, [100, 20], threshold=2)
        assert res == 121
        self.check_insns_in_loops(int_add_ovf=1)

        res = self.run(f, [sys.maxint, 1], threshold=2)
        assert res == -40
        self.check_insns_in_loops(int_add_ovf=1)

    def test_green_int_add_ovf(self):
        py.test.skip("not working yet")
        def f(n, m):
            try:
                res = ovfcheck(n + m)
            except OverflowError:
                res = -42
            hint(res, concrete=True)
            return res

        res = self.interpret(f, [100, 20])
        assert res == 120
        self.check_insns({})
        res = self.interpret(f, [sys.maxint, 1])
        assert res == -42
        self.check_insns({})

    def test_nonzeroness_assert_while_compiling(self):
        class X:
            pass
        class Y:
            pass

        def g(x, y):
            if y.flag:
                return x.value
            else:
                return -7

        def h(n):
            if n:
                x = X()
                x.value = n
                return x
            else:
                return None

        y = Y()

        def f(n):
            y.flag = True
            g(h(n), y)
            y.flag = False
            return g(h(0), y)

        res = self.interpret(f, [42])
        assert res == -7

    def test_segfault_while_compiling(self):
        class X:
            pass
        class Y:
            pass

        def g(x, y):
            x = hint(x, deepfreeze=True)
            if y.flag:
                return x.value
            else:
                return -7

        def h(n):
            if n:
                x = X()
                x.value = n
                return x
            else:
                return None

        y = Y()

        def f(n):
            y.flag = True
            g(h(n), y)
            y.flag = False
            return g(h(0), y)

        res = self.interpret(f, [42])
        assert res == -7

    def test_switch(self):
        class MyJitDriver(JitDriver):
            greens = ['m']
            reds = ['n', 'i', 'res']
        def g(n, x):
            if n == 0:
                return 12 + x
            elif n == 1:
                return 34 + x
            elif n == 3:
                return 56 + x
            elif n == 7:
                return 78 + x
            else:
                return 90 + x
        def f(n, m):
            i = 1024
            while i > 0:
                i >>= 1
                #
                x = g(n, n)   # gives a red switch
                y = g(hint(m, concrete=True), n)   # gives a green switch
                res = x - y
                #
                MyJitDriver.jit_merge_point(n=n, m=m, res=res, i=i)
                MyJitDriver.can_enter_jit(n=n, m=m, res=res, i=i)
            return res

        res = self.run(f, [7, 2], threshold=2)
        assert res == 78 - 90
        res = self.run(f, [8, 1], threshold=2)
        assert res == 90 - 34

    def test_switch_char(self):
        def g(n, x):
            n = chr(n)
            if n == '\x00':
                return 12 + x
            elif n == '\x01':
                return 34 + x
            elif n == '\x02':
                return 56 + x
            elif n == '\x03':
                return 78 + x
            else:
                return 90 + x
        def f(n, m):
            x = g(n, n)   # gives a red switch
            y = g(hint(m, concrete=True), n)   # gives a green switch
            return x - y

        res = self.interpret(f, [3, 0], backendoptimize=True)
        assert res == 78 - 12
        res = self.interpret(f, [2, 4], backendoptimize=True)
        assert res == 56 - 90

    def test_simple_substitute_graph(self):

        class MetaG:
            def __init__(self, codewriter):
                pass

            def _freeze_(self):
                return True

            def metafunc(self, jitstate, abox, bbox):
                from pypy.jit.timeshifter.rvalue import IntRedBox
                builder = jitstate.curbuilder
                gv_result = builder.genop2("int_sub", abox.getgenvar(jitstate),
                                           bbox.getgenvar(jitstate))
                return IntRedBox(abox.kind, gv_result)

        class MyJitDriver(JitDriver):
            greens = []
            reds = ['a', 'b', 'i', 'res']

        A = lltype.GcArray(lltype.Signed)

        def g(a, b):
            return a + b

        def f(a, b):
            res = lltype.malloc(A, 20)
            i = 0
            while i < 10:
                #
                x = g(a, b)
                y = g(b, a)
                res[2*i] = x
                res[2*i+1] = y
                #
                MyJitDriver.jit_merge_point(a=a, b=b, res=res, i=i)
                MyJitDriver.can_enter_jit(a=a, b=b, res=res, i=i)
                i += 1
            return res

        class MyPolicy(HintAnnotatorPolicy):
            novirtualcontainer = True
            
            def look_inside_graph(self, graph):
                if graph.func is g:
                    return MetaG   # replaces g with a meta-call to metafunc()
                else:
                    return True

        res = self.run(f, [7, 1], threshold=3, policy=MyPolicy())
        assert list(res) == [8, 8,  8, 8,  8, 8,   # direct run
                             8, 8,  8, 8,          # fallback interp run
                             6, -6,  6, -6,  6, -6,  6, -6,  6, -6]  # compiled
        self.check_insns_in_loops(int_sub=2)

    def test_substitute_graph_void(self):

        class MetaG:
            def __init__(self, codewriter):
                pass

            def _freeze_(self):
                return True

            def metafunc(self, jitstate, space, mbox):
                from pypy.jit.timeshifter.rvalue import IntRedBox
                builder = jitstate.curbuilder
                gv_result = builder.genop1("int_neg", mbox.getgenvar(jitstate))
                return IntRedBox(mbox.kind, gv_result)

        class MyJitDriver(JitDriver):
            greens = ['m']
            reds = ['n', 'i', 'res']

        class Fz(object):
            x = 10
            
            def _freeze_(self):
                return True

        def g(fz, m):
            return m * fz.x

        fz = Fz()

        def f(n, m):
            i = 1024
            while i > 0:
                i >>= 1
                #
                x = g(fz, n)    # this goes via MetaG
                y = g(fz, m)    # but this g() runs directly (green call)
                hint(y, concrete=True)
                res = x + g(fz, y)   # this g() too
                #
                MyJitDriver.jit_merge_point(n=n, m=m, res=res, i=i)
                MyJitDriver.can_enter_jit(n=n, m=m, res=res, i=i)
            return res

        class MyPolicy(HintAnnotatorPolicy):
            novirtualcontainer = True
            
            def look_inside_graph(self, graph):
                if graph.func is g:
                    return MetaG   # replaces g with a meta-call to metafunc()
                else:
                    return True

        res = self.run(f, [3, 6], threshold=2, policy=MyPolicy())
        assert res == -3 + 600
        self.check_insns_in_loops({'int_neg': 1, 'int_add': 1,
                                   'int_gt': 1, 'int_rshift': 1})

    def test_hash_of_green_string_is_green(self):
        py.test.skip("unfortunately doesn't work")
        def f(n):
            if n == 0:
                s = "abc"
            elif n == 1:
                s = "cde"
            else:
                s = "fgh"
            return hash(s)

        res = self.interpret(f, [0])
        self.check_insns({'int_eq': 2})
        assert res == f(0)

    def test_misplaced_global_merge_point(self):
        def g(n):
            hint(None, global_merge_point=True)
            return n+1
        def f(n):
            hint(None, global_merge_point=True)
            return g(n)
        py.test.raises(AssertionError, self.interpret, f, [7], [])

    # void tests
    def test_void_args(self):
        class Space(object):
            true = True
            false = False
            
            def is_true(self, x):
                if x:
                    return self.true
                return self.false

            def add(self, x, y):
                return x + y

            def sub(self, x, y):
                return x - y

            def _freeze_(self):
                return True

        class MyJitDriver(JitDriver):
            greens = []
            reds = ['space', 'x', 'y', 'i', 'res']

        def f(space, x, y):
            i = 1024
            while i > 0:
                i >>= 1
                #
                if space.is_true(x):
                    res = space.add(x, y)
                else:
                    res = space.sub(6, y)
                #
                MyJitDriver.jit_merge_point(space=space, x=x, y=y,
                                            res=res, i=i)
                MyJitDriver.can_enter_jit(space=space, x=x, y=y,
                                          res=res, i=i)
            return res

        def main1(x, y):
            return f(space, x, y)

        space = Space()
        res = self.run(main1, [5, 6], threshold=2)
        assert res == 11

        def g(space, x, y):
            return space.add(x, y)

        def f(space, x, y):
            i = 1024
            while i > 0:
                i >>= 1
                #
                if space.is_true(x):
                    res = g(space, x, y)
                else:
                    res = space.sub(6, y)
                #
                MyJitDriver.jit_merge_point(space=space, x=x, y=y,
                                            res=res, i=i)
                MyJitDriver.can_enter_jit(space=space, x=x, y=y,
                                          res=res, i=i)
            return res

        def main2(x, y):
            return f(space, x, y)
        res = self.run(main2, [5, 6], threshold=2, policy=StopAtXPolicy(g))
        assert res == 11


    #def test_handle_SegfaultException(self):
    #    ...
