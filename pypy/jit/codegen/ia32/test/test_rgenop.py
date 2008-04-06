import py
from pypy.jit.codegen.ia32.rgenop import RI386GenOp
from pypy.jit.codegen.test.rgenop_tests import AbstractRGenOpTestsDirect
from pypy.jit.codegen.test.rgenop_tests import AbstractRGenOpTestsCompile

# for the individual tests see
# ====> ../../test/rgenop_tests.py

class TestRI386GenopDirect(AbstractRGenOpTestsDirect):
    RGenOp = RI386GenOp
    from pypy.jit.codegen.ia32.test.test_operation import RGenOpPacked

class TestRI386GenopCompile(AbstractRGenOpTestsCompile):
    RGenOp = RI386GenOp
    from pypy.jit.codegen.ia32.test.test_operation import RGenOpPacked

    def test_read_frame_float_var_compile(self):
        py.test.skip("no support for addr.float[0]")
