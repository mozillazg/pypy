import py
from pypy.jit.rainbow.test.test_promotion import TestOOType as PromotionTest
from pypy.jit.codegen.cli.test.test_gencli_interpreter import CompiledCliMixin

class TestPromotionCli(CompiledCliMixin, PromotionTest):

    # for the individual tests see
    # ====> ../../../rainbow/test/test_promotion.py

    pass
