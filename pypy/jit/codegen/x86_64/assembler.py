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

class X86_64CodeBuilder(object):
    """ creats x86_64 opcodes"""
    def write(self, data):
        """ writes data into memory"""
        raise NotImplementedError
    
    def tell(self):
        """ tells the current position in memory"""
        raise NotImplementedError
    
    # XXX for now, arg1 and arg2 are registers
    def ADD(self, arg1, arg2):
        rexR, modrm1 = self.get_register_bits(arg1)
        rexB, modrm2 = self.get_register_bits(arg2)
        #rexW(1) = 64bitMode rexX(0) = doesn't matter
        self.write_rex_byte(1, rexR, 0, rexB)
        self.write('\x00')
        self.write_modRM_byte(3, modrm1, modrm2)
               
    def get_register_bits(self, register):
        return REGISTER_MAP[register]
    
    # Rex-Prefix 4WRXB see AMD vol3 page 45
    def write_rex_byte(self, rexW, rexR, rexX, rexB):
        byte = (4 << 4) | (rexW << 3) | (rexR << 2) | (rexX << 1) | rexB
        self.write(chr(byte))
        
    def write_modRM_byte(self, mod, reg, rm):
        byte = mod << 6 | (reg << 3) | rm
        self.write(chr(byte))