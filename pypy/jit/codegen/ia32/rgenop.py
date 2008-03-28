
from pypy.jit.codegen.model import AbstractRGenOp, GenLabel, GenBuilder
from pypy.jit.codegen.model import GenVar, GenConst, CodeGenSwitch
from pypy.jit.codegen.model import ReplayBuilder, dummy_var
from pypy.rlib.objectmodel import specialize
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.jit.codegen.ia32.operation import *
from pypy.jit.codegen.ia32.regalloc import RegAlloc
# XXX explain
from pypy.jit.codegen.i386.regalloc import write_stack_reserve

WORD = 4
PROLOGUE_FIXED_WORDS = 5

class IntConst(GenConst):
    def __init__(self, value):
        self.value = value

    def repr(self):
        return "const=$%s" % (self.value,)

class IntVar(GenVar):
    token = "i"
    ll_type = lltype.Signed
    SIZE = WORD

class FloatVar(GenVar):
    token = "f"
    ll_type = lltype.Float
    SIZE = 8 # XXX really?

LL_TO_GENVAR = {}
TOKEN_TO_GENVAR = {}
for value in locals().values():
    if hasattr(value, 'll_type'):
        LL_TO_GENVAR[value.ll_type] = value.token
        TOKEN_TO_GENVAR[value.token] = value

class Builder(GenBuilder):
    def __init__(self, rgenop, inputoperands, inputvars):
        self.rgenop = rgenop
        self.operations = []
        self.inputoperands = inputoperands
        self.inputvars = inputvars

    def genop_call(self, sigtoken, gv_fnptr, args_gv):
        op = OpCall(sigtoken, gv_fnptr, list(args_gv))
        self.operations.append(op)
        return op

    def start_mc(self):
        mc = self.rgenop.open_mc()
        # XXX we completely ignore additional logic that would generate a jump
        #     to another block if we run out of space
        return mc

    @specialize.arg(1)
    def genop2(self, opname, gv_arg1, gv_arg2):
        cls = getopclass2(opname)
        op = cls(gv_arg1, gv_arg2)
        self.operations.append(op)
        return op

    def finish_and_return(self, sigtoken, gv_returnvar):
        mc = self.start_mc()
        regalloc = RegAlloc(self.operations)
        for i in range(len(self.inputoperands)):
            inp_loc = self.inputoperands[i]
            inp_gv = self.inputvars[i]
            regalloc.set_position(inp_gv, inp_loc)
        regalloc.generate_operations(mc)
        # --- epilogue ---
        mc.MOV(esp, ebp)
        mc.POP(ebp)
        mc.POP(edi)
        mc.POP(esi)
        mc.POP(ebx)
        mc.RET()
        # ----------------
        mc.done()
        self.rgenop.close_mc(mc)

    def end(self):
        pass

class RI386GenOp(AbstractRGenOp):
    from pypy.jit.codegen.i386.codebuf import MachineCodeBlock
    from pypy.jit.codegen.i386.codebuf import InMemoryCodeBuilder

    MC_SIZE = 65536 * 16

    def __init__(self):
        self.allocated_mc = None
        self.keepalive_gc_refs = [] 

    def open_mc(self):
        # XXX supposed infinite for now
        mc = self.allocated_mc
        if mc is None:
            return self.MachineCodeBlock(self.MC_SIZE)
        else:
            self.allocated_mc = None
            return mc

    def close_mc(self, mc):
        assert self.allocated_mc is None
        self.allocated_mc = mc

    @specialize.genconst(1)
    def genconst(self, llvalue):
        T = lltype.typeOf(llvalue)
        if T is llmemory.Address:
            return AddrConst(llvalue)
        elif T is lltype.Signed:
            return IntConst(llvalue)
        elif isinstance(T, lltype.Ptr):
            lladdr = llmemory.cast_ptr_to_adr(llvalue)
            if T.TO._gckind == 'gc':
                self.keepalive_gc_refs.append(lltype.cast_opaque_ptr(llmemory.GCREF, llvalue))
            return AddrConst(lladdr)
        else:
            raise NotImplementedError(llvalue)

    def newgraph(self, sigtoken, name):
        mc = self.open_mc()
        entrypoint = mc.tell()
        # push on stack some registers
        mc.PUSH(ebx)
        mc.PUSH(esi)
        mc.PUSH(edi)
        mc.PUSH(ebp)
        mc.MOV(ebp, esp)
        inputargs_gv = [TOKEN_TO_GENVAR[i]() for i in sigtoken[0]]
        ofs = WORD * PROLOGUE_FIXED_WORDS
        inputoperands = []
        for i in range(len(inputargs_gv)):
            input_gv = inputargs_gv[i]
            inputoperands.append(mem(ebp, ofs))
            ofs += input_gv.SIZE
        # XXX <I don't understand this>
        write_stack_reserve(mc, len(inputoperands) * WORD)
        # XXX </I don't understand this>
        builder = Builder(self, inputoperands, inputargs_gv)
        mc.done()
        self.close_mc(mc)
        # XXX copy?
        return builder, IntConst(entrypoint), inputargs_gv

    @staticmethod
    @specialize.memo()
    def kindToken(T):
        # XXX this will die eventually
        return None

    @staticmethod
    @specialize.memo()
    def sigToken(FUNCTYPE):
        # XXX we need to make this RPython probably
        return ([LL_TO_GENVAR[arg] for arg in FUNCTYPE.ARGS],
                LL_TO_GENVAR[FUNCTYPE.RESULT])

    def check_no_open_mc(self):
        pass
