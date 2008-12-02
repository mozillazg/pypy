import py
from pypy.rpython.module.support import LLSupport, OOSupport
from pypy.jit.rainbow.test.test_portal import PortalTest
from pypy.jit.rainbow.test.test_vlist import P_OOPSPEC
from pypy.jit.rainbow.test.test_interpreter import OOTypeMixin
from pypy.tool.sourcetools import func_with_new_name
from pypy.jit.conftest import Benchmark

from pypy.jit.tl import tlc
from pypy.jit.tl.test.test_tl import FACTORIAL_SOURCE


class BaseTestTLC(PortalTest):
    small = False

    def _get_interp(self):
        def decode_strlist(s):
            lists = s.split('|')
            return [lst.split(',') for lst in lists]
        
        def interp(llbytecode, pc, inputarg, llstrlists):
            from pypy.rpython.annlowlevel import hlstr
            bytecode = hlstr(llbytecode)
            strlists = hlstr(llstrlists)
            pool = tlc.ConstantPool()
            pool.strlists = decode_strlist(strlists)
            obj = tlc.interp_eval_without_call(bytecode,
                                               pc,
                                               tlc.IntObj(inputarg),
                                               pool)
            return obj.int_o()
        
        to_rstr = self.to_rstr
        def build_bytecode(s):
            result = ''.join([chr(int(t)) for t in s.split(',')])
            return to_rstr(result)
        def build_strlist(items):
            lists = [','.join(lst) for lst in items]
            return to_rstr('|'.join(lists))
        interp.convert_arguments = [build_bytecode, int, int, build_strlist]
        
        return interp


    def test_factorial(self):
        code = tlc.compile(FACTORIAL_SOURCE)
        bytecode = ','.join([str(ord(c)) for c in code])

        n = 5
        expected = 120
        
        interp = self._get_interp()
        res = self.timeshift_from_portal(interp,
                                         tlc.interp_eval_without_call,
                                         [bytecode, 0, n, []],
                                         policy=P_OOPSPEC)#, backendoptimize=True)
        assert res == expected
        self.check_insns(malloc=1)

    def test_nth_item(self):
        # get the nth item of a chained list
        code = tlc.compile("""
            NIL
            PUSH 40
            CONS
            PUSH 20
            CONS
            PUSH 10
            CONS
            PUSHARG
            DIV
        """)
        bytecode = ','.join([str(ord(c)) for c in code])

        interp = self._get_interp()
        res = self.timeshift_from_portal(interp,
                                         tlc.interp_eval_without_call,
                                         [bytecode, 0, 1, []],
                                         policy=P_OOPSPEC)#, backendoptimize=True)
        assert res == 20

    def test_getattr(self):
        from pypy.jit.tl.tlc import interp_eval, nil, ConstantPool
        pool = ConstantPool()
        code = tlc.compile("""
            NEW foo,bar
            PICK 0
            PUSH 42
            SETATTR bar,
            GETATTR bar,
        """, pool)
        bytecode = ','.join([str(ord(c)) for c in code])
        interp = self._get_interp()
        res = self.timeshift_from_portal(interp,
                                         tlc.interp_eval_without_call,
                                         [bytecode, 0, 0, pool.strlists],
                                         policy=P_OOPSPEC)
        assert res == 42
        self.check_insns(malloc=1)        



class TestLLType(BaseTestTLC):
    type_system = "lltype"
    to_rstr = staticmethod(LLSupport.to_rstr)

class TestOOType(OOTypeMixin, BaseTestTLC):
    type_system = "ootype"
    to_rstr = staticmethod(OOSupport.to_rstr)
