from pypy.jit.codegen.ia32.rgenop import RI386GenOp
from pypy.jit.codegen.test.rgenop_tests import AbstractRGenOpTestsDirect
from pypy.jit.codegen.test.rgenop_tests import AbstractRGenOpTestsCompile

# for the individual tests see
# ====> ../../test/rgenop_tests.py

class TestRI386GenopDirect(AbstractRGenOpTestsDirect):
    RGenOp = RI386GenOp
    from pypy.jit.codegen.i386.test.test_operation import RGenOpPacked

class TestRI386GenopCompile(AbstractRGenOpTestsCompile):
    RGenOp = RI386GenOp
    from pypy.jit.codegen.i386.test.test_operation import RGenOpPacked

    def setup_class(cls):
        py.test.skip("skip compilation tests")
