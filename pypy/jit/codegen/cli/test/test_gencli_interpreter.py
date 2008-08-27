import py
from pypy.jit.codegen.cli.rgenop import RCliGenOp
from pypy.jit.rainbow.test.test_interpreter import TestOOType as RainbowTest
from pypy.translator.cli.test.runtest import compile_graph


class CompiledCliMixin(object):
    RGenOp = RCliGenOp
    translate_support_code = True

    def interpret(self, ll_function, values, opt_consts=[], *args, **kwds):
        values, writer, jitcode = self.convert_and_serialize(ll_function, values, **kwds)
        translator = self.rtyper.annotator.translator
        func = compile_graph(self.rewriter.portal_entry_graph, translator)
        return func(*values)


    def check_insns(self, expected=None, **counts):
        "Cannot check instructions in the generated assembler."

class TestRainbowCli(CompiledCliMixin, RainbowTest):

    # for the individual tests see
    # ====> ../../../rainbow/test/test_interpreter.py
    
    def skip(self):
        py.test.skip('in progress')

    test_simple_struct = skip
    test_complex_struct = skip
    test_degenerate_with_voids = skip
    test_arith_plus_minus = skip
    test_plus_minus = skip
    test_red_virtual_container = skip
    test_red_propagate = skip
    test_merge_structures = skip
    test_green_with_side_effects = skip
    test_compile_time_const_tuple = skip
    test_green_deepfrozen_oosend = skip
    test_direct_oosend_with_green_self = skip
    test_builtin_oosend_with_green_args = skip
    test_residual_red_call = skip
    test_residual_red_call_with_exc = skip
    test_simple_meth = skip
    test_simple_red_meth = skip
    test_simple_red_meth_vars_around = skip
    test_yellow_meth_with_green_result = skip
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
    test_red_int_add_ovf = skip
    test_nonzeroness_assert_while_compiling = skip
    test_segfault_while_compiling = skip
    test_learn_nonzeroness = skip
    test_freeze_booleffects_correctly = skip
    test_ptrequality = skip
    test_void_args = skip
    test_red_isinstance = skip
    test_red_isinstance_degenerated = skip
    test_simple_array = skip
    test_arraysize = skip
    test_setarrayitem = skip
    test_red_array = skip
    test_degenerated_before_return = skip
    test_degenerated_before_return_2 = skip
    test_degenerated_at_return = skip
    test_degenerated_via_substructure = skip
    test_red_subclass = skip
