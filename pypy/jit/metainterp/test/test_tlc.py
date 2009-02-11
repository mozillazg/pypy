import py
from pypy.rpython.module.support import LLSupport
from pypy.rlib.jit import hint

from pypy.jit.tl import tlc

from pypy.jit.metainterp.test.test_basic import OOJitMixin, LLJitMixin


class TLCTests:

    def _get_interp(self, bytecode, pool):
        def interp(inputarg):
            args = [tlc.IntObj(inputarg)]
            obj = tlc.interp_eval(bytecode, 0, args, pool)
            return obj.int_o()
        return interp

    def exec_code(self, src, inputarg):
        pool = tlc.ConstantPool()
        bytecode = tlc.compile(src, pool)
        interp = self._get_interp(bytecode, pool)
        return self.meta_interp(interp, [inputarg], view=False)

    def test_method(self):
        code = """
            NEW foo,meth=meth
            PICK 0
            PUSHARG
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
        res = self.exec_code(code, 40)
        assert res == 42

    def test_accumulator(self):
        py.test.skip("takes too long and does not optimize :-(")
        path = py.path.local(tlc.__file__).dirpath('accumulator.tlc.src')
        code = path.read()
        res = self.exec_code(code, 20)
        assert res == sum(range(20))
        res = self.exec_code(code, -10)
        assert res == 10


class TestLLtype(TLCTests, LLJitMixin):
    pass
