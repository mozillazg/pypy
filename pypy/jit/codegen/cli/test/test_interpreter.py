import py
from pypy.jit.codegen.cli.rgenop import RCliGenOp
from pypy.jit.codegen.dump.rgenop import RDumpGenOp
from pypy.jit.rainbow.test.test_interpreter import TestOOType as RainbowTest

class TestRainbowCli(RainbowTest):
    RGenOp = RCliGenOp
    RGenOp = RDumpGenOp

    # for the individual tests see
    # ====> ../../../rainbow/test/test_interpreter.py

    def run_generated(self, writer, generated, residualargs, **kwds):
        if 'check_raises' not in kwds:
            res = generated.DynamicInvoke(residualargs)
        else:
            assert False, 'TODO'
        return res

    def check_insns(self, expected=None, **counts):
        "Cannot check instructions in the generated assembler."

    def skip(self):
        py.test.skip('in progress')

    test_simple_opt_const_propagation1 = skip
    test_simple_opt_const_propagation2 = skip
    #test_red_switch = skip
    test_merge = skip
    test_loop_merging = skip
    test_loop_merging2 = skip
    test_two_loops_merging = skip
    test_green_across_split = skip
    test_merge_const_before_return = skip
    test_merge_3_redconsts_before_return = skip
    test_merge_const_at_return = skip
    test_call_4 = skip
    test_call_5 = skip
    test_call_6 = skip
    test_green_call = skip
    test_green_call_void_return = skip
    test_split_on_green_return = skip
    test_simple_struct = skip
    test_complex_struct = skip
    test_simple_array = skip
    test_arraysize = skip
    test_degenerate_with_voids = skip
    test_red_virtual_container = skip
    test_setarrayitem = skip
    test_red_propagate = skip
    test_merge_structures = skip
    test_green_with_side_effects = skip
    test_compile_time_const_tuple = skip
    test_green_deepfrozen_oosend = skip
    test_direct_oosend_with_green_self = skip
    test_residual_red_call = skip
    test_residual_red_call_with_exc = skip
    test_simple_meth = skip
    test_simple_red_meth = skip
    test_simple_red_meth_vars_around = skip
    test_simple_indirect_call = skip
    test_normalize_indirect_call = skip
    test_normalize_indirect_call_more = skip
    test_green_char_at_merge = skip
    test_self_referential_structures = skip
    test_known_nonzero = skip
    test_debug_assert_ptr_nonzero = skip
    test_indirect_red_call = skip
    test_indirect_red_call_with_exc = skip
    test_indirect_gray_call = skip
    test_indirect_residual_red_call = skip
    test_constant_indirect_red_call = skip
    test_constant_indirect_red_call_no_result = skip
    test_indirect_sometimes_residual_pure_red_call = skip
    test_indirect_sometimes_residual_pure_but_fixed_red_call = skip
    test_manual_marking_of_pure_functions = skip
    test_red_int_add_ovf = skip
    test_nonzeroness_assert_while_compiling = skip
    test_segfault_while_compiling = skip
    test_switch = skip
    test_switch_char = skip
    test_learn_boolvalue = skip
    test_learn_nonzeroness = skip
    test_freeze_booleffects_correctly = skip
    test_ptrequality = skip
    test_green_ptrequality = skip
    test_void_args = skip
    test_degenerated_before_return = skip
    test_degenerated_before_return_2 = skip
    test_degenerated_at_return = skip
    test_degenerated_via_substructure = skip
    test_red_subclass = skip
