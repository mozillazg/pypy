from pypy.rlib.objectmodel import specialize
from pypy.jit.codegen.model import AbstractRGenOp, GenLabel, GenBuilder
from pypy.jit.codegen.model import GenVar, GenConst, CodeGenSwitch


class Var(GenVar):

    def __init__(self):
        pass

    #repr?


class IntConst(GenConst):

    def __init__(self, value):
            self.value = value

    @specialize.arg(1)
    def revealconst(self, T):
        if isinstance(T, lltype.Ptr):
            return lltype.cast_int_to_ptr(T, self.value)
        elif T is llmemory.Address:
            return llmemory.cast_int_to_adr(self.value)
        else:
            return lltype.cast_primitive(T, self.value)

    #repr?


class AddrConst(GenConst):

    def __init__(self, addr):
        self.addr = addr

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

    #repr?


class Label(GenLabel):

    def __init__(self, startaddr, arg_positions, stackdepth):
        self.startaddr = startaddr
        self.arg_positions = arg_positions
        self.stackdepth = stackdepth


class FlexSwitch(CodeGenSwitch):

    #<comment>

    def __init__(self, rgenop):
        self.rgenop = rgenop
        self.default_case_addr = 0

    def initialize(self, builder, gv_exitswitch):
        mc = builder.mc
        mc.MOV(eax, gv_exitswitch.operand(builder))
        self.saved_state = builder._save_state()
        self._reserve(mc)

    def _reserve(self, mc):
        RESERVED = 11*4+5      # XXX quite a lot for now :-/
        pos = mc.tell()
        mc.UD2()
        mc.write('\x00' * (RESERVED-1))
        self.nextfreepos = pos
        self.endfreepos = pos + RESERVED

    def _reserve_more(self):
        start = self.nextfreepos
        end   = self.endfreepos
        newmc = self.rgenop.open_mc()
        self._reserve(newmc)
        self.rgenop.close_mc(newmc)
        fullmc = InMemoryCodeBuilder(start, end)
        fullmc.JMP(rel32(self.nextfreepos))
        fullmc.done()

    def add_case(self, gv_case):
        rgenop = self.rgenop
        targetbuilder = Builder._new_from_state(rgenop, self.saved_state)
        target_addr = targetbuilder.mc.tell()
        try:
            self._add_case(gv_case, target_addr)
        except CodeBlockOverflow:
            self._reserve_more()
            self._add_case(gv_case, target_addr)
        return targetbuilder

    def _add_case(self, gv_case, target_addr):
        start = self.nextfreepos
        end   = self.endfreepos
        mc = InMemoryCodeBuilder(start, end)
        mc.CMP(eax, gv_case.operand(None))
        mc.JE(rel32(target_addr))
        pos = mc.tell()
        if self.default_case_addr:
            mc.JMP(rel32(self.default_case_addr))
        else:
            illegal_start = mc.tell()
            mc.JMP(rel32(0))
            ud2_addr = mc.tell()
            mc.UD2()
            illegal_mc = InMemoryCodeBuilder(illegal_start, end)
            illegal_mc.JMP(rel32(ud2_addr))
        mc.done()
        self.nextfreepos = pos

    def add_default(self):
        rgenop = self.rgenop
        targetbuilder = Builder._new_from_state(rgenop, self.saved_state)
        self.default_case_addr = targetbuilder.mc.tell()
        start = self.nextfreepos
        end   = self.endfreepos
        mc = InMemoryCodeBuilder(start, end)
        mc.JMP(rel32(self.default_case_addr))
        mc.done()
        return targetbuilder

    #</comment>


class Builder(GenBuilder):

    def __init__(self, rgenop):
        self.rgenop = rgenop

    # ----------------------------------------------------------------
    # The public Builder interface

    def end(self):
        pass

    @specialize.arg(1)
    def genop1(self, opname, gv_arg):
        genmethod = getattr(self, 'op_' + opname)
        return genmethod(gv_arg)

    @specialize.arg(1)
    def genop2(self, opname, gv_arg1, gv_arg2):
        genmethod = getattr(self, 'op_' + opname)
        return genmethod(gv_arg1, gv_arg2)



class RLLVMGenOp(AbstractRGenOp):

    def __init__(self):
        #self.mcs = []   # machine code blocks where no-one is currently writing
        #self.keepalive_gc_refs = []
        pass

    # ----------------------------------------------------------------
    # the public RGenOp interface

    def openbuilder(self):
        return Builder(self)

    def newgraph(self, sigtoken, name):
        numargs = sigtoken          # for now
        builder = self.openbuilder()
        entrypoint = builder.asm.mc.tell()
        inputargs_gv = builder._write_prologue(sigtoken)
        return builder, IntConst(entrypoint), inputargs_gv

    @specialize.genconst(1)
    def genconst(self, llvalue):    #i386 version (ppc version is slightly different)
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
        return llmemory.offsetof(T, name)

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
        return None     # for now

    @staticmethod
    @specialize.memo()
    def sigToken(FUNCTYPE):
        return len(FUNCTYPE.ARGS)     # for now

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


global_rgenop = RLLVMGenOp()
RLLVMGenOp.constPrebuiltGlobal = global_rgenop.genconst
