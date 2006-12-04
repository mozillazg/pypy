import py
from pypy.jit.codegen.llvm.rgenop import RLLVMGenOp
from pypy.jit.codegen.test.rgenop_tests import AbstractRGenOpTests


py.test.skip("WIP")

class TestRLLVMGenop(AbstractRGenOpTests):
    RGenOp = RLLVMGenOp
