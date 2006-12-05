import py
from pypy.jit.codegen.llvm.rgenop import RLLVMGenOp
from pypy.jit.codegen.test.rgenop_tests import AbstractRGenOpTests
from pypy.rpython.lltypesystem import lltype
from ctypes import c_void_p, cast, CFUNCTYPE, c_int


FUNC = lltype.FuncType([lltype.Signed], lltype.Signed)

def make_adder(rgenop, n):
    # 'return x+n'
    sigtoken = rgenop.sigToken(FUNC)
    builder, gv_add_one, [gv_x] = rgenop.newgraph(sigtoken, "adder")
    #note: entrypoint (gv_add_one.value) gets updated by builder.end() (don't use before that!)
    gv_result = builder.genop2("int_add", gv_x, rgenop.genconst(n))
    builder.finish_and_return(sigtoken, gv_result)
    builder.end()
    return gv_add_one

def test_adder_direct():
    rgenop = RLLVMGenOp()
    gv_add_5 = make_adder(rgenop, 5)
    fnptr = cast(c_void_p(gv_add_5.value), CFUNCTYPE(c_int, c_int))
    #fnptr = gv_add_5.revealconst(lltype.Ptr(FUNC))
    res = fnptr(37)
    assert res == 42


#class TestRLLVMGenop(AbstractRGenOpTests):
#    RGenOp = RLLVMGenOp

