import py
from pypy.rpython.lltypesystem import lltype
from pypy.jit.codegen.cli.rgenop import RCliGenOp
from pypy.jit.rainbow.test.test_interpreter import TestOOType as RainbowTest
from pypy.translator.cli.test.runtest import compile_graph, get_annotation
from pypy.annotation import model as annmodel

def wrap_convert_arguments(callee, convert_arguments):
    indexes = range(len(convert_arguments))
    convnames = ['conv%d' % i for i in indexes]
    argnames =  ['arg%d' % i for i in indexes]
    varnames =  ['var%d' % i for i in indexes]
    lines = []
    lines.append('def fn(%s):' % ', '.join(argnames))
    for var, conv, arg in zip(varnames, convnames, argnames):
        lines.append('    %s = %s(%s)' % (var, conv, arg))
    lines.append('    return callee(%s)' % ', '.join(varnames))
    
    src = py.code.Source('\n'.join(lines))
    mydict = (dict(zip(convnames, convert_arguments)))
    mydict['callee'] = callee
    exec src.compile() in mydict
    return mydict['fn']

class CompiledCliMixin(object):
    RGenOp = RCliGenOp
    translate_support_code = True

    def interpret(self, ll_function, values, opt_consts=[], *args, **kwds):
        newvalues, writer, jitcode = self.convert_and_serialize(ll_function, values, **kwds)
        translator = self.rtyper.annotator.translator
        graph = self.rewriter.portal_entry_graph
        
        if hasattr(ll_function, 'convert_arguments'):
            fn = wrap_convert_arguments(self.rewriter.portal_entry, ll_function.convert_arguments)
            FUNC = self.rewriter.PORTAL_FUNCTYPE
            args_s = [get_annotation(value) for value in values]
            s_result = annmodel.lltype_to_annotation(FUNC.RESULT)
            graph = self.rewriter.annhelper.getgraph(fn, args_s, s_result)
            self.rewriter.annhelper.finish()

        func = compile_graph(graph, translator, nowrap=True)
        return func(*values)


    def check_insns(self, expected=None, **counts):
        "Cannot check instructions in the generated assembler."

class TestRainbowCli(CompiledCliMixin, RainbowTest):

    # for the individual tests see
    # ====> ../../../rainbow/test/test_interpreter.py
    
    def skip(self):
        py.test.skip('in progress')

    def test_convert_arguments(self):
        def ll_function(x):
            return x+40
        def getlen(string):
            return len(string)
        ll_function.convert_arguments = [getlen]
        res = self.interpret(ll_function, ["xx"], [])
        assert res == 42

    def test_degenerate_with_voids(self):
        # the original test can't be executed when compiled because we can't
        # inspect the content of an instance return an instance as a result;
        # instead, we just check the class name
        S = self.GcStruct('S', ('y', lltype.Void),
                               ('x', lltype.Signed))
        malloc = self.malloc
        def ll_function():
            s = malloc(S)
            s.x = 123
            return s
        res = self.interpret(ll_function, [], [])
        assert res.class_name == 'S'

    def test_arith_plus_minus(self):
        py.test.skip("Cannot work unless we add support for constant arguments in compiled tests")

    def test_compile_time_const_tuple(self):
        py.test.skip("Fails, and it seems to be related to missing support for constant arguments")

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
