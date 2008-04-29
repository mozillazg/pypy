import py
from pypy.rpython.lltypesystem import lltype
from pypy.jit.codegen.llgraph.rgenop import RGenOp
from pypy.jit.codegen.llgraph.llimpl import testgengraph
from pypy.jit.codegen.test.rgenop_tests import AbstractRGenOpTestsDirect
from pypy.jit.codegen.test.rgenop_tests import AbstractRGenOpTestsCompile
from pypy.rpython.test.test_llinterp import gengraph, interpret

# for the individual tests see
# ====> ../../test/rgenop_tests.py

class BaseLLGraphRGenop(object):
    RGenOp = RGenOp
    RGenOpPacked = RGenOp

    def setup_method(self, meth):
        if 'ovfcheck' in meth.__name__:
            py.test.skip("no chance (the llinterpreter has no rtyper)")
        super(BaseLLGraphRGenop, self).setup_method(meth)

    def getcompiled(self, runner, argtypes, annotatorpolicy):
        def quasi_compiled_runner(*args):
            return interpret(runner, args, policy=annotatorpolicy)
        return quasi_compiled_runner

    def directtesthelper(self, FUNC, func):
        from pypy.annotation import model as annmodel
        argtypes = [annmodel.lltype_to_annotation(T) for T in FUNC.TO.ARGS]
        t, rtyper, graph = gengraph(func, argtypes)
        return rtyper.getcallable(graph)
    

class TestLLGraphRGenopDirect(BaseLLGraphRGenop, AbstractRGenOpTestsDirect):

    def test_cast_raising(self):
        py.test.skip('fixme')

class TestLLGraphRGenopCompile(BaseLLGraphRGenop, AbstractRGenOpTestsCompile):
    pass

def test_not_calling_end_explodes():
    F1 = lltype.FuncType([lltype.Signed], lltype.Signed)
    rgenop = RGenOp()
    sigtoken = rgenop.sigToken(F1)
    builder, gv_adder, [gv_x] = rgenop.newgraph(sigtoken, "adder")
    builder.start_writing()
    gv_result = builder.genop2("int_add", gv_x, rgenop.genconst(5))
    builder.finish_and_return(sigtoken, gv_result)
    #builder.end() <--- the point
    ptr = gv_adder.revealconst(lltype.Ptr(F1))
    py.test.raises(AssertionError, "testgengraph(ptr._obj.graph, [1])")
