from pypy.jit.codegen.x86_64.objmodel import Register8, Register64, Immediate8, Immediate32, Immediate64


#Mapping from 64Bit-Register to coding (Rex.W or Rex.B , ModRM)
REGISTER_MAP = {
                "rax": (0, 0),
                "rcx": (0, 1),
                "rdx": (0, 2),
                "rbx": (0, 3),
                "rsp": (0, 4),
                "rbp": (0, 5),
                "rsi": (0, 6),
                "rdi": (0, 7),
                "r8":  (1, 0),
                "r9":  (1, 1),
                "r10": (1, 2),
                "r11": (1, 3),
                "r12": (1, 4),
                "r13": (1, 5),
                "r14": (1, 6),
                "r15": (1, 7),
                }
                
# Mapping from 8Bit-Register to coding
REGISTER_MAP_8BIT = {
                    "al":0,
                    "cl":1,
                    "dl":2,
                    }
                    
# This method wirtes the bitencodings into
# the memory. The parameters are overwritten
# if one of the operands is an register
# tttn isn't used yet
# extra is an extra byte for long opcodes like IMUL
def make_two_operand_instr(W = None, R = None, X = None, B = None, opcode =None, m = None, md1 = None, md2 = None, tttn = None, extra = None):
    def quadreg_instr(self, arg1, arg2):
        # move the parameter 
        # to the inner function
        mod = m
        modrm1 = md1
        modrm2 = md2
        rexW = W
        rexR = R
        rexX = X
        rexB = B
        # TODO: other cases e.g memory as operand
        if isinstance(arg1,Register64):
            rexR, modrm1 = self.get_register_bits(arg1.reg)
        elif isinstance(arg1,Register8):
            modrm1 = self.get_register_bits_8Bit(arg1.reg)
            
        # exchange the two arguments (modrm2/modrm1)
        if isinstance(arg2,Immediate32):
            # e.g: IMUL (source==dest)
            if(modrm2=="sameReg"):
                modrm2 = modrm1
                rexB = rexR
            self.write_rex_byte(rexW, rexR, rexX, rexB)
            self.write(opcode)
            self.write_modRM_byte(3, modrm2, modrm1)
            self.writeImm32(arg2.value)
        elif isinstance(arg2,Immediate8):
            self.write_rex_byte(rexW, rexR, rexX, rexB)
            self.write(opcode)
            self.write_modRM_byte(3, modrm2, modrm1)
            self.write(chr(arg2.value)) 
        elif isinstance(arg2,Register64):
            rexB, modrm2 = self.get_register_bits(arg2.reg)            
            # FIXME: exchange the two arguments (rexB/rexR)
            self.write_rex_byte(rexW, rexB, rexX, rexR)
            self.write(opcode)
            # used in imul (extra long opcode)
            if not extra == None:
                self.write(extra)
            self.write_modRM_byte(mod, modrm2, modrm1)        
    return quadreg_instr
        
        
# This method wirtes the bitencodings into
# the memory. The parameters are overwritten
# if one of the operands is an register
# tttn codes the flags and is only used by SETcc
def make_one_operand_instr(W = None, R = None, X = None, B = None, opcode = None, m = None, md1 = None, md2 = None, tttn=None, extra = None):
    def quadreg_instr(self, arg1):       
        # move the parameter 
        # to the inner function
        mod = m
        modrm1 = md1
        modrm2 = md2
        rexW = W
        rexR = R
        rexX = X
        rexB = B
        
        # TODO: other cases e.g memory as operand
        if isinstance(arg1,Register64):
            rexB, modrm1 = self.get_register_bits(arg1.reg)
        if isinstance(arg1,Register8):
            modrm1 = self.get_register_bits_8Bit(arg1.reg)
            
        # rexW(1) = 64bitMode 
        self.write_rex_byte(rexW, rexR, rexX, rexB)
        self.write(opcode)
        if not tttn == None:
            byte = (9 << 4) | tttn
            self.write(chr(byte))
        self.write_modRM_byte(mod, modrm2, modrm1)        
    return quadreg_instr
        
# TODO: comment        
def make_two_operand_instr_with_alternate_encoding(W = None, R = None, X = None, B = None, opcode =None, md1 = None, md2 = None):
    def quadreg_instr(self, arg1, arg2):
        # move the parameter 
        # to the inner function
        modrm1 = md1
        modrm2 = md2
        rexW = W
        rexR = R
        rexX = X
        rexB = B
        # TODO: other cases e.g memory as operand
        # FIXME: rexB?
        if isinstance(arg1,Register64):
            rexB, modrm1 = self.get_register_bits(arg1.reg)
            
        # exchange the two arguments (modrm2/modrm1)
        if isinstance(arg2,Immediate64):
            self.write_rex_byte(rexW, rexR, rexX, rexB)
            self.write(opcode+chr(modrm1))
            self.writeImm64(arg2.value)
    return quadreg_instr
        
class X86_64CodeBuilder(object):
    """ creats x86_64 opcodes"""
    def write(self, data):
        """ writes data into memory"""
        raise NotImplementedError
    
    def tell(self):
        """ tells the current position in memory"""
        raise NotImplementedError
    
    
    # The opcodes differs depending on the operands
    # Params:
    # W, R, X, B, Opcode, mod, modrm1, modrm2, tttn(JUMPS), extraopcode 
    
    # FIXME: rexX,rexB are set
    _ADD_QWREG_IMM32 = make_two_operand_instr(   1,    0,    0,    0, "\x81", 3, None, 2)  
    _ADD_QWREG_QWREG = make_two_operand_instr(   1, None,    0, None, "\x00", 3, None, None)
    
    # FIXME: rexB is set
    _CMP_QWREG_IMM32 = make_two_operand_instr(   1,    0,    0,    1, "\x81", 3, None, 7)
    _CMP_QWREG_QWREG = make_two_operand_instr(   1, None,    0, None, "\x39", 3, None, None)
    # FIXME: rex B is set
    _CMP_8REG_IMM8   = make_two_operand_instr(   0,    0,    0,    0, "\x82", 3, None, 7)
    
    _DEC_QWREG       = make_one_operand_instr(   1,    0,    0, None, "\xFF", 3, None, 1)
    _INC_QWREG       = make_one_operand_instr(   1,    0,    0, None, "\xFF", 3, None, 0)

     
    _MOV_QWREG_IMM32 = make_two_operand_instr(   1,    0,    0, None, "\xC7", 3, None, 0)
    _MOV_QWREG_QWREG = make_two_operand_instr(   1, None,    0, None, "\x89", 3, None, None)
    _MOV_QWREG_IMM64 = make_two_operand_instr_with_alternate_encoding(1,0,0,None,"\xB8",None,None)
        
    _IMUL_QWREG_QWREG = make_two_operand_instr(  1, None,    0, None, "\x0F", 3, None, None, None, "\xAF")
    _IMUL_QWREG_IMM32 = make_two_operand_instr(  1, None,    0, None, "\x69", 3, None, "sameReg")
    
    _JMP_QWREG       = make_one_operand_instr(   1,    0,    0, None, "\xFF", 3, None, 4)

    # FIXME: rexW is set 
    _POP_QWREG       = make_one_operand_instr(   1,    0,    0, None, "\x8F", 3, None, 0)
    _PUSH_QWREG      = make_one_operand_instr(   1,    0,    0, None, "\xFF", 3, None, 6)
     
    _SETG_8REG       = make_one_operand_instr(   0,    0,    0,    0, "\x0F", 3, None, 0,15)
     
    _SUB_QWREG_QWREG = make_two_operand_instr(   1, None,    0, None, "\x28", 3, None, None)    
    _SUB_QWREG_IMM32 = make_two_operand_instr(   1,    0,    0,    0, "\x81", 3, None, 5)
    
    # TODO: maybe a problem with more ore less than two arg.
    def ADD(self, op1, op2):
        method = getattr(self, "_ADD"+op1.to_string()+op2.to_string())
        method(op1, op2)
        
    def CMP(self, op1, op2):
        method = getattr(self, "_CMP"+op1.to_string()+op2.to_string())
        method(op1, op2)
        
    def DEC(self, op1):
        method = getattr(self, "_DEC"+op1.to_string())
        method(op1)
        
    def INC(self, op1):
        method = getattr(self, "_INC"+op1.to_string())
        method(op1)
        
    # op1 must be a register
    def JMP(self,op1):
        method = getattr(self, "_JMP"+op1.to_string())
        method(op1)
        #self.write("\xE9")
        #self.writeImm32(displ)
        
    def POP(self, op1):
        method = getattr(self, "_POP"+op1.to_string())
        method(op1)
        
    def PUSH(self, op1):
        method = getattr(self, "_POP"+op1.to_string())
        method(op1)
        
    def MOV(self, op1, op2):
        method = getattr(self, "_MOV"+op1.to_string()+op2.to_string())
        method(op1, op2)
        
    def IMUL(self, op1, op2):
        method = getattr(self, "_IMUL"+op1.to_string()+op2.to_string())
        # exchange the two arguments because 
        # the result is in the first register 
        if(op1.to_string()=="_QWREG" and op2.to_string()=="_QWREG"):
            method(op2, op1)
        else:
            method(op1, op2)
    
    def RET(self):
        self.write("\xC3")
        
    def SETG(self, op1):
        method = getattr(self, "_SETG"+op1.to_string())
        method(op1)
        
    def SUB(self, op1, op2):
        method = getattr(self, "_SUB"+op1.to_string()+op2.to_string())
        method(op1, op2)
        
    def get_register_bits(self, register):
        return REGISTER_MAP[register]
    
    def get_register_bits_8Bit(self, register):
        return REGISTER_MAP_8BIT[register]
    
    # Parse the integervalue to an charakter
    # and write it
    def writeImm32(self, imm32):
        x = hex(imm32)
        # parse to string and cut "0x" off
        # fill with zeros if to short
        y = "0"*(10-len(x))+x[2:len(x)]
        assert len(y) == 8            
        self.write(chr(int(y[6:8],16))) 
        self.write(chr(int(y[4:6],16)))
        self.write(chr(int(y[2:4],16)))
        self.write(chr(int(y[0:2],16)))
        
        
    # Parse the integervalue to an charakter
    # and write it
    def writeImm64(self, imm64):
        x = hex(imm64)
        # parse to string and cut "0x" off
        # fill with zeros if to short
        y = "0"*(18-len(x))+x[2:len(x)]
        assert len(y) == 16    
        self.write(chr(int(y[14:16],16))) 
        self.write(chr(int(y[12:14],16)))
        self.write(chr(int(y[10:12],16)))
        self.write(chr(int(y[8:10],16)))        
        self.write(chr(int(y[6:8],16))) 
        self.write(chr(int(y[4:6],16)))
        self.write(chr(int(y[2:4],16)))
        self.write(chr(int(y[0:2],16)))
            
    
    # Rex-Prefix 4WRXB see AMD vol3 page 45
    def write_rex_byte(self, rexW, rexR, rexX, rexB):
        byte = (4 << 4) | (rexW << 3) | (rexR << 2) | (rexX << 1) | rexB
        self.write(chr(byte))
        
    def write_modRM_byte(self, mod, reg, rm):
        byte = mod << 6 | (reg << 3) | rm
        self.write(chr(byte))
        
