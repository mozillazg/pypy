import py
from pypy.jit.codegen.ia32.rgenop import RI386GenOp
from pypy.jit.codegen.test.rgenop_tests import AbstractRGenOpTestsDirect
from pypy.jit.codegen.test.rgenop_tests import AbstractRGenOpTestsCompile

# for the individual tests see
# ====> ../../test/rgenop_tests.py

class TestRI386GenopDirect(AbstractRGenOpTestsDirect):
    RGenOp = RI386GenOp
    from pypy.jit.codegen.ia32.test.test_operation import RGenOpPacked

    def skipped(self):
        py.test.skip("unsupported")

    # frame access related
    test_genconst_from_frame_var_direct = skipped
    test_write_frame_place_direct = skipped
    test_write_lots_of_frame_places_direct = skipped
    test_read_frame_place_direct = skipped
    test_frame_vars_like_the_frontend_direct = skipped
    test_demo_f1_direct = skipped

class TestRI386GenopCompile(AbstractRGenOpTestsCompile):
    RGenOp = RI386GenOp
    from pypy.jit.codegen.ia32.test.test_operation import RGenOpPacked

    def setup_class(cls):
        py.test.skip("skip compilation tests")
