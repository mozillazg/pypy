import py
from pypy.jit.codegen.llvm.rgenop import RLLVMGenOp
from pypy.jit.codegen.test.rgenop_tests import AbstractRGenOpTests
from sys import platform


class TestRLLVMGenop(AbstractRGenOpTests):
    RGenOp = RLLVMGenOp

    def compile(self, runner, argtypes):
        if platform == 'darwin':
            py.test.skip('Compilation for Darwin not fully support yet (static/dyn lib issue')

        super(TestRLLVMGenop, self).compile(runner.argtypes)

    def test_branching_direct(self):
        py.test.skip('WIP')

    test_goto_direct = test_branching_direct
    test_if_direct = test_branching_direct
    test_switch_direct = test_branching_direct
    test_large_switch_direct = test_branching_direct
    test_fact_direct = test_branching_direct
