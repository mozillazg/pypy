from pypy.jit.codegen.model import AbstractRGenOp, GenLabel, GenBuilder
from pypy.jit.codegen.model import GenVar, GenConst, CodeGenSwitch

class RLLVMGenOp(AbstractRGenOp):
    pass

global_rgenop = RLLVMGenOp()
#XXX RLLVMGenOp.constPrebuiltGlobal = global_rgenop.genconst
