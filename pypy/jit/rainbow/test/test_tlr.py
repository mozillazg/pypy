from pypy.rpython.module.support import LLSupport, OOSupport
from pypy.jit.rainbow.test.test_portal import PortalTest
from pypy.jit.rainbow.test.test_vlist import P_OOPSPEC
from pypy.tool.sourcetools import func_with_new_name

from pypy.jit.tl import tlr


class BaseTestTLR(PortalTest):

    def test_tlr(self):
        bytecode = ','.join([str(ord(c)) for c in tlr.SQUARE])
        to_rstr = self.to_rstr

        def build_bytecode(s):
            result = ''.join([chr(int(t)) for t in s.split(',')])
            return to_rstr(result)

        def ll_function(llbytecode, arg):
            from pypy.rpython.annlowlevel import hlstr
            # needed so that both lltype and ootype can index the string with []
            bytecode = hlstr(llbytecode)
            return tlr.interpret(bytecode, arg)
        ll_function.convert_arguments = [build_bytecode, int]

        res = self.timeshift_from_portal(ll_function, tlr.interpret, [bytecode, 1764],
                             policy=P_OOPSPEC)
        assert res == 3111696

        res = self.timeshift_from_portal(ll_function, tlr.interpret, [bytecode, 9],
                             policy=P_OOPSPEC)
        assert res == 81

class TestLLType(BaseTestTLR):
    type_system = "lltype"
    to_rstr = staticmethod(LLSupport.to_rstr)

class TestOOType(BaseTestTLR):
    type_system = "ootype"
    to_rstr = staticmethod(OOSupport.to_rstr)
