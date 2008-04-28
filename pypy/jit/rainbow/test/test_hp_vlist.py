import py
from pypy.jit.hintannotator.policy import HintAnnotatorPolicy
from pypy.jit.rainbow.test.test_interpreter import InterpretationTest, P_OOPSPEC
from pypy.rlib.jit import JitDriver, hint, JitHintError
from pypy.jit.rainbow.test import test_hotpath



class TestVList(test_hotpath.HotPathTest):
    type_system = "lltype"

    def test_vlist(self):
        myjitdriver = JitDriver(greens = [],
                                reds = ['i', 'tot'])
        def ll_function():
            tot = 0
            i = 1024
            while i > 0:
                i >>= 1
                lst = []
                lst.append(12)
                tot += lst[0]
                myjitdriver.jit_merge_point(tot=tot, i=i)
                myjitdriver.can_enter_jit(tot=tot, i=i)
            return tot
        res = self.run(ll_function, [], threshold=2)
        assert res == ll_function()
        self.check_insns_in_loops({'int_gt': 1, 'int_rshift': 1, 'int_add': 1})

    def test_enter_block(self):
        myjitdriver = JitDriver(greens = [],
                                reds = ['i', 'tot', 'flag'])
        def ll_function(flag):
            tot = 0
            i = 1024
            while i > 0:
                i >>= 1
                lst = []
                lst.append(flag)
                lst.append(131)
                if flag:
                    tot += lst[0]
                else:
                    tot += lst[1]
                myjitdriver.jit_merge_point(tot=tot, i=i, flag=flag)
                myjitdriver.can_enter_jit(tot=tot, i=i, flag=flag)
            return tot
        res = self.run(ll_function, [6], threshold=2)
        assert res == ll_function(6)
        self.check_insns_in_loops({'int_gt': 1, 'int_rshift': 1, 'int_add': 1,
                                   'int_is_true': 1})
        res = self.run(ll_function, [0], threshold=2)
        assert res == ll_function(0)
        self.check_insns_in_loops({'int_gt': 1, 'int_rshift': 1, 'int_add': 1,
                                   'int_is_true': 1})

    def test_merge(self):
        myjitdriver = JitDriver(greens = [],
                                reds = ['i', 'tot', 'flag'])
        def ll_function(flag):
            tot = 0
            i = 1024
            while i > 0:
                i >>= 1
                lst = []
                if flag:
                    lst.append(flag)
                else:
                    lst.append(131)
                tot += lst[-1]
                myjitdriver.jit_merge_point(tot=tot, i=i, flag=flag)
                myjitdriver.can_enter_jit(tot=tot, i=i, flag=flag)
            return tot
        res = self.run(ll_function, [6], threshold=2, policy=P_OOPSPEC)
        assert res == ll_function(6)
        self.check_insns_in_loops({'int_gt': 1, 'int_rshift': 1, 'int_add': 1,
                                   'int_is_true': 1})
        res = self.run(ll_function, [0], threshold=2, policy=P_OOPSPEC)
        assert res == ll_function(0)
        self.check_insns_in_loops({'int_gt': 1, 'int_rshift': 1, 'int_add': 1,
                                   'int_is_true': 1})

    def test_replace(self):
        py.test.skip("port me")
        def ll_function(flag):
            lst = []
            if flag:
                lst.append(12)
            else:
                lst.append(131)
            return lst[-1]
        res = self.interpret(ll_function, [6], [], policy=P_OOPSPEC)
        assert res == 12
        self.check_insns({'int_is_true': 1})
        res = self.interpret(ll_function, [0], [], policy=P_OOPSPEC)
        assert res == 131
        self.check_insns({'int_is_true': 1})

    def test_force(self):
        myjitdriver = JitDriver(greens = [],
                                reds = ['i', 'tot', 'flag'])
        def ll_function(flag):
            i = 1024
            tot = 0
            while i:
                i >>= 1
                lst = []
                lst.append(flag)
                if flag:
                    lst.append(12)
                tot += lst[-1]
                myjitdriver.jit_merge_point(tot=tot, i=i, flag=flag)
                myjitdriver.can_enter_jit(tot=tot, i=i, flag=flag)
            return tot
        res = self.run(ll_function, [6], 2, policy=P_OOPSPEC)
        assert res == ll_function(6)
        res = self.run(ll_function, [0], 2, policy=P_OOPSPEC)
        assert res == ll_function(0)

    def test_oop_vlist(self):
        myjitdriver = JitDriver(greens = [],
                                reds = ['i', 'tot'])
        def ll_function():
            i = 1024
            tot = 0
            while i:
                i >>= 1
                lst = [3, 5]
                five = lst.pop()        # [3]
                lst.append(len(lst))    # [3, 1]
                lst2 = list(lst)
                three = lst.pop(0)      # [1]
                lst.insert(0, 8)        # [8, 1]
                lst.insert(2, 7)        # [8, 1, 7]
                lst.append(not lst)     # [8, 1, 7, 0]
                lst.reverse()           # [0, 7, 1, 8]
                lst3 = lst2 + lst       # [3, 1, 0, 7, 1, 8]
                del lst3[1]             # [3, 0, 7, 1, 8]
                seven = lst3.pop(2)     # [3, 0, 1, 8]
                lst3[0] = 9             # [9, 0, 1, 8]
                nine = lst3.pop(-4)     # [0, 1, 8]
                tot += (len(lst3) * 10000000 +
                        lst3[0]   *  1000000 +
                        lst3[1]   *   100000 +
                        lst3[-1]  *    10000 +
                        five      *     1000 +
                        three     *      100 +
                        seven     *       10 +
                        nine      *        1)
                myjitdriver.jit_merge_point(tot=tot, i=i)
                myjitdriver.can_enter_jit(tot=tot, i=i)
            return tot
        assert ll_function() == 30185379 * 11
        res = self.run(ll_function, [], 2, policy=P_OOPSPEC)
        assert res == 30185379 * 11
        self.check_insns_in_loops({'int_rshift': 1, 'int_add': 1,
                                   'int_is_true': 1})

    def test_alloc_and_set(self):
        myjitdriver = JitDriver(greens = [],
                                reds = ['i', 'tot'])
        def ll_function():
            i = 1024
            tot = 0
            while i:
                i >>= 1
                lst = [0] * 9
                tot += len(lst)
                myjitdriver.jit_merge_point(tot=tot, i=i)
                myjitdriver.can_enter_jit(tot=tot, i=i)
            return tot
        res = self.run(ll_function, [], 2, policy=P_OOPSPEC)
        assert res == 9 * 11
        self.check_insns_in_loops({'int_rshift': 1, 'int_add': 1,
                                   'int_is_true': 1})
        
    def test_lists_deepfreeze(self):
        py.test.skip("port me")
        l1 = [1,2,3,4,5]
        l2 = [6,7,8,9,10]
        def getlist(n):
            if n:
                return l1
            else:
                return l2
        def ll_function(n, i):
            l = getlist(n)
            l = hint(l, deepfreeze=True)
            res = l[i]
            res = hint(res, variable=True)
            return res
        
        res = self.interpret(ll_function, [3, 4], [0, 1], policy=P_OOPSPEC)
        assert res == 5
        self.check_insns({})

    def test_frozen_list(self):
        lst = [5, 7, 9]
        myjitdriver = JitDriver(greens = ['x'],
                                reds = ['i', 'tot'])
        def ll_function(x):
            i = 1024
            tot = 0
            while i:
                i >>= 1
                mylist = hint(lst, deepfreeze=True)
                z = mylist[x]
                hint(z, concrete=True)
                tot += z
                myjitdriver.jit_merge_point(x=x, tot=tot, i=i)
                myjitdriver.can_enter_jit(x=x, tot=tot, i=i)
            return tot

        res = self.run(ll_function, [1], 2, policy=P_OOPSPEC)
        assert res == 7 * 11
        self.check_insns_in_loops({'int_rshift': 1, 'int_add': 1,
                                   'int_is_true': 1})

    def test_frozen_list_indexerror(self):
        lst = [5, 7, 9]
        myjitdriver = JitDriver(greens = ['x'],
                                reds = ['i', 'tot'])
        def ll_function(x):
            i = 1024
            tot = 0
            while i:
                i >>= 1
                mylist = hint(lst, deepfreeze=True)
                try:
                    z = mylist[x]
                except IndexError:
                    tot += -42
                else:
                    hint(z, concrete=True)
                    tot += z
                myjitdriver.jit_merge_point(x=x, tot=tot, i=i)
                myjitdriver.can_enter_jit(x=x, tot=tot, i=i)
            return tot

        res = self.run(ll_function, [4], threshold=2, policy=P_OOPSPEC)
        assert res == -42 * 11
        self.check_insns_in_loops({'int_rshift': 1, 'int_add': 1,
                                   'int_is_true': 1})

    def test_bogus_index_while_compiling(self):
        py.test.skip("implement me")
        class Y:
            pass

        def g(lst, y, n):
            lst = hint(lst, deepfreeze=True)
            if y.flag:
                return lst[n]
            else:
                return -7

        y = Y()
        lst1 = [3, 4, 5]
        lst2 = [6, 2]

        def h(i):
            if i == 1: return lst1
            elif i == 2: return lst2
            else: return []

        def f(n):
            y.flag = n < 3
            g(h(1), y, n)
            y.flag = n < 2
            return g(h(2), y, n)

        res = self.interpret(f, [2], [0], policy=P_OOPSPEC)
        assert res == -7
