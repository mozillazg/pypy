from pypy.jit.codegen import model
from pypy.rlib.objectmodel import specialize
from pypy.jit.codegen.x86_64.objmodel import Register8, Register64, Immediate8, Immediate32, Immediate64
from pypy.jit.codegen.x86_64.codebuf import InMemoryCodeBuilder
#TODO: understand llTypesystem
from pypy.rpython.lltypesystem import llmemory, lltype 
from pypy.jit.codegen.ia32.objmodel import LL_TO_GENVAR
from pypy.jit.codegen.model import GenLabel



# TODO: support zero arg.

# This method calls the assembler to generate code.
# It saves the operands in the helpregister gv_z
# and determine the Type of the operands,
# to choose the right method in assembler.py
def make_two_argument_method(name):
    def op_int(self, gv_x, gv_y):
        gv_z = self.allocate_register()
        self.mc.MOV(gv_z, gv_x)
        method = getattr(self.mc, name)
        
        # Many operations don't support
        # 64 Bit Immmediates directly
        if isinstance(gv_y,Immediate64):
            gv_w = self.allocate_register()
            self.mc.MOV(gv_w, gv_y)
            method(gv_z, gv_w)
        else: 
            method(gv_z, gv_y)
            
        return gv_z
    return op_int

def make_one_argument_method(name):
    def op_int(self, gv_x):
        method = getattr(self.mc, name)
        method(gv_x)
        return gv_x
    return op_int


# a small helper that provides correct type signature
# used by sigtoken
def map_arg(arg):
    if isinstance(arg, lltype.Ptr):
        arg = llmemory.Address
    if isinstance(arg, (lltype.Array, lltype.Struct)):
        arg = lltype.Void
    return LL_TO_GENVAR[arg]
    
class Label(GenLabel):
    def __init__(self, startaddr, arg_positions, stackdepth):
        self.startaddr = startaddr
        self.arg_positions = arg_positions
        self.stackdepth = stackdepth
    

class Builder(model.GenBuilder):

    MC_SIZE = 65536

    #FIXME: The MemCodeBuild. is not opend in an _open method
    def __init__(self):
        self.mc = InMemoryCodeBuilder(self.MC_SIZE)
        #callee-saved registers are commented out
        self.freeregisters ={        
                "rax":None,
                "rcx":None,
                "rdx":None,
              # "rbx":None,
                "rsi":None,
                "rdi":None,
                "r8": None,
                "r9": None,
                "r10":None,
              # "r11":None,
              # "r12":None,
              # "r13":None,
              # "r14":None,
              # "r15":None,
               }
               
    def _open(self):
        pass
                   
    @specialize.arg(1)
    def genop1(self, opname, gv_arg):
        genmethod = getattr(self, 'op_' + opname)
        print hex(self.mc.tell()),":",opname," ",gv_arg.to_string()
        return genmethod(gv_arg)

    @specialize.arg(1)
    def genop2(self, opname, gv_arg1, gv_arg2):
        genmethod = getattr(self, 'op_' + opname)
        print hex(self.mc.tell()),":",opname," ",gv_arg1.to_string()," ",gv_arg2.to_string()
        return genmethod(gv_arg1, gv_arg2)
    
    op_int_add  = make_two_argument_method("ADD")
    op_int_and  = make_two_argument_method("AND")
    op_int_dec  = make_one_argument_method("DEC") #for debuging
    op_int_inc  = make_one_argument_method("INC") #for debuging
    op_int_mul  = make_two_argument_method("IMUL")
    op_int_neg  = make_one_argument_method("NEG")
    op_int_not  = make_one_argument_method("NOT")
    op_int_or   = make_two_argument_method("OR")
    op_int_push = make_one_argument_method("PUSH") #for debuging
    op_int_pop  = make_one_argument_method("POP")  #for debuging
    op_int_sub  = make_two_argument_method("SUB")
    op_int_xor  = make_two_argument_method("XOR")

    # FIXME: is that lshift val?
    # FIXME: uses rcx insted of cl
    def op_int_lshift(self, gv_x, gv_y):
        gv_z = self.allocate_register("rcx")
        self.mc.MOV(gv_z, gv_y)
        self.mc.SHL(gv_x)
        return gv_x
    
    # FIXME: uses rcx insted of cl
    def op_int_rshift(self, gv_x, gv_y):
        gv_z = self.allocate_register("rcx")
        self.mc.MOV(gv_z, gv_y)
        self.mc.SHR(gv_x)
        return gv_x
    
    # IDIV RDX:RAX with QWREG
    # FIXME: supports only RAX with QWREG
    def op_int_div(self, gv_x, gv_y):
        gv_z = self.allocate_register("rax")
        gv_w = self.allocate_register("rdx")
        self.mc.MOV(gv_z, gv_x)
        self.mc.XOR(gv_w, gv_w)
        self.mc.IDIV(gv_y)
        return gv_z 
    
    # IDIV RDX:RAX with QWREG
    # FIXME: supports only RAX with QWREG
    def op_int_mod(self, gv_x, gv_y):
        gv_z = self.allocate_register("rax")
        gv_w = self.allocate_register("rdx")
        self.mc.MOV(gv_z, gv_x)
        self.mc.XOR(gv_w, gv_w)
        self.mc.IDIV(gv_y)
        return gv_w 
    
#    def op_int_invert(self, gv_x):
#       return self.mc.NOT(gv_x)
        
         
    #FIXME: can only jump 32bit
    # -6 : length of the jne instruction
    def jump_if_true(self, gv_condition, args_for_jump_gv):   
        targetbuilder = Builder()
        self.mc.CMP(gv_condition, Immediate32(0))
        displ = self.calc_32bit_displacement(self.mc.tell(),targetbuilder.mc.tell())
        self.mc.JNE(displ-6)
        #targetbuilder.come_from(self.mc, 'JNE')      
        return targetbuilder
    
    def op_int_gt(self, gv_x, gv_y):
        self.mc.CMP(gv_x, gv_y)
        # You can not use every register for
        # 8 bit operations, so you have to
        # choose rax,rcx or rdx 
        # TODO: rcx rdx
        gv_z = self.allocate_register("rax")
        self.mc.SETG(Register8("al"))
        return Register64("rax")
    
    def op_int_lt(self, gv_x, gv_y):
        self.mc.CMP(gv_x, gv_y)
        gv_z = self.allocate_register("rax")
        self.mc.SETL(Register8("al"))
        return Register64("rax")
    
    def op_int_le(self, gv_x, gv_y):
        self.mc.CMP(gv_x, gv_y)
        gv_z = self.allocate_register("rax")
        self.mc.SETLE(Register8("al"))
        return Register64("rax")
     
    def op_int_eq(self, gv_x, gv_y):
        self.mc.CMP(gv_x, gv_y)
        gv_z = self.allocate_register("rax")
        self.mc.SETE(Register8("al"))
        return Register64("rax")
    
    def op_int_ne(self, gv_x, gv_y):
        self.mc.CMP(gv_x, gv_y)
        gv_z = self.allocate_register("rax")
        self.mc.SETNE(Register8("al"))
        return Register64("rax")
    
    def op_int_ge(self, gv_x, gv_y):
        self.mc.CMP(gv_x, gv_y)
        gv_z = self.allocate_register("rax")
        self.mc.SETGE(Register8("al"))
        return Register64("rax")
    
    def finish_and_return(self, sigtoken, gv_returnvar):
        #self.mc.write("\xB8\x0F\x00\x00\x00")
        print hex(self.mc.tell()),": RET"
        self._open()
        if not gv_returnvar == None:#check void return
            self.mc.MOV(Register64("rax"), gv_returnvar)
        self.mc.RET()
        self._close()
        
    #FIXME: uses 32bit displ    
    # if the label is greater than 32bit
    # it must be in a register
    # -5 length of the jmp instruction
    def finish_and_goto(self, outputargs_gv, target):
        import pdb;pdb.set_trace() 
        self._open()
        #gv_x = self.allocate_register()
        #self.mc.MOV(gv_x,Immediate64(target.startaddr))
        #self.mc.JMP(gv_x)
        
        displ = self.calc_32bit_displacement(self.mc.tell(),target.startaddr)
        self.mc.JMP(displ-5)

        #self.mc.RET()
        
        self._close()
    
    def allocate_register(self, register=None):
        if register is None:
            return Register64(self.freeregisters.popitem()[0])
        else:
            if not self.freeregisters:
                raise NotImplementedError("spilling not implemented")
            del self.freeregisters[register]
            return Register64(register)
        
    def end(self):
        pass
    
    #TODO: args_gv muste be a list of unique GenVars
    def enter_next_block(self, args_gv):
        # move constants into an register
        for i in range(len(args_gv)):
            if isinstance(args_gv[i],model.GenConst):
                gv_x = self.allocate_register()
                self.mc.MOV(gv_x, argsv_gv[i])
                args_gv[i] = gv_x
        L = Label(self.mc.tell(), args_gv, 0)
        return L
    
    def _close(self):
        self.mc.done()
    
    def calc_32bit_displacement(self, curr_addr, want_jump_to):
        return want_jump_to-curr_addr


class RX86_64GenOp(model.AbstractRGenOp):
    
    @staticmethod
    @specialize.memo()
    def sigToken(FUNCTYPE):
        return ([map_arg(arg) for arg in FUNCTYPE.ARGS if arg
                is not lltype.Void], map_arg(FUNCTYPE.RESULT))

    # wrappes a integer value
    def genconst(self, llvalue):
        T = lltype.typeOf(llvalue)
        # TODO: other cases(?),imm64
        if T is lltype.Signed:
            if llvalue > int("FFFFFFFF",16):
                return Immediate64(llvalue)
            else:
                return Immediate32(llvalue)
        
    def newgraph(self, sigtoken, name):
        arg_tokens, res_token = sigtoken
        #print "arg_tokens:",arg_tokens
        inputargs_gv = []
        builder = Builder()
        # TODO: Builder._open()
        entrypoint = builder.mc.tell()
        # TODO: support more than two reg
        register_list = ["rdi","rsi"]
        # fill the list with the correct registers
        inputargs_gv = [builder.allocate_register(register_list[i])
                                for i in range(len(arg_tokens))]
        return builder,Immediate64(entrypoint), inputargs_gv
    
