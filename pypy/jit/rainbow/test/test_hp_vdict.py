import py
from pypy.jit.hintannotator.policy import HintAnnotatorPolicy
from pypy.jit.rainbow.test.test_interpreter import InterpretationTest, P_OOPSPEC
from pypy.rlib.jit import JitDriver, hint, JitHintError
from pypy.jit.rainbow.test import test_hotpath


class TestVDict(test_hotpath.HotPathTest):
    type_system = "lltype"

    def test_vdict(self):
        class MyJitDriver(JitDriver):
            greens = []
            reds = ['i', 'tot']
        def ll_function():
            tot = 0
            i = 1024
            while i > 0:
                i >>= 1
                dic = {}
                dic[12] = 34
                dic[13] = 35
                tot += dic[12]
                MyJitDriver.jit_merge_point(tot=tot, i=i)
                MyJitDriver.can_enter_jit(tot=tot, i=i)
            return tot
        res = self.run(ll_function, [], 2, policy=P_OOPSPEC)
        assert res == 34 * 11
        self.check_insns_in_loops({'int_gt': 1, 'int_rshift': 1, 'int_add': 1})

    def test_merge(self):
        class MyJitDriver(JitDriver):
            greens = []
            reds = ['i', 'tot', 'flag']
        def ll_function(flag):
            tot = 0
            i = 1024
            while i > 0:
                i >>= 1
                dic = {}
                dic[11] = 66
                if flag:
                    dic[12] = 34
                else:
                    dic[12] = 35
                dic[13] = 35
                tot += dic[12]
                MyJitDriver.jit_merge_point(tot=tot, i=i, flag=flag)
                MyJitDriver.can_enter_jit(tot=tot, i=i, flag=flag)
            return tot
        res = self.run(ll_function, [True], 2, policy=P_OOPSPEC)
        assert res == 34 * 11
        self.check_insns_in_loops({'int_gt': 1, 'int_rshift': 1, 'int_add': 1})

    def test_vdict_and_vlist(self):
        class MyJitDriver(JitDriver):
            greens = []
            reds = ['i', 'tot']
        def ll_function():
            tot = 0
            i = 1024
            while i > 0:
                i >>= 1
                dic = {}
                lst = [12]
                dic[12] = 34
                dic[13] = 35
                tot += dic[lst.pop()]
                MyJitDriver.jit_merge_point(tot=tot, i=i)
                MyJitDriver.can_enter_jit(tot=tot, i=i)
            return tot
        res = self.run(ll_function, [], 2, policy=P_OOPSPEC)
        assert res == 34 * 11
        self.check_insns_in_loops({'int_gt': 1, 'int_rshift': 1, 'int_add': 1})

    def test_multiple_vdicts(self):
        class MyJitDriver(JitDriver):
            greens = []
            reds = ['i', 'tot']
        def ll_function():
            tot = 0
            i = 1024
            while i > 0:
                i >>= 1
                d1 = {}
                d1[12] = 34
                l1 = [12]
                l2 = ['foo']
                d2 = {}
                d2['foo'] = 'hello'
                tot += d1[l1.pop()] + len(d2[l2.pop()])
                MyJitDriver.jit_merge_point(tot=tot, i=i)
                MyJitDriver.can_enter_jit(tot=tot, i=i)
            return tot
        res = self.run(ll_function, [], 2, policy=P_OOPSPEC)
        assert res == 39 * 11
        self.check_insns_in_loops({'int_gt': 1, 'int_rshift': 1, 'int_add': 1})

    def test_dicts_deepfreeze(self):
        py.test.skip("how do you generate constant arguments?")
        d1 = {1: 123, 2: 54, 3:84}
        d2 = {1: 831, 2: 32, 3:81}
        def getdict(n):
            if n:
                return d1
            else:
                return d2
        class MyJitDriver(JitDriver):
            greens = []
            reds = ['i', 'tot', 'n', 'x']
        def ll_function(n, x):
            tot = 0
            i = 1024
            while i > 0:
                i >>= 1
                d = getdict(n)
                d = hint(d, deepfreeze=True)
                res = d[i]
                res = hint(res, variable=True)
                tot += res
                MyJitDriver.jit_merge_point(tot=tot, i=i, n=n, x=x)
                MyJitDriver.can_enter_jit(tot=tot, i=i, n=n, x=x)
            return tot
        res = self.run(ll_function, [3, 2], 2, policy=P_OOPSPEC)
        assert res == 54 * 11
