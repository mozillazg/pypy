import py
from pypy.jit.codegen.cli.test.test_interpreter import CliMixin
from pypy.jit.rainbow.test.test_promotion import TestOOType as PromotionTest

class TestPromotionCli(CliMixin, PromotionTest):

    # for the individual tests see
    # ====> ../../../rainbow/test/test_promotion.py

    def skip(self):
        py.test.skip('in progress')

    test_simple_promotion = skip
    test_many_promotions = skip
    test_promote_inside_call = skip
    test_promote_inside_call2 = skip
    test_two_promotions = skip
    test_mixed_merges = skip
    test_green_across_global_mp = skip
    test_promote_bug_1 = skip
    test_exception_after_promotion = skip
    test_promote_in_yellow_call = skip
    test_more_promote_in_yellow_call = skip
    test_two_promotions_in_call = skip
    test_more_promotes = skip
    test_raise_result_mixup_some_more = skip
    test_raise_result_mixup = skip
    test_remembers_across_mp = skip
    test_promote_after_yellow_call = skip
    test_virtual_list_copy = skip
    test_vstruct_unfreeze = skip
    test_promote_after_call = skip
    test_merge_then_promote = skip
    test_promote_class = skip
    test_read___class___after_promotion = skip
