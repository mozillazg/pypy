import py
from pypy.jit.hintannotator.policy import HintAnnotatorPolicy
from pypy.jit.rainbow.test.test_interpreter import InterpretationTest, P_OOPSPEC
from pypy.jit.rainbow.test.test_interpreter import OOTypeMixin
from pypy.rlib.jit import hint


class VDictTest(InterpretationTest):
    type_system = "lltype"

    def test_vdict(self):
        def ll_function():
            dic = {}
            dic[12] = 34
            dic[13] = 35
            return dic[12]
        res = self.interpret(ll_function, [], [], policy=P_OOPSPEC)
        assert res == 34
        self.check_insns({})

    def test_merge(self):
        def ll_function(flag):
            dic = {}
            if flag:
                dic[12] = 34
            else:
                dic[12] = 35
            dic[13] = 35
            return dic[12]

        res = self.interpret(ll_function, [True], [], policy=P_OOPSPEC)
        assert res == 34
        self.check_insns({})

    def test_vdict_and_vlist(self):
        def ll_function():
            dic = {}
            lst = [12]
            dic[12] = 34
            dic[13] = 35
            return dic[lst.pop()]
        res = self.interpret(ll_function, [], [], policy=P_OOPSPEC)
        assert res == 34
        self.check_insns({})

    def test_multiple_vdicts(self):
        def ll_function():
            d1 = {}
            d1[12] = 34
            l1 = [12]
            l2 = ['foo']
            d2 = {}
            d2['foo'] = 'hello'
            return d1[l1.pop()] + len(d2[l2.pop()])
        res = self.interpret(ll_function, [], [], policy=P_OOPSPEC)
        assert res == 39
        self.check_insns({})

    def test_dicts_deepfreeze(self):
        d1 = {1: 123, 2: 54, 3:84}
        d2 = {1: 831, 2: 32, 3:81}
        def getdict(n):
            if n:
                return d1
            else:
                return d2
        def ll_function(n, i):
            d = getdict(n)
            d = hint(d, deepfreeze=True)
            res = d[i]
            res = hint(res, variable=True)
            return res
        
        res = self.interpret(ll_function, [3, 2], [0, 1], policy=P_OOPSPEC)
        assert res == 54
        self.check_insns({})



    def test_dict_escape(self):
        d1 = {1: 123, 2: 54, 3:84}
        d2 = {1: 831, 2: 32, 3:81}

        def getdict(n):
            if n:
                return d1
            else:
                return d2

        class A:
            pass

        def f(n):
            d = getdict(n)
            x = A()
            x.d = d
            return x

        a = []

        def ll_function(n, i):
            x = f(n)
            a.append(x)
            d = hint(x.d, deepfreeze=True)
            res = d[i]
            res = hint(res, variable=True)
            return res

        res = self.interpret(ll_function, [3, 2], [0, 1], policy=P_OOPSPEC)
        assert res == 54

class TestOOType(OOTypeMixin, VDictTest):
    type_system = "ootype"

class TestLLType(VDictTest):
    type_system = "lltype"
