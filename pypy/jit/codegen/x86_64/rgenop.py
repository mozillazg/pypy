from pypy.jit.codegen import model
from pypy.rlib.objectmodel import specialize
from pypy.jit.codegen.x86_64.objmodel import IntVar, Register64, Register8, Immediate8, Immediate32, Immediate64, Stack64
from pypy.jit.codegen.x86_64.codebuf import InMemoryCodeBuilder
from pypy.rpython.lltypesystem import llmemory, lltype 
from pypy.jit.codegen.ia32.objmodel import LL_TO_GENVAR
from pypy.jit.codegen.model import GenLabel
from pypy.jit.codegen.emit_moves import emit_moves, emit_moves_safe



# TODO: support zero arg.

# This method calls the assembler to generate code.
# It saves the operands in the helpregister gv_z
# and determine the type of the operands,
# to choose the right method in assembler.py
def make_two_argument_method(name):
    def op_int(self, gv_x, gv_y):
        [gv_x, gv_y] = self.move_to_registers([gv_x, gv_y]) 
        dont_alloc = []
        if not isinstance(gv_x, model.GenConst):
            dont_alloc.append(gv_x.location.reg)
        if not isinstance(gv_y, model.GenConst):
            dont_alloc.append(gv_y.location.reg)
        gv_z = self.allocate_register(None, dont_alloc)
        self.mc.MOV(gv_z, gv_x)
        method = getattr(self.mc, name)
        
        # Many operations don't support
        # 64 Bit Immmediates directly
        if isinstance(gv_y,Immediate64):
            dont_alloc.append(gv_z.location.reg)
            gv_w = self.allocate_register(None, dont_alloc)
            self.mc.MOV(gv_w, gv_y)
            method(gv_z, gv_w)
        else: 
            method(gv_z, gv_y)
        return gv_z
    return op_int

def make_one_argument_method(name):
    def op_int(self, gv_x):
        [gv_x] = self.move_to_registers([gv_x]) 
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
    
class WrongArgException(Exception):
    pass
    
class Label(GenLabel):
    def __init__(self, startaddr, arg_positions, stackdepth):
        self.startaddr = startaddr
        self.arg_positions = arg_positions
        self.stackdepth = stackdepth

# used by emit_moves
class MoveEmitter(object):
    def __init__(self, builder):
        self.builder = builder
        self.moves = []
       
    def create_fresh_location(self):
        return self.builder.allocate_register().location.reg
    
    def emit_move(self, source, target):
        self.moves.append((source, target))

class Builder(model.GenBuilder):

    MC_SIZE = 65536

    def __init__(self, stackdepth, used_registers=[], used_stack_pos = None):
        self.stackdepth = stackdepth 
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
        self._orig_location={}# used to restore the location of a gv
        self.known_gv = [] # contains the live genvars (used for spilling and allocation)
        for reg in used_registers:
            del self.freeregisters[reg.location.reg]
            self._orig_location[reg] = reg.location
            self.known_gv.append(reg)
        if used_stack_pos == None:
            self.used_stack_pos = {}
        else:
            self.used_stack_pos = used_stack_pos
               
    def _open(self):
        pass
                   
    @specialize.arg(1)
    def genop1(self, opname, gv_arg): 
        genmethod = getattr(self, 'op_' + opname)
        return genmethod(gv_arg)
        
    @specialize.arg(1)
    def genop2(self, opname, gv_arg1, gv_arg2): 
        genmethod = getattr(self, 'op_' + opname)
        return genmethod(gv_arg1, gv_arg2)
    
    def genraisingop1(self, opname, gv_arg1):
        assert opname[len(opname)-4:len(opname)] == "_ovf"
        
        genmethod = getattr(self, 'op_' + opname[0:len(opname)-4])
        gv_result = genmethod(gv_arg1)
        gv_bool = self.allocate_register("rax", gv_result)
        self.mc.SETO(IntVar(Register8("al")))
        return gv_result, gv_bool
    
    # This Method creates an overflow method which
    # return the operations result and a flag(BoolVar)
    # flag= True if there was an overflow
    # it works like genop2
    def genraisingop2(self, opname, gv_arg1, gv_arg2):
        assert opname[len(opname)-4:len(opname)] == "_ovf"
        
        genmethod = getattr(self, 'op_' + opname[0:len(opname)-4])
        gv_result = genmethod(gv_arg1, gv_arg2)
        gv_bool = self.allocate_register("rax", gv_result)
        self.mc.SETO(IntVar(Register8("al")))
        return gv_result, gv_bool
 
    op_int_add     = make_two_argument_method("ADD")  # TODO: use inc
    op_int_and     = make_two_argument_method("AND")
    op_int_dec     = make_one_argument_method("DEC")  # for debuging
    op_int_inc     = make_one_argument_method("INC")  # for debuging
    op_int_mul     = make_two_argument_method("IMUL")
    op_int_neg     = make_one_argument_method("NEG")
    op_int_not     = make_one_argument_method("NOT")  # for debuging
    op_int_or      = make_two_argument_method("OR")
    op_int_push    = make_one_argument_method("PUSH") # for debuging
    op_int_pop     = make_one_argument_method("POP")  # for debuging
    op_int_sub     = make_two_argument_method("SUB")  # TODO: use DEC
    op_int_xor     = make_two_argument_method("XOR")

    # must return a genvar
    def genop_same_as(self, imm):
        gv_x = self.allocate_register()
        self.mc.MOV(gv_x, imm)
        return gv_x
        
    # returns 1 if gv_x is true
    def op_int_is_true(self, gv_x):
        [gv_x, gv_y] = self.move_to_registers([gv_x, Immediate32(1)], None, move_imm_too=True)  
        self.mc.CMP(gv_x, gv_y)
        [gv_x, gv_y] = self.throw_away_if_const([gv_x,gv_y])
        gv_z = self.allocate_register("rax")
        self.mc.SETE(IntVar(Register8("al")))
        return gv_z

    # TODO: support reg8
    def op_cast_bool_to_int(self, gv_x):
        [gv_x] = self.move_to_registers([gv_x]) 
        assert isinstance(gv_x, IntVar) and isinstance(gv_x.location,Register64)
        return gv_x
    
    # 0 xor 1 == 1
    # 1 xor 1 == 0
    def op_bool_not(self, gv_x):
        [gv_x] = self.move_to_registers([gv_x]) 
        self.mc.XOR(gv_x, Immediate32(1))
        return gv_x

    # FIXME: is that lshift val?
    # FIXME: uses rcx insted of cl
    def op_int_lshift(self, gv_x, gv_y):
        gv_z = self.allocate_register("rcx")
        [gv_x, gv_y] = self.move_to_registers([gv_x, gv_y], ["rcx"]) 
        self.mc.MOV(gv_z, gv_y)
        self.mc.SHL(gv_x)
        return gv_x
    
    # FIXME: uses rcx insted of cl
    def op_int_rshift(self, gv_x, gv_y):
        gv_z = self.allocate_register("rcx")
        [gv_x, gv_y] = self.move_to_registers([gv_x, gv_y], ["rcx"]) 
        self.mc.MOV(gv_z, gv_y)
        self.mc.SHR(gv_x)
        return gv_x
    
    # called before an assembler operation
    # ensures that every genVar is
    # inside of a register
    def move_to_registers(self, registers, dont_alloc = None, move_imm_too = False):
        if dont_alloc is None:
            dont_alloc = []
            
        for i in range(len(registers)):
            if isinstance(registers[i], model.GenVar) and isinstance(registers[i].location, Stack64):
                registers[i] = self.move_back_to_register(registers[i], dont_alloc)
                dont_alloc.append(registers[i].location.reg)
            # some operations dont suppoert immediateoperands
            # but only registers
            if move_imm_too and isinstance(registers[i], Immediate32): 
                gv_new = self.allocate_register(None, dont_alloc)
                self.mc.MOV(gv_new, registers[i])
                registers[i] = gv_new
                dont_alloc.append(registers[i].location.reg)
                registers[i].location.contains_Const()
        return registers         
    
    # IDIV RDX:RAX with QWREG
    # supports only RAX (64bit) with QWREG  
    def op_int_floordiv(self, gv_x, gv_y):
        gv_z = self.allocate_register("rax")
        gv_w = self.allocate_register("rdx")
        [gv_x, gv_y] = self.move_to_registers([gv_x, gv_y], ["rax", "rdx"], move_imm_too=True) 
        self.mc.MOV(gv_z, gv_x)
        self.mc.CDQ() #sign extention of rdx:rax
        self.mc.IDIV(gv_y)
        return gv_z 
    
    # IDIV RDX:RAX with QWREG
    # supports only RAX with QWREG
    def op_int_mod(self, gv_x, gv_y):
        gv_z = self.allocate_register("rax")
        gv_w = self.allocate_register("rdx")
        [gv_x, gv_y] = self.move_to_registers([gv_x, gv_y], ["rax", "rdx"], move_imm_too=True) 
        self.mc.MOV(gv_z, gv_x)
        self.mc.XOR(gv_w, gv_w)
        self.mc.IDIV(gv_y)
        return gv_w 
    
    op_int_invert = op_int_not
    
    # if a register contains a constant
    # it will be marked to be don't spilled
    def throw_away_if_const(self, registers):
        for i in range(len(registers)):
            if registers[i].location.contains_genConst:
                registers[i].location.dont_spill(True)
        return registers
            
    # You can not use every register for
    # 8 bit operations, so you have to
    # choose rax,rcx or rdx 
    # TODO: use also rcx rdx
    def op_int_gt(self, gv_x, gv_y):
        [gv_x, gv_y] = self.move_to_registers([gv_x, gv_y], None, move_imm_too=True)  
        self.mc.CMP(gv_x, gv_y)
        [gv_x, gv_y] = self.throw_away_if_const([gv_x,gv_y])
        gv_z = self.allocate_register("rax")
        self.mc.SETG(IntVar(Register8("al")))
        return gv_z
    
    def op_int_lt(self, gv_x, gv_y):
        [gv_x, gv_y] = self.move_to_registers([gv_x, gv_y], None, move_imm_too=True)  
        self.mc.CMP(gv_x, gv_y)
        [gv_x, gv_y] = self.throw_away_if_const([gv_x,gv_y])
        gv_z = self.allocate_register("rax")
        self.mc.SETL(IntVar(Register8("al")))
        return gv_z
    
    def op_int_le(self, gv_x, gv_y):
        [gv_x, gv_y] = self.move_to_registers([gv_x, gv_y], None, move_imm_too=True)  
        self.mc.CMP(gv_x, gv_y)
        [gv_x, gv_y] = self.throw_away_if_const([gv_x,gv_y])
        gv_z = self.allocate_register("rax")
        self.mc.SETLE(IntVar(Register8("al")))
        return gv_z
     
    def op_int_eq(self, gv_x, gv_y):
        [gv_x, gv_y] = self.move_to_registers([gv_x, gv_y], None, move_imm_too=True)  
        self.mc.CMP(gv_x, gv_y)
        [gv_x, gv_y] = self.throw_away_if_const([gv_x,gv_y])
        gv_z = self.allocate_register("rax")
        self.mc.SETE(IntVar(Register8("al")))
        return gv_z
    
    def op_int_ne(self, gv_x, gv_y):
        [gv_x, gv_y] = self.move_to_registers([gv_x, gv_y], None, move_imm_too=True)  
        self.mc.CMP(gv_x, gv_y)
        [gv_x, gv_y] = self.throw_away_if_const([gv_x,gv_y])
        gv_z = self.allocate_register("rax")
        self.mc.SETNE(IntVar(Register8("al")))
        return gv_z
    
    def op_int_ge(self, gv_x, gv_y):
        [gv_x, gv_y] = self.move_to_registers([gv_x, gv_y], None, move_imm_too=True)  
        self.mc.CMP(gv_x, gv_y)
        [gv_x, gv_y] = self.throw_away_if_const([gv_x,gv_y])
        gv_z = self.allocate_register("rax")
        self.mc.SETGE(IntVar(Register8("al")))
        return gv_z
    
    # move back the gv to orig. positions
    # (this pos. could be changed here which 
    # could result in wrong locations of the gv)
    def start_writing(self):
        for i in range(len(self.known_gv)):
            if self.known_gv[i] in self._orig_location:
                self.known_gv[i].location = self._orig_location[self.known_gv[i]]
        
    # the moves to pass arg. when making a jump to a block
    # the targetvars are only copys
    def _compute_moves(self, outputargs_gv, targetargs_gv):
        tar2src = {}
        tar2loc = {}
        src2loc = {} 
        for i in range(len(outputargs_gv)):
            tar2src[targetargs_gv[i].location] = outputargs_gv[i].location
            tar2loc[targetargs_gv[i].location] = targetargs_gv[i].location
            src2loc[outputargs_gv[i].location] = outputargs_gv[i].location
        movegen = MoveEmitter(self)
        emit_moves(movegen, [target_gv.location for target_gv in targetargs_gv],
                    tar2src, tar2loc, src2loc)
        return movegen.moves
    
    
    #FIXME: can only jump 32bit
    #FIXME: imm8 insted of imm32?
    def _new_jump(name, value):
        from pypy.tool.sourcetools import func_with_new_name
        def jump(self, gv_condition, args_for_jump_gv): 
            # the targetbuilder must know the registers(live vars) 
            # of the calling block and the used stack_pos
            # to ensure a correct register allocation 
            targetbuilder = Builder(self.stackdepth, args_for_jump_gv, self.used_stack_pos)
            self.mc.CMP(gv_condition, Immediate32(value))
            self.mc.JNE(targetbuilder.mc.tell())
            return targetbuilder
        return func_with_new_name(jump, name)
    
    jump_if_false = _new_jump("jump_if_false", 1)
    jump_if_true  = _new_jump('jump_if_true', 0)
    
    # moves stackpointer if there are
    # gv on the stack (which are not 
    # need anymore)
    def finish_and_return(self, sigtoken, gv_returnvar):
        #self.mc.write("\xB8\x0F\x00\x00\x00")
        self._open()
        gv_return = self.allocate_register("rax")
        # if there unused genVars on the stack
        # throw them away
        if not self.stackdepth == 0:
            self.mc.ADD(IntVar(Register64("rsp")), Immediate32(self.stackdepth*8))
            self.stackdepth == 0
        if not gv_returnvar == None:#check void return      
            self.mc.MOV(gv_return, gv_returnvar)
        self.mc.RET()
        self._close()
        
    # FIXME: uses 32bit displ 
    # TODO: return also stackdepth or pop! 
    # if the label is greater than 32bit
    # it must be in a register (not supported)
    def finish_and_goto(self, outputargs_gv, target):
        self._open()
        #gv_x = self.allocate_register()
        #self.mc.MOV(gv_x,Immediate64(target.startaddr))
        #self.mc.JMP(gv_x) 
        moves = self._compute_moves(outputargs_gv, target.arg_positions)
        for source_gv, target_gv in moves:
            # TODO: check for MOV(STACK,STACK)
            self.mc.MOV(IntVar(source_gv), IntVar(target_gv)) 
        self.mc.JMP(target.startaddr)
        self._close()
        
    # FIXME: returns only IntVars    
    # TODO: support the allocation of 8bit Reg
    # Don't remember genVars which contain constants(Optimization)
    # An allocation could have spilling as sideeffect(stack mov)
    def allocate_register(self, register=None, dontalloc = None):
        if dontalloc is None:
            dontalloc = []
            
        if register is None:
            # dont use registers from dontalloc
            # e.g you dont want to use rax because it is
            # needed/used already somewhere else
            leave = False  
            reg = None
            seen_reg = 0
            while not leave:
                # none or only "dontalloc" regs. are left
                if not self.freeregisters or seen_reg == len(self.freeregisters):
                    new_gv = self.spill_register(dontalloc)
                    self.known_gv.append(new_gv)
                    return new_gv
                # After one ore more loops: 
                # This reg is in dontalloc
                if not reg == None:
                    self.freeregisters.append(reg)
                reg = self.freeregisters.popitem()[0]
                # leave if the reg is not in dontalloc           
                if reg not in dontalloc:
                    leave = True
                seen_reg = seen_reg +1
                
            new_gv = IntVar(Register64(reg))
            self.known_gv.append(new_gv)
            return new_gv
        
        else:
            if register not in self.freeregisters:
                # the register must be in the list.
                # beacuse if its not free it is
                # used by a gen_var
                for i in range(len(self.known_gv)):
                    if isinstance(self.known_gv[i].location, Register64) and register == self.known_gv[i].location.reg:
                        # move the values from the requiered 
                        # register to an other one and 
                        # return the requested one.
                        gv_temp = self.allocate_register(None, dontalloc)
                        self.mc.MOV(gv_temp, self.known_gv[i])
                        new_gv = IntVar(Register64(register))
                        self.known_gv.append(new_gv)
                        self.known_gv[i].location.reg = gv_temp.location.reg
                        self.known_gv.remove(gv_temp)
                        return new_gv
                    
                # raised when the register is not in freereg. and not
                # used by a gen_var 
                raise Exception("error while register moves")
                           
            del self.freeregisters[register]
            new_gv = IntVar(Register64(register))
            self.known_gv.append(new_gv)
            return new_gv
        
    def end(self):
        pass
    
    # TODO: args_gv muste be a list of unique GenVars, dont searchs for double gv
    # Spilling could change the location of a
    # genVar after this Label. That will result in a
    # wrong mapping in _compute_moves when leaving this block.
    # So the parameters must be inmutable(copy them)
    def enter_next_block(self, args_gv):
        # move constants into an register
        copy_args = []
        for i in range(len(args_gv)):
            if isinstance(args_gv[i],model.GenConst):
                gv_x = self.allocate_register()
                self.mc.MOV(gv_x, args_gv[i])
                args_gv[i] = gv_x
            # copy the genvars:
            # without copying the references could be changed
            # which can result in wrong locations of the gv 
            copy_args.append(IntVar(Register64(args_gv[i].location.reg)))
        L = Label(self.mc.tell(), copy_args, 0)
        return L
    
    def _close(self):
        self.mc.done() # used for dump code (debugging)
        
    # TODO: alloc strategy
    # TODO: support 8bit reg. alloc
    # just greedy spilling.
    # moves GenVar locations on the stack
    # to free an register
    def spill_register(self, dont_spill=None):
        if dont_spill is None:
            dont_spill = []
        # take the first gv which is not
        # on the stack
        gv_to_spill = None
        for i in range(len(self.known_gv)):
            if isinstance(self.known_gv[i].location, Register64):
                if self.known_gv[i].location.reg not in dont_spill:
                    gv_to_spill = self.known_gv[i]
                    break
        # there must be genVars which are 
        # inside an register so:
        if gv_to_spill == None:
            raise WrongArgException("to many dont_spill/dont_alloc registers")
        assert isinstance(gv_to_spill.location, Register64)
        # if the register contains a genCons
        # it has not to be saved on the stack
        if gv_to_spill.location.throw_away:
            return gv_to_spill
        else:
            # search for free stack position/location
            for location in range(self.stackdepth):
                if location not in self.used_stack_pos.keys():
                    # a location has been found which is not the tos.
                    self.mc.MOV(IntVar(Stack64(self.stackdepth-location)), gv_to_spill)
                    self.used_stack_pos[location] = None
                    new_gv = IntVar(Register64(gv_to_spill.location.reg))  
                    gv_to_spill.location = Stack64(location)     
                    return new_gv
            # no free stack pos found
            # use the top of stack ->push   
            self.used_stack_pos[self.stackdepth] = None # remember as used   
            self.stackdepth = self.stackdepth +1 
            self.mc.PUSH(gv_to_spill) 
            new_gv = IntVar(Register64(gv_to_spill.location.reg))
            gv_to_spill.location = Stack64(self.stackdepth)         
            return new_gv
        
    # A GenVar which location is on the stack
    # will be moved back to make operations posible
    # and faster
    def move_back_to_register(self, a_spilled_gv, dont_alloc):
        # if a_spilled_gv is the top of stack
        gv_new = self.allocate_register(None, dont_alloc)
        if a_spilled_gv.location.offset ==  self.stackdepth:
            self.mc.POP(gv_new)
            self.stackdepth = self.stackdepth -1
            del self.used_stack_pos[self.stackdepth]
            assert self.stackdepth >= 0 
            a_spilled_gv.location = Register64(gv_new.location.reg)
            self.known_gv.remove(gv_new)
            # TODO: look if there is a genVar with stackdepth
            #       if not it has already been moved to a reg. 
            #       pop it or change the stackpointer
            return a_spilled_gv
        else:
        # else access the memory
            self.mc.MOV(gv_new, IntVar(Stack64(self.stackdepth-a_spilled_gv.location.offset)))
            del self.used_stack_pos[a_spilled_gv.location.offset]
            a_spilled_gv.location = Register64(gv_new.location.reg)
            self.known_gv.remove(gv_new) 
            return a_spilled_gv
            
            

class RX86_64GenOp(model.AbstractRGenOp):
    
    @staticmethod
    @specialize.memo()
    def sigToken(FUNCTYPE):
        return ([map_arg(arg) for arg in FUNCTYPE.ARGS if arg
                is not lltype.Void], map_arg(FUNCTYPE.RESULT))

    # wrappes a integer value
    # many 64-bit operations only 
    # support 32-bit immediates
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
        inputargs_gv = []
        builder = Builder(0) # stackdepth = 0, no used regs/mem_pos
        # TODO: Builder._open()
        entrypoint = builder.mc.tell()
        # from http://www.x86-64.org/documentation/abi.pdf
        # TODO: also return Stackpositions and let the
        #       builder know 
        register_list = ["rdi","rsi","rdx","rcx","r8","r9"]
        # fill the list with the correct registers
        inputargs_gv = [builder.allocate_register(register_list[i])
                                for i in range(len(arg_tokens))]
        return builder,Immediate64(entrypoint), inputargs_gv
    
