from pypy.jit.codegen.x86_64.objmodel import Register64, Immediate32

#Mapping from register to coding (Rex.W or Rex.B , ModRM)
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

# This method wirtes the bitencodings into
# the memory. The parameters are overwritten
# if one of the operands is an register
def make_two_operand_instr(W = None, R = None, X = None, B = None, opcode =None, md1 = None, md2 = None):
    def quadreg_instr(self, arg1, arg2):
        # move the parameter 
        # to the inner function
        modrm1 = md1
        modrm2 = md2
        rexW = W
        rexR = R
        rexX = X
        rexB = B
        # Todo: other cases e.g memory as operand
        if isinstance(arg1,Register64):
            rexR, modrm1 = self.get_register_bits(arg1.reg)
            
        if isinstance(arg2,Register64):
            rexB, modrm2 = self.get_register_bits(arg2.reg)
            
        # exchange the two arguments (modrm2/modrm1)
        if isinstance(arg2,Immediate32):
            self.write_rex_byte(rexW, rexR, rexX, rexB)
            self.write(opcode)
            self.write_modRM_byte(3, modrm2, modrm1)
            # FIXME: Bad solution
            # TODO: support values > 255
            if(arg2.value<256):
                self.write(chr(arg2.value)) 
                self.write(chr(0))
                self.write(chr(0))
                self.write(chr(0))
        else:
            # FIXME: exchange the two arguments (rexB/rexR)
            self.write_rex_byte(rexW, rexB, rexX, rexR)
            self.write(opcode)
            self.write_modRM_byte(3, modrm2, modrm1)        
    return quadreg_instr
        
        
# This method wirtes the bitencodings into
# the memory. The parameters are overwritten
# if one of the operands is an register
def make_one_operand_instr(W = None, R = None, X = None, B = None, opcode = None,  md1 = None, md2 = None):
    def quadreg_instr(self, arg1):       
        # move the parameter 
        # to the inner function
        modrm1 = md1
        modrm2 = md2
        rexW = W
        rexR = R
        rexX = X
        rexB = B
        
        # Todo: other cases e.g memory as operand
        if isinstance(arg1,Register64):
            rexB, modrm1 = self.get_register_bits(arg1.reg)
            
        # rexW(1) = 64bitMode 
        self.write_rex_byte(rexW, rexR, rexX, rexB)
        self.write(opcode)
        self.write_modRM_byte(3, modrm2, modrm1)        
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
    
    # FIXME: rexX,rexB are set
    _ADD_QWREG_IMM32 = make_two_operand_instr(   1,    0,    0,    0, "\x81", None, 2)  
    _ADD_QWREG_QWREG = make_two_operand_instr(   1, None,    0, None, "\x00", None, None)
    
    _DEC_QWREG       = make_one_operand_instr(   1,    0,    0, None, "\xFF", None, 1)
    _INC_QWREG       = make_one_operand_instr(   1,    0,    0, None, "\xFF", None, 0)

     
    _MOV_QWREG_IMM32 = make_two_operand_instr(   1,    0,    0, None, "\xC7", None, 0)
    _MOV_QWREG_QWREG = make_two_operand_instr(   1, None,    0, None, "\x89", None, None)
    
    # FIXME: rexW is set 
    _POP_QWREG       = make_one_operand_instr(   1,    0,    0, None, "\x8F", None, 0)
    _PUSH_QWREG      = make_one_operand_instr(   1,    0,    0, None, "\xFF", None, 6)
     
    _SUB_QWREG_QWREG = make_two_operand_instr(   1, None,    0, None, "\x28", None, None)
    
    # TODO: maybe a problem with more ore less than two arg.
    def ADD(self, op1, op2):
        method = getattr(self, "_ADD"+op1.to_string()+op2.to_string())
        method(op1, op2)
        
    def DEC(self, op1):
        method = getattr(self, "_DEC"+op1.to_string())
        method(op1)
        
    def INC(self, op1):
        method = getattr(self, "_INC"+op1.to_string())
        method(op1)
        
    def POP(self, op1):
        method = getattr(self, "_POP"+op1.to_string())
        method(op1)
        
    def PUSH(self, op1):
        method = getattr(self, "_POP"+op1.to_string())
        method(op1)
        
    def MOV(self, op1, op2):
        method = getattr(self, "_MOV"+op1.to_string()+op2.to_string())
        method(op1, op2)
    
    def RET(self):
        self.write("\xC3")
        
    def SUB(self, op1, op2):
        method = getattr(self, "_SUB"+op1.to_string()+op2.to_string())
        method(op1, op2)
        
    def get_register_bits(self, register):
        return REGISTER_MAP[register]
    
    
    # Rex-Prefix 4WRXB see AMD vol3 page 45
    def write_rex_byte(self, rexW, rexR, rexX, rexB):
        byte = (4 << 4) | (rexW << 3) | (rexR << 2) | (rexX << 1) | rexB
        self.write(chr(byte))
        
    def write_modRM_byte(self, mod, reg, rm):
        byte = mod << 6 | (reg << 3) | rm
        self.write(chr(byte))
        
