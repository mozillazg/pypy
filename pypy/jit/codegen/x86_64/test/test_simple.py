# Some opcode simple tests

import py
from pypy.jit.codegen.x86_64.rgenop import RX86_64GenOp
from pypy.rpython.lltypesystem import lltype
from ctypes import cast, c_void_p, CFUNCTYPE, c_long, c_double
from pypy.jit.codegen.x86_64.objmodel import Register64, Immediate32
from pypy.jit.codegen.test.rgenop_tests import AbstractTestBase
from pypy.jit.codegen.test.rgenop_tests import AbstractRGenOpTestsDirect

rgenop = RX86_64GenOp()

def make_testbuilder(num_of_args):
    FUNC = lltype.FuncType([lltype.Signed]*num_of_args, lltype.Signed) #the funtiontype(arguments,returntype) of the graph we will create
    token = rgenop.sigToken(FUNC)
    builder, entrypoint, inputargs_gv = rgenop.newgraph(token, "test")
    builder.start_writing() 
    ctypestypes = [c_long]*num_of_args
    fp = cast(c_void_p(entrypoint.value),
              CFUNCTYPE(c_long, *ctypestypes))
    return builder, fp, inputargs_gv, token
    
class TestSimple():   
        
    def test_add_big_num(self):
        builder, fp, inputargs_gv, token = make_testbuilder(2)
        genv0 = inputargs_gv[0] #the first argument "location"
        genv1 = inputargs_gv[1] 
        genv_result = builder.genop2("int_add", genv0, genv1) #creates the addition and returns the place(register) of the result in genv_result
        builder.finish_and_return(token, genv_result)
        num = fp(1280, 20)
        assert num == 1300
        num = fp(1280, 1000)
        assert num == 2280
        num = fp(1280, -80)
        assert num == 1200
        
    def test_add_twice(self):
        builder, fp, inputargs_gv, token = make_testbuilder(2)
        genv0 = inputargs_gv[0] #the first argument "location"
        genv1 = inputargs_gv[1] 
        genv2 = builder.genop2("int_add", genv0, genv1) 
        genv_result = builder.genop2("int_add", genv2, genv1) 
        builder.finish_and_return(token, genv_result)
        result = fp(4, 6) # 4+6+6= 16
        assert result == 16
        result = fp(2,12) # 2+12+12= 26
        assert result == 26
        result = fp(10,-2) # 10+(-2)+(-2) = 6
        assert result == 6
        result = fp(-4,0) # -4 +0+0 = -4
        assert result == -4
        result = fp(0,-4) # 0+(-4)+(-4) = -8
        assert result == -8
        result = fp(1280,500) # 1280+500+500=2280
        assert result == 2280
        result = fp(0,252) # 0+252+252= 504
        assert result == 504 #==0000:0001:1111:1000

    def test_tripple_add(self):
        builder, fp, inputargs_gv, token = make_testbuilder(2)
        genv0 = inputargs_gv[0] 
        genv1 = inputargs_gv[1] 
        genv2 = builder.genop2("int_add", genv0, genv1) 
        genv3 = builder.genop2("int_add", genv2, genv1) 
        genv_result = builder.genop2("int_add", genv3, genv1) 
        builder.finish_and_return(token, genv_result)
        result = fp(4, 6) # 4+6+6+6= 22
        assert result == 22
        result = fp(2,12) # 2+12+12+12= 38
        assert result == 38
        result = fp(10,-2) # 10+(-2)+(-2)+(-2) = 4
        assert result == 4
        result = fp(-4,0) # -4 +0+0+0 = -4
        assert result == -4
        result = fp(0,-4) # 0+(-4)+(-4)+(-4) = -12
        assert result == -12
        result = fp(1280,500) # 1280+500+500+500=2780
        assert result == 2780
        result = fp(0,252) # 0+252+252= 756
        assert result == 756 #==0000:0001:1111:1000
        
    def test_add(self):
        builder, fp, inputargs_gv, token = make_testbuilder(2)
        genv0 = inputargs_gv[0] #the first argument "location"
        genv1 = inputargs_gv[1] 
        genv_result = builder.genop2("int_add", genv0, genv1) #creates the addition and returns the place(register) of the result in genv_result
        builder.finish_and_return(token, genv_result)
        ten = fp(4, 6) # 4+6= 10
        assert ten == 10
        print ten
        
    def test_add_neg(self):
        builder, fp, inputargs_gv, token = make_testbuilder(2)
        genv0 = inputargs_gv[0] #the first argument "location"
        genv1 = inputargs_gv[1] 
        genv_result = builder.genop2("int_add", genv0, genv1) #creates the addition and returns the place(register) of the result in genv_result
        builder.finish_and_return(token, genv_result)
        ten = fp(-4, -6)
        assert ten == -10
        print ten    
        four = fp(-4,0)
        assert four == -4
        print four
        four = fp(0,-4)
        assert four == -4
        print four
        two = fp(-4, 6)
        assert two == 2
        print two
        two = fp(4, -6)
        assert two == -2
        print two
        
    def test_add_imm32(self):
        builder, fp, inputargs_gv, token = make_testbuilder(1)
        genv0 = inputargs_gv[0] #the first argument "location"
        genv_result = builder.genop2("int_add", genv0, rgenop.genconst(-100000)) #creates the addition and returns the place(register) of the result in genv_result
        builder.finish_and_return(token, genv_result)
        num = fp(-1000) # -1000+(-100000) = -101000
        assert num == -101000
        print num
        num = fp(1000) # 1000+(-100000) = -99000
        assert num == -99000
        print num
        num = fp(50) # 50+(-100000) = -99950
        assert num == -99950
        print num
        num = fp(-1024) # -1024+(-100000) = -1124
        assert num == -101024
        print num
        builder, fp, inputargs_gv, token = make_testbuilder(1)
        genv0 = inputargs_gv[0] #the first argument "location"
        genv_result = builder.genop2("int_add", genv0, rgenop.genconst(1000)) #creates the addition and returns the place(register) of the result in genv_result
        builder.finish_and_return(token, genv_result)
        num = fp(1111) # 1111+1000 = 2111
        assert num == 2111
        print num
        num = fp(-100) # -100+1000 = 900
        assert num == 900
        print num

        
        
    def test_ret(self):
        builder, fp, inputargs_gv, token = make_testbuilder(1)
        builder.finish_and_return(token, inputargs_gv[0])
        print repr("".join(builder.mc._all))
        four = fp(4) # return 4
        assert four == 4
        print four
        
    def test_sub(self):
        builder, fp, inputargs_gv, token = make_testbuilder(2)
        genv0 = inputargs_gv[0] #the first argument "location"
        genv1 = inputargs_gv[1] 
        genv_result = builder.genop2("int_sub", genv0, genv1) #creates the subtraction and returns the place(register) of the result in genv_result
        builder.finish_and_return(token, genv_result)
        four = fp(10, 6) # 10 - 6 = 4
        assert four == 4
        ten  = fp(-2, 8)
        assert ten == -10
        ten  = fp(-2,-12)
        assert ten == 10
        print four
        
    def test_sub_imm32(self):
        builder, fp, inputargs_gv, token = make_testbuilder(1)
        genv0 = inputargs_gv[0] #the first argument "location" 
        genv_result = builder.genop2("int_sub", genv0, rgenop.genconst(2)) #creates the subtraction and returns the place(register) of the result in genv_result
        builder.finish_and_return(token, genv_result)
        eight = fp(10) # 10-2 = 8
        assert eight == 8
        num = fp(-2)
        assert num == -4

        