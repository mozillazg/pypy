
from pypy.jit.codegen.model import AbstractRGenOp, GenLabel, GenBuilder
from pypy.jit.codegen.model import GenVar, GenConst, CodeGenSwitch
from pypy.jit.codegen.model import ReplayBuilder, dummy_var
from pypy.rlib.objectmodel import specialize
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.jit.codegen.ia32.operation import *
from pypy.jit.codegen.ia32.regalloc import RegAlloc
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
        self.coming_from = None

    def genop_call(self, sigtoken, gv_fnptr, args_gv):
        op = OpCall(sigtoken, gv_fnptr, list(args_gv))
        self.operations.append(op)
        return op

    def start_mc(self):
        mc = self.rgenop.open_mc()
        # update the coming_from instruction
        start = self.coming_from
        if start:
            targetaddr = mc.tell()
            end = self.coming_from_end
            fallthrough = targetaddr == end
            #if self.update_defaultcaseaddr_of:   # hack for FlexSwitch
            #    self.update_defaultcaseaddr_of.defaultcaseaddr = targetaddr
            #    fallthrough = False
            if fallthrough:
                # the jump would be with an offset 0, i.e. it would go
                # exactly after itself, so we don't really need the jump
                # instruction at all and we can overwrite it and continue.
                mc.seekback(end - start)
                targetaddr = start
            else:
                # normal case: patch the old jump to go to targetaddr
                oldmc = self.rgenop.InMemoryCodeBuilder(start, end)
                insn = EMIT_JCOND[self.coming_from_cond]
                insn(oldmc, rel32(targetaddr))
                oldmc.done()
            self.coming_from = 0
        return mc

    def set_coming_from(self, mc, insncond=INSN_JMP):
        self.coming_from_cond = insncond
        self.coming_from = mc.tell()
        insnemit = EMIT_JCOND[insncond]
        insnemit(mc, rel32(-1))
        self.coming_from_end = mc.tell()

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
        if gv_returnvar is not None:
            regalloc.generate_final_var(mc, gv_returnvar, eax)
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
        # <I don't understand>
        # this probably depends on how much we do call from inside
        # still, looks quite messy...
        write_stack_reserve(mc, 1)
        # </I don't understand>
        for i in range(len(inputargs_gv)):
            input_gv = inputargs_gv[i]
            inputoperands.append(mem(ebp, ofs))
            ofs += input_gv.SIZE
        builder = Builder(self, inputoperands, inputargs_gv)
        builder.set_coming_from(mc)
        mc.done()
        self.close_mc(mc)
        # XXX copy of inputargs_gv?
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
