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
        def interp(llbytecode, pc, inputarg):
            from pypy.rpython.annlowlevel import hlstr
            bytecode = hlstr(llbytecode)
            return tlc.interp_without_call(bytecode, pc, inputarg)
        
        to_rstr = self.to_rstr
        def build_bytecode(s):
            result = ''.join([chr(int(t)) for t in s.split(',')])
            return to_rstr(result)
        interp.convert_arguments = [build_bytecode, int, int]
        
        return interp


    def test_factorial(self):
        code = tlc.compile(FACTORIAL_SOURCE)
        bytecode = ','.join([str(ord(c)) for c in code])

        n = 5
        expected = 120
        
        interp = self._get_interp()
        res = self.timeshift_from_portal(interp,
                                         tlc.interp_eval_without_call,
                                         [bytecode, 0, n],
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
                                         [bytecode, 0, 1],
                                         policy=P_OOPSPEC)#, backendoptimize=True)
        assert res == 20


class TestLLType(BaseTestTLC):
    type_system = "lltype"
    to_rstr = staticmethod(LLSupport.to_rstr)

class TestOOType(OOTypeMixin, BaseTestTLC):
    type_system = "ootype"
    to_rstr = staticmethod(OOSupport.to_rstr)
