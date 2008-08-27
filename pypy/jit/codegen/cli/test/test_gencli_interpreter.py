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
    
    pass
