import py
from pypy.rpython.lltypesystem import lltype
from pypy.jit.codegen.x86_64.rgenop import RX86_64GenOp
from pypy.jit.codegen.test.rgenop_tests import AbstractRGenOpTestsDirect
#from pypy.jit.codegen.test.rgenop_tests import AbstractRGenOpTestsCompile

# for the individual tests see
# ====> ../../test/rgenop_tests.py

def skip(self):
    py.test.skip("not implemented yet")

def make_one_op_instr(rgenop, instr_name):
    sigtoken = rgenop.sigToken(lltype.FuncType([lltype.Signed], lltype.Signed))
    builder, gv_one_op_instr, [gv_x] = rgenop.newgraph(sigtoken, "one_op_instr")
    builder.start_writing()
    
    gv_result = builder.genop1(instr_name, gv_x)
    builder.finish_and_return(sigtoken, gv_result)
    builder.end()
    return gv_one_op_instr

def make_bool_op(rgenop, which_bool_op):
    sigtoken = rgenop.sigToken(lltype.FuncType([lltype.Signed, lltype.Signed], lltype.Signed))
    builder, gv_bool_op, [gv_x, gv_y] = rgenop.newgraph(sigtoken, "bool_op")
    builder.start_writing()
    
    gv_result = builder.genop2(which_bool_op, gv_x, gv_y)
    builder.finish_and_return(sigtoken, gv_result)
    builder.end()
    return gv_bool_op

def make_cmp(rgenop, which_cmp):
    sigtoken = rgenop.sigToken(lltype.FuncType([lltype.Signed, lltype.Signed], lltype.Signed))
    builder, gv_cmp, [gv_x, gv_y] = rgenop.newgraph(sigtoken, "cmp")
    builder.start_writing()
    
    gv_result = builder.genop2(which_cmp, gv_x, gv_y)
    builder.finish_and_return(sigtoken, gv_result)
    builder.end()
    return gv_cmp

def make_mul(rgenop):
    sigtoken = rgenop.sigToken(lltype.FuncType([lltype.Signed, lltype.Signed], lltype.Signed))
    builder, gv_mul, [gv_x, gv_y] = rgenop.newgraph(sigtoken, "mul")
    builder.start_writing()
    gv_result = builder.genop2("int_mul", gv_x, gv_y)
    builder.finish_and_return(sigtoken, gv_result)
    builder.end()
    return gv_mul
    
def make_mul_imm(rgenop, num):
    sigtoken = rgenop.sigToken(lltype.FuncType([lltype.Signed, lltype.Signed], lltype.Signed))
    builder, gv_mul, [gv_x, gv_y] = rgenop.newgraph(sigtoken, "mul")
    builder.start_writing()
    gv_result = builder.genop2("int_mul", gv_x, rgenop.genconst(num))
    builder.finish_and_return(sigtoken, gv_result)
    builder.end()
    return gv_mul        

class TestRGenopDirect(AbstractRGenOpTestsDirect):
    RGenOp = RX86_64GenOp
                        
    def test_inc(self):
        inc_function = make_one_op_instr(self.RGenOp(),"int_inc")
        fnptr = self.cast(inc_function,1)
        res = fnptr(0)
        assert res == 1
        
    def test_dec(self):
        dec_function = make_one_op_instr(self.RGenOp(),"int_dec")
        fnptr = self.cast(dec_function,1)
        res = fnptr(2)
        assert res == 1
        
    def test_mul_im32(self):
        rgenop = self.RGenOp()
        mul_function = make_mul_imm(rgenop,200)
        fnptr = self.cast(mul_function,1)
        res = fnptr(210)
        assert res == 42000
        
    # segmentation fault at mov(qwreg,imm64)
    
    #def test_mul_im64(self):
    #    rgenop = self.RGenOp()
    #    mul_function = make_mul_imm(rgenop,int("123456789",16))
    #    fnptr = self.cast(mul_function,1)
    #    res = fnptr(2)
    #    assert res == int("123456789",16)*2
        
    def test_mul(self):
        rgenop = self.RGenOp()
        mul_function = make_mul(rgenop)
        fnptr = self.cast(mul_function,2)
        res = fnptr(1200,300)
        assert res == 360000
        
    def test_greater(self):
        rgenop = self.RGenOp()
        cmp_function = make_cmp(rgenop, "int_gt")
        fnptr = self.cast(cmp_function,2)
        res = fnptr(3,4) # 3>4?
        assert res == 0  # false
        res = fnptr(4,3)
        assert res == 1 
        res = fnptr(4,4)
        assert res == 0
        res = fnptr(4,0)
        assert res == 1        
        res = fnptr(-4,0)
        assert res == 0
        
    def test_less(self):
        rgenop = self.RGenOp()
        cmp_function = make_cmp(rgenop, "int_lt")
        fnptr = self.cast(cmp_function,2)
        res = fnptr(3,4) # 3<4?
        assert res == 1  # true
        res = fnptr(4,3)
        assert res == 0 
        res = fnptr(4,4)
        assert res == 0
        res = fnptr(4,0)
        assert res == 0
        res = fnptr(-4,0)
        assert res == 1
        
    def test_less_or_equal(self):
        rgenop = self.RGenOp()
        cmp_function = make_cmp(rgenop, "int_le")
        fnptr = self.cast(cmp_function,2)
        res = fnptr(3,4) # 3<=4?
        assert res == 1  # true
        res = fnptr(4,3)
        assert res == 0 
        res = fnptr(4,4)
        assert res == 1
        res = fnptr(4,0)
        assert res == 0
        res = fnptr(-4,0)
        assert res == 1
        
    def test_greater_or_equal(self):
        rgenop = self.RGenOp()
        cmp_function = make_cmp(rgenop, "int_ge")
        fnptr = self.cast(cmp_function,2)
        res = fnptr(3,4) # 3>=4?
        assert res == 0  # false
        res = fnptr(4,3)
        assert res == 1 
        res = fnptr(4,4)
        assert res == 1
        res = fnptr(4,0)
        assert res == 1
        res = fnptr(-4,0)
        assert res == 0
        
    def test__equal(self):
        rgenop = self.RGenOp()
        cmp_function = make_cmp(rgenop, "int_eq")
        fnptr = self.cast(cmp_function,2)
        res = fnptr(3,4) # 3==4?
        assert res == 0  # false
        res = fnptr(4,3)
        assert res == 0 
        res = fnptr(4,4)
        assert res == 1
        res = fnptr(4,0)
        assert res == 0
        res = fnptr(-4,0)
        assert res == 0
        
    def test_not_equal(self):
        rgenop = self.RGenOp()
        cmp_function = make_cmp(rgenop, "int_ne")
        fnptr = self.cast(cmp_function,2)
        res = fnptr(3,4) # 3!=4?
        assert res == 1  # true
        res = fnptr(4,3)
        assert res == 1 
        res = fnptr(4,4)
        assert res == 0
        res = fnptr(4,0)
        assert res == 1
        res = fnptr(-4,0)
        assert res == 1
        
    def test_int_and(self):
        rgenop = self.RGenOp()
        bool_function = make_bool_op(rgenop,"int_and")
        fnptr = self.cast(bool_function,2)
        result = fnptr(1,1)
        assert result == 1
        result = fnptr(1,0)
        assert result == 0
        result = fnptr(0,1)
        assert result == 0
        result = fnptr(0,0)
        assert result == 0
        # AND 010101
        #     101010
        #   = 000000
        result = fnptr(42,21) 
        assert result == 0
        
    def test_int_or(self):
        rgenop = self.RGenOp()
        bool_function = make_bool_op(rgenop,"int_or")
        fnptr = self.cast(bool_function,2)
        result = fnptr(1,1)
        assert result == 1
        result = fnptr(1,0)
        assert result == 1
        result = fnptr(0,1)
        assert result == 1
        result = fnptr(0,0)
        assert result == 0
        # or  010101
        #     101010
        #   = 111111
        result = fnptr(42,21) 
        assert result == 63
        
    def test_int_xor(self):
        rgenop = self.RGenOp()
        bool_function = make_bool_op(rgenop,"int_xor")
        fnptr = self.cast(bool_function,2)
        result = fnptr(1,1)
        assert result == 0
        result = fnptr(1,0)
        assert result == 1
        result = fnptr(0,1)
        assert result == 1
        result = fnptr(0,0)
        assert result == 0
        # xor 010101
        #     101010
        #   = 111111
        result = fnptr(42,21) 
        assert result == 63
        
    def test_neg(self):
        neg_function = make_one_op_instr(self.RGenOp(),"int_neg")
        fnptr = self.cast(neg_function,1)
        result = fnptr(1)
        assert result == -1
        result = fnptr(-1)
        assert result == 1  
        result = fnptr(255)
        assert result == -255
        result = fnptr(0)
        assert result == 0
        result = fnptr(-123456789)
        assert result == 123456789
        
    def test_not(self):
        not_function = make_one_op_instr(self.RGenOp(),"int_not")
        fnptr = self.cast(not_function,1)
        result = fnptr(1)
        assert result == -2
        result = fnptr(0)
        assert result == -1
        result = fnptr(-43)
        assert result == 42
       
    #TODO: Test push/pop
       
    test_directtesthelper_direct = skip
    test_dummy_compile = skip
    test_cast_raising = skip
    test_float_adder = skip
    test_float_call = skip
    test_float_loop_direct = skip
    test_dummy_direct = skip
    test_largedummy_direct = skip
    test_branching_direct = skip
    ##test_goto_direct = skip##
    test_if_direct = skip
    test_switch_direct = skip
    test_large_switch_direct = skip
    test_fact_direct = skip
    test_calling_pause_direct = skip
    test_longwinded_and_direct = skip
    test_condition_result_cross_link_direct = skip
    test_multiple_cmps = skip
    test_flipped_cmp_with_immediate = skip
    test_tight_loop = skip
    test_jump_to_block_with_many_vars = skip
    test_same_as = skip
    test_pause_and_resume_direct = skip
    test_like_residual_red_call_with_exc_direct = skip
    test_call_functions_with_different_signatures_direct = skip
    test_defaultonly_switch = skip
    test_bool_not_direct = skip
    test_read_frame_var_direct = skip
    test_read_frame_var_float_direct = skip
    test_genconst_from_frame_var_direct = skip
    test_write_frame_place_direct = skip
    test_write_frame_place_float_direct = skip
    test_write_lots_of_frame_places_direct = skip
    test_read_frame_place_direct = skip
    test_read_float_frame_place_direct = skip
    test_frame_vars_like_the_frontend_direct = skip
    test_unaliasing_variables_direct = skip
    test_from_random_direct = skip
    test_from_random_2_direct = skip
    test_from_random_3_direct = skip
    test_from_random_4_direct = skip
    test_from_random_5_direct = skip
    test_genzeroconst = skip
    test_ovfcheck_adder_direct = skip
    test_ovfcheck1_direct = skip
    test_ovfcheck2_direct = skip
    test_cast_direct = skip
    test_array_of_ints = skip
    test_interior_access = skip
    test_fieldaccess = skip
    test_interior_access = skip
    test_interior_access_float = skip
    test_void_return = skip
    test_demo_f1_direct = skip
    test_red_switch = skip