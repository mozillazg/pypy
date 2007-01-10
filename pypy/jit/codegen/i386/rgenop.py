from pypy.rlib.objectmodel import specialize
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.jit.codegen.model import AbstractRGenOp, GenLabel, GenBuilder
from pypy.jit.codegen.model import GenVar, GenConst, CodeGenSwitch
from pypy.jit.codegen.i386.ri386 import *
from pypy.jit.codegen.i386 import conftest


WORD = 4    # bytes


class Operation(GenVar):
    def allocate_registers(self, allocator):
        pass
    def generate(self, allocator):
        raise NotImplementedError

class Op1(Operation):
    def __init__(self, x):
        self.x = x
    def allocate_registers(self, allocator):
        allocator.using(self.x)
    def generate(self, allocator):
        operand = allocator.var2loc[self]
        allocator.load_operand(operand, self.x)
        self.emit(allocator.mc, operand)

class OpSameAs(Op1):
    emit = staticmethod(lambda mc, x: None)

class Op2(Operation):
    def __init__(self, x, y):
        self.x = x
        self.y = y
    def allocate_registers(self, allocator):
        allocator.using(self.x)
        allocator.using(self.y)
    def generate(self, allocator):
        operand1 = allocator.var2loc[self]
        allocator.load_operand(operand1, self.x)
        operand2 = allocator.get_location(self.y)
        self.emit(allocator.mc, operand1, operand2)

class OpIntAdd(Op2):
    opname = 'int_add'
    emit = staticmethod(I386CodeBuilder.ADD)

class OpIntSub(Op2):
    opname = 'int_sub'
    emit = staticmethod(I386CodeBuilder.SUB)

# ____________________________________________________________

class IntConst(GenConst):

    def __init__(self, value):
        self.value = value

    def operand(self, builder):
        return imm(self.value)

    def nonimmoperand(self, builder, tmpregister):
        builder.mc.MOV(tmpregister, self.operand(builder))
        return tmpregister

    @specialize.arg(1)
    def revealconst(self, T):
        if isinstance(T, lltype.Ptr):
            return lltype.cast_int_to_ptr(T, self.value)
        elif T is llmemory.Address:
            return llmemory.cast_int_to_adr(self.value)
        else:
            return lltype.cast_primitive(T, self.value)

    def __repr__(self):
        "NOT_RPYTHON"
        try:
            return "const=%s" % (imm(self.value).assembler(),)
        except TypeError:   # from Symbolics
            return "const=%r" % (self.value,)

    def repr(self):
        return "const=$%s" % (self.value,)

class AddrConst(GenConst):

    def __init__(self, addr):
        self.addr = addr

    def operand(self, builder):
        return imm(llmemory.cast_adr_to_int(self.addr))

    def nonimmoperand(self, builder, tmpregister):
        builder.mc.MOV(tmpregister, self.operand(builder))
        return tmpregister

    @specialize.arg(1)
    def revealconst(self, T):
        if T is llmemory.Address:
            return self.addr
        elif isinstance(T, lltype.Ptr):
            return llmemory.cast_adr_to_ptr(self.addr, T)
        elif T is lltype.Signed:
            return llmemory.cast_adr_to_int(self.addr)
        else:
            assert 0, "XXX not implemented"

    def __repr__(self):
        "NOT_RPYTHON"
        return "const=%r" % (self.addr,)

    def repr(self):
        return "const=<0x%x>" % (llmemory.cast_adr_to_int(self.addr),)

# ____________________________________________________________

def setup_opclasses(base):
    d = {}
    for name, value in globals().items():
        if type(value) is type(base) and issubclass(value, base):
            if hasattr(value, 'opname'):
                assert value.opname not in d
                d[value.opname] = value
    return d
OPCLASSES1 = setup_opclasses(Op1)
OPCLASSES2 = setup_opclasses(Op2)
del setup_opclasses


class RegAllocator(object):
    AVAILABLE_REGS = [eax, ecx, edx, ebx, esi, edi]
    AVAILABLE_REGS_REV = AVAILABLE_REGS[:]
    AVAILABLE_REGS_REV.reverse()

    def __init__(self, operations, input_var2loc):
        self.operations = operations
        self.input_var2loc = input_var2loc
        self.var2loc = {}

    def set_final(self, final_vars_gv, final_locs):
        used = {}
        for i in range(len(final_vars_gv)):
            v = final_vars_gv[i]
            loc = final_locs[i]
            if v.is_const or v in self.var2loc or (
                self.input_var2loc.get(v, loc) != loc):
                v = OpSameAs(v)
                self.operations.append(v)
            self.var2loc[v] = loc
            used[loc] = True
        self.available_regs = [reg for reg in self.AVAILABLE_REGS_REV
                                   if reg not in used]

    def creating(self, v):
        loc = self.var2loc.get(v, None)
        if isinstance(loc, REG):
            self.available_regs.append(loc)

    def using(self, v):
        if not v.is_const and v not in self.var2loc:
            try:
                loc = self.input_var2loc[v]
            except KeyError:
                try:
                    loc = self.available_regs.pop()
                except IndexError:
                    #loc = ...
                    raise NotImplementedError
            self.var2loc[v] = loc

    def get_location(self, gv_source):
        if isinstance(gv_source, IntConst):
            return imm(gv_source.value)
        else:
            return self.var2loc[gv_source]

    def load_operand(self, operand, gv_source):
        srcloc = self.get_location(gv_source)
        if srcloc != operand:
            self.mc.MOV(operand, srcloc)


class Builder(GenBuilder):
    coming_from = 0

    def __init__(self, rgenop, input_vars_gv, input_var2loc):
        self.rgenop = rgenop
        self.input_vars_gv = input_vars_gv
        self.input_var2loc = input_var2loc

    def start_writing(self):
        self.operations = []

    def generate_block_code(self, final_vars_gv, final_locs):
        operations = self.operations
        allocator = RegAllocator(operations, self.input_var2loc)
        allocator.set_final(final_vars_gv, final_locs)
        for i in range(len(operations)-1, -1, -1):
            v = operations[i]
            allocator.creating(v)
            v.allocate_registers(allocator)
        mc = self.start_mc()
        allocator.mc = mc
        for op in operations:
            op.generate(allocator)
        self.operations = None
        return mc

    def enter_next_block(self, kinds, args_gv):
        locs = {}
        seen_regs = 0
        for v in args_gv:
            loc = self.input_var2loc.get(v, None)
            locs[v] = loc
            if isinstance(loc, REG):
                i = loc.op
                seen_regs |= 1 << i
        i = 0
        final_locs = []
        final_var2loc = {}
        for v in args_gv:
            loc = locs[v]
            if loc is None:
                while seen_regs & (1 << i):
                    i += 1
                assert i < len(RegAllocator.AVAILABLE_REGS)   # XXX
                loc = RegAllocator.AVAILABLE_REGS[i]
                i += 1
            final_locs.append(loc)
            final_var2loc[v] = loc
        mc = self.generate_block_code(args_gv, final_locs)
        self.set_coming_from(mc)
        self.rgenop.close_mc(mc)
        self.input_args_gv = args_gv
        self.input_var2loc = final_var2loc
        self.start_writing()

    def set_coming_from(self, mc, insn=I386CodeBuilder.JMP):
        self.coming_from_insn = insn
        self.coming_from = mc.tell()
        insn(mc, rel32(0))

    def start_mc(self):
        mc = self.rgenop.open_mc()
        # update the coming_from instruction
        start = self.coming_from
        if start:
            targetaddr = mc.tell()
            end = start + 6    # XXX hard-coded, enough for JMP and Jcond
            oldmc = self.rgenop.InMemoryCodeBuilder(start, end)
            insn = self.coming_from_insn
            insn(oldmc, rel32(targetaddr))
            oldmc.done()
            self.coming_from = 0
        return mc

    def finish_and_return(self, sigtoken, gv_returnvar):
        mc = self.generate_block_code([gv_returnvar], [eax])
        # --- epilogue ---
        mc.POP(edi)
        mc.POP(esi)
        mc.POP(ebx)
        mc.POP(ebp)
        mc.RET()
        # ----------------
        self.rgenop.close_mc(mc)

    def end(self):
        pass

    @specialize.arg(1)
    def genop1(self, opname, gv_arg):
        cls = OPCLASSES1[opname]
        op = cls(gv_arg)
        self.operations.append(op)
        return op

    @specialize.arg(1)
    def genop2(self, opname, gv_arg1, gv_arg2):
        cls = OPCLASSES2[opname]
        op = cls(gv_arg1, gv_arg2)
        self.operations.append(op)
        return op


class RI386GenOp(AbstractRGenOp):
    from pypy.jit.codegen.i386.codebuf import MachineCodeBlock
    from pypy.jit.codegen.i386.codebuf import InMemoryCodeBuilder

    MC_SIZE = 65536
    
    def __init__(self):
        self.mcs = []   # machine code blocks where no-one is currently writing
        self.keepalive_gc_refs = [] 
        self.total_code_blocks = 0

    def open_mc(self):
        if self.mcs:
            # XXX think about inserting NOPS for alignment
            return self.mcs.pop()
        else:
            # XXX supposed infinite for now
            self.total_code_blocks += 1
            return self.MachineCodeBlock(self.MC_SIZE)

    def close_mc(self, mc):
        # an open 'mc' is ready for receiving code... but it's also ready
        # for being garbage collected, so be sure to close it if you
        # want the generated code to stay around :-)
        self.mcs.append(mc)

    def check_no_open_mc(self):
        assert len(self.mcs) == self.total_code_blocks

    def newgraph(self, sigtoken, name):
        # --- prologue ---
        mc = self.open_mc()
        entrypoint = mc.tell()
        if conftest.option.trap:
            mc.BREAKPOINT()
        mc.PUSH(ebp)
        mc.MOV(ebp, esp)
        mc.PUSH(ebx)
        mc.PUSH(esi)
        mc.PUSH(edi)
        self.close_mc(mc)
        # NB. a bit of a hack: the first generated block of the function
        # will immediately follow, by construction
        # ----------------
        numargs = sigtoken     # for now
        inputargs_gv = []
        input_var2loc = {}
        for i in range(numargs):
            v = GenVar()
            inputargs_gv.append(v)
            input_var2loc[v] = mem(ebp, WORD * (2+i))
        builder = Builder(self, inputargs_gv, input_var2loc)
        builder.start_writing()
        return builder, IntConst(entrypoint), inputargs_gv

##    def replay(self, label, kinds):
##        return ReplayBuilder(self), [dummy_var] * len(kinds)

    @specialize.genconst(1)
    def genconst(self, llvalue):
        T = lltype.typeOf(llvalue)
        if T is llmemory.Address:
            return AddrConst(llvalue)
        elif isinstance(T, lltype.Primitive):
            return IntConst(lltype.cast_primitive(lltype.Signed, llvalue))
        elif isinstance(T, lltype.Ptr):
            lladdr = llmemory.cast_ptr_to_adr(llvalue)
            if T.TO._gckind == 'gc':
                self.keepalive_gc_refs.append(lltype.cast_opaque_ptr(llmemory.GCREF, llvalue))
            return AddrConst(lladdr)
        else:
            assert 0, "XXX not implemented"
    
    # attached later constPrebuiltGlobal = global_rgenop.genconst

    @staticmethod
    @specialize.memo()
    def fieldToken(T, name):
        FIELD = getattr(T, name)
        if isinstance(FIELD, lltype.ContainerType):
            fieldsize = 0      # not useful for getsubstruct
        else:
            fieldsize = llmemory.sizeof(FIELD)
        return (llmemory.offsetof(T, name), fieldsize)

    @staticmethod
    @specialize.memo()
    def allocToken(T):
        return llmemory.sizeof(T)

    @staticmethod
    @specialize.memo()
    def varsizeAllocToken(T):
        if isinstance(T, lltype.Array):
            return RI386GenOp.arrayToken(T)
        else:
            # var-sized structs
            arrayfield = T._arrayfld
            ARRAYFIELD = getattr(T, arrayfield)
            arraytoken = RI386GenOp.arrayToken(ARRAYFIELD)
            length_offset, items_offset, item_size = arraytoken
            arrayfield_offset = llmemory.offsetof(T, arrayfield)
            return (arrayfield_offset+length_offset,
                    arrayfield_offset+items_offset,
                    item_size)

    @staticmethod
    @specialize.memo()    
    def arrayToken(A):
        return (llmemory.ArrayLengthOffset(A),
                llmemory.ArrayItemsOffset(A),
                llmemory.ItemOffset(A.OF))

    @staticmethod
    @specialize.memo()
    def kindToken(T):
        if T is lltype.Float:
            py.test.skip("not implemented: floats in the i386 back-end")
        return None     # for now

    @staticmethod
    @specialize.memo()
    def sigToken(FUNCTYPE):
        numargs = 0
        for ARG in FUNCTYPE.ARGS:
            if ARG is not lltype.Void:
                numargs += 1
        return numargs     # for now

    @staticmethod
    def erasedType(T):
        if T is llmemory.Address:
            return llmemory.Address
        if isinstance(T, lltype.Primitive):
            return lltype.Signed
        elif isinstance(T, lltype.Ptr):
            return llmemory.GCREF
        else:
            assert 0, "XXX not implemented"

global_rgenop = RI386GenOp()
RI386GenOp.constPrebuiltGlobal = global_rgenop.genconst
