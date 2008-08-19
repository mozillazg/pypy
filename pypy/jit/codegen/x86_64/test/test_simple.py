import py
from pypy.jit.codegen.x86_64.rgenop import RX86_64GenOp
from pypy.rpython.lltypesystem import lltype
from ctypes import cast, c_void_p, CFUNCTYPE, c_long, c_double
from pypy.jit.codegen.x86_64.objmodel import Register64, Immediate32
from pypy.jit.codegen.test.rgenop_tests import AbstractTestBase
from pypy.jit.codegen.test.rgenop_tests import AbstractRGenOpTestsDirect

rgenop = RX86_64GenOp()

def make_testbuilder():
    FUNC = lltype.FuncType([lltype.Signed, lltype.Signed], lltype.Signed) #the funtiontype(arguments,returntype) of the graph we will create
    token = rgenop.sigToken(FUNC)
    builder, entrypoint, inputargs_gv = rgenop.newgraph(token, "test")
    builder.start_writing() 
    ctypestypes = [c_long, c_long]
    fp = cast(c_void_p(entrypoint.value),
              CFUNCTYPE(c_long, *ctypestypes))
    return builder, fp, inputargs_gv, token
        
def test_add():
    builder, fp, inputargs_gv, token = make_testbuilder()
    genv0 = inputargs_gv[0] #the first argument "place"
    genv1 = inputargs_gv[1] 
    genv_result = builder.genop2("int_add", genv0, genv1) #creates the addition and returns the place(register) of the result in genv_result
    builder.finish_and_return(token, genv_result)
    ten = fp(4, 6)
    assert ten == 10
    print ten
    
def test_ret():
    builder, fp, inputargs_gv, token = make_testbuilder()
    builder.finish_and_return(token, inputargs_gv[0])
    print repr("".join(builder.mc._all))
    four = fp(4, 17)
    assert four == 4
    print four
    
def test_sub():
    builder, fp, inputargs_gv, token = make_testbuilder()
    genv0 = inputargs_gv[0] #the first argument "place"
    genv1 = inputargs_gv[1] 
    genv_result = builder.genop2("int_sub", genv0, genv1) #creates the addition and returns the place(register) of the result in genv_result
    builder.finish_and_return(token, genv_result)
    four = fp(10, 6)
    assert four == 4
    print four