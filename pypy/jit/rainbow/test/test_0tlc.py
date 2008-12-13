import py
from pypy.rpython.module.support import LLSupport, OOSupport
from pypy.jit.rainbow.test.test_portal import PortalTest
from pypy.jit.rainbow.test.test_vlist import P_OOPSPEC
from pypy.jit.rainbow.test.test_interpreter import OOTypeMixin
from pypy.tool.sourcetools import func_with_new_name
from pypy.jit.conftest import Benchmark

from pypy.jit.tl import tlc
from pypy.jit.tl.tlopcode import serialize_program, decode_program
from pypy.jit.tl.test.test_tl import FACTORIAL_SOURCE


class BaseTestTLC(PortalTest):
    small = False

    def _get_interp(self):
            
        def interp(llprogram, inputarg):
            from pypy.rpython.annlowlevel import hlstr
            program = hlstr(llprogram)
            bytecode, pool = decode_program(program)
            args = [tlc.IntObj(inputarg)]
            obj = tlc.interp_eval(bytecode, 0, args, pool)
            return obj.int_o()
        return interp

    def exec_code(self, src, inputarg): #, pool=None):
        pool = tlc.ConstantPool()
        bytecode = tlc.compile(src, pool)
        program = serialize_program(bytecode, pool)
        llprogram = self.to_rstr(program)
        interp = self._get_interp()
        res = self.timeshift_from_portal(interp,
                                         tlc.interp_eval,
                                         [llprogram, inputarg],
                                         policy=P_OOPSPEC)
        return res

    def test_factorial(self):
        res = self.exec_code(FACTORIAL_SOURCE, 5)
        assert res == 120
        self.check_insns(malloc=1)

    def test_nth_item(self):
        # get the nth item of a chained list
        code = """
            NIL
            PUSH 40
            CONS
            PUSH 20
            CONS
            PUSH 10
            CONS
            PUSHARG
            DIV
        """
        res = self.exec_code(code, 1)
        assert res == 20

    def test_getattr(self):
        code = """
            NEW foo,bar
            PICK 0
            PUSH 42
            SETATTR bar,
            GETATTR bar,
        """
        res = self.exec_code(code, 0)
        assert res == 42
        self.check_insns(malloc=1, direct_call=0)

    def test_method(self):
        code = """
            NEW foo,meth=meth
            PICK 0
            PUSH 40
            SETATTR foo
            PUSH 2
            SEND meth/1
            RETURN
        meth:
            PUSHARG
            GETATTR foo
            PUSHARGN 1
            ADD
            RETURN
        """
        res = self.exec_code(code, 0)
        assert res == 42

class TestLLType(BaseTestTLC):
    type_system = "lltype"
    to_rstr = staticmethod(LLSupport.to_rstr)

class TestOOType(OOTypeMixin, BaseTestTLC):
    type_system = "ootype"
    to_rstr = staticmethod(OOSupport.to_rstr)
