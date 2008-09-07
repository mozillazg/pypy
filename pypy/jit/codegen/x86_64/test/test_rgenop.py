import py
from pypy.rpython.lltypesystem import lltype
from pypy.jit.codegen.x86_64.rgenop import RX86_64GenOp
from pypy.jit.codegen.test.rgenop_tests import AbstractRGenOpTestsDirect
#from pypy.jit.codegen.test.rgenop_tests import AbstractRGenOpTestsCompile

# for the individual tests see
# ====> ../../test/rgenop_tests.py

def skip(self):
    py.test.skip("not implemented yet")
    
def make_mul(rgenop):
    sigtoken = rgenop.sigToken(lltype.FuncType([lltype.Signed, lltype.Signed], lltype.Signed))
    builder, gv_mul, [gv_x, gv_y] = rgenop.newgraph(sigtoken, "mul")
    builder.start_writing()
    gv_result = builder.genop2("int_mul", gv_x, gv_y)
    builder.finish_and_return(sigtoken, gv_result)
    builder.end()
    return gv_mul
    
def make_mul_im32(rgenop):
    sigtoken = rgenop.sigToken(lltype.FuncType([lltype.Signed, lltype.Signed], lltype.Signed))
    builder, gv_mul, [gv_x, gv_y] = rgenop.newgraph(sigtoken, "mul")
    builder.start_writing()
    gv_result = builder.genop2("int_mul", gv_x, rgenop.genconst(200))
    builder.finish_and_return(sigtoken, gv_result)
    builder.end()
    return gv_mul

def make_inc(rgenop):
    sigtoken = rgenop.sigToken(lltype.FuncType([lltype.Signed], lltype.Signed))
    builder, gv_inc, gv_x = rgenop.newgraph(sigtoken, "inc")
    builder.start_writing()
    gv_result = builder.genop1("int_inc", gv_x[0])
    builder.finish_and_return(sigtoken, gv_result)
    builder.end()
    return gv_inc

def make_dec(rgenop):
    sigtoken = rgenop.sigToken(lltype.FuncType([lltype.Signed], lltype.Signed))
    builder, gv_dec, gv_x = rgenop.newgraph(sigtoken, "dec")
    builder.start_writing()
    gv_result = builder.genop1("int_dec", gv_x[0])
    builder.finish_and_return(sigtoken, gv_result)
    builder.end()
    return gv_dec

def make_push(rgenop):
    sigtoken = rgenop.sigToken(lltype.FuncType([lltype.Signed], lltype.Signed))
    builder, gv_push, gv_x = rgenop.newgraph(sigtoken, "push")
    builder.start_writing()
    gv_result = builder.genop1("int_push", gv_x[0])
    builder.finish_and_return(sigtoken, gv_result)
    builder.end()
    return gv_push

def make_pop(rgenop):
    sigtoken = rgenop.sigToken(lltype.FuncType([lltype.Signed], lltype.Signed))
    builder, gv_pop, gv_x = rgenop.newgraph(sigtoken, "pop")
    builder.start_writing()
    gv_result = builder.genop1("int_pop", gv_x[0])
    builder.finish_and_return(sigtoken, gv_result)
    builder.end()
    return gv_pop

class TestRGenopDirect(AbstractRGenOpTestsDirect):
    RGenOp = RX86_64GenOp
    
    def test_inc(self):
        rgenop = self.RGenOp()
        inc_function = make_inc(rgenop)
        fnptr = self.cast(inc_function,1)
        res = fnptr(0)
        assert res == 1
        
    def test_dec(self):
        rgenop = self.RGenOp()
        dec_function = make_dec(rgenop)
        fnptr = self.cast(dec_function,1)
        res = fnptr(2)
        assert res == 1
        
    def test_mul_im32(self):
        rgenop = self.RGenOp()
        mul_function = make_mul_im32(rgenop)
        fnptr = self.cast(mul_function,1)
        res = fnptr(210)
        assert res == 42000
        
    def test_mul(self):
        rgenop = self.RGenOp()
        mul_function = make_mul(rgenop)
        fnptr = self.cast(mul_function,2)
        res = fnptr(1200,300)
        assert res == 360000
        
   # def test_push_and_pop(self):
   #     rgenop = self.RGenOp()
   #     push_result = make_push(rgenop)
   #     fnptr = self.cast(push_result,1)
   #     pop_result = make_pop(rgenop)
   #     fnptr = self.cast(pop_result,1)
   #     res = fnptr(42)
        #assert res == 1
        
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