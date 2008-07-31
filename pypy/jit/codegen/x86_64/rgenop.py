from pypy.jit.codegen import model
from pypy.rlib.objectmodel import specialize
from pypy.jit.codegen.x86_64.objmodel import IntVar, Const
from pypy.jit.codegen.x86_64.codebuf import InMemoryCodeBuilder

class Builder(model.GenBuilder):

    MC_SIZE = 65536

    def __init__(self):
        self.mc = InMemoryCodeBuilder(self.MC_SIZE)
        self.freeregisters ={        
                "rax":None,
                "rcx":None,
                "rdx":None,
              #  "rbx":None,
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
        
    @specialize.arg(1)
    def genop1(self, opname, gv_arg):
        genmethod = getattr(self, 'op_' + opname)
        return genmethod(gv_arg)

    @specialize.arg(1)
    def genop2(self, opname, gv_arg1, gv_arg2):
        genmethod = getattr(self, 'op_' + opname)
        return genmethod(gv_arg1, gv_arg2)
    
    def op_int_add(self, gv_x, gv_y):
        gv_z = self.allocate_register()
        self.mc.MOV(gv_z.reg, gv_x.reg)
        self.mc.ADD(gv_z.reg, gv_y.reg)
        return gv_z
    
    def finish_and_return(self, sigtoken, gv_returnvar):
        #self.mc.write("\xB8\x0F\x00\x00\x00")
        self.mc.MOV("rax", gv_returnvar.reg)
        self.mc.RET()
    
    def allocate_register(self, register=None):
        if register is None:
            return IntVar(self.freeregisters.popitem()[0])
        else:
            del self.freeregisters[register]
            return IntVar(register)
        

class RX86_64GenOp(model.AbstractRGenOp):


    @staticmethod
    @specialize.memo()
    def sigToken(FUNCTYPE):
        return None
    
    def newgraph(self, sigtoken, name):
        # XXX for now assume that all functions take two ints and return an int
        builder = Builder()
        inputargs_gv = [builder.allocate_register("rdi"),
                        builder.allocate_register("rsi")]
        #XXX
        entrypoint = Const(builder.mc.tell())
        return builder, entrypoint, inputargs_gv
    
