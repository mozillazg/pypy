from pypy.rlib.objectmodel import specialize
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.jit.codegen.model import AbstractRGenOp, GenLabel, GenBuilder
from pypy.jit.codegen.model import GenVar, GenConst, CodeGenSwitch
from pypy.jit.codegen.llvm import llvmjit


def log(s):
    print str(s)
    pass


n_vars = 0

class Var(GenVar):

    def __init__(self):
        global n_vars
        self.name = '%v' + str(n_vars) 
        n_vars += 1

    def operand(self):
        return 'int ' + self.name

    def operand2(self):
        return self.name

    #repr?


class IntConst(GenConst):

    def __init__(self, value):
        self.value = value

    def operand(self):
        return 'int ' + str(self.value)

    def operand2(self):
        return str(self.value)

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

    def operand(self):
        return 'int* ' + str(llmemory.cast_adr_to_int(self.addr))

    def operand2(self):
        return str(llmemory.cast_adr_to_int(self.addr))

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

    def __init__(self, rgenop):
        log('FlexSwitch.__init__')
        self.rgenop = rgenop
        #self.default_case_addr = 0

    def initialize(self, builder, gv_exitswitch):
        log('FlexSwitch.initialize TODO')
        #mc = builder.mc
        #mc.MOV(eax, gv_exitswitch.operand(builder))
        #self.saved_state = builder._save_state()
        #self._reserve(mc)

    def _reserve(self, mc):
        log('FlexSwitch._reserve TODO')
        #RESERVED = 11*4+5      # XXX quite a lot for now :-/
        #pos = mc.tell()
        #mc.UD2()
        #mc.write('\x00' * (RESERVED-1))
        #self.nextfreepos = pos
        #self.endfreepos = pos + RESERVED

    def _reserve_more(self):
        log('FlexSwitch._reserve_more TODO')
        #start = self.nextfreepos
        #end   = self.endfreepos
        #newmc = self.rgenop.open_mc()
        #self._reserve(newmc)
        #self.rgenop.close_mc(newmc)
        #fullmc = InMemoryCodeBuilder(start, end)
        #fullmc.JMP(rel32(self.nextfreepos))
        #fullmc.done()

    def add_case(self, gv_case):
        log('FlexSwitch.add_case TODO')
        #rgenop = self.rgenop
        #targetbuilder = Builder._new_from_state(rgenop, self.saved_state)
        #target_addr = targetbuilder.mc.tell()
        #try:
        #    self._add_case(gv_case, target_addr)
        #except CodeBlockOverflow:
        #    self._reserve_more()
        #    self._add_case(gv_case, target_addr)
        #return targetbuilder

    def _add_case(self, gv_case, target_addr):
        log('FlexSwitch._add_case TODO')
        #start = self.nextfreepos
        #end   = self.endfreepos
        #mc = InMemoryCodeBuilder(start, end)
        #mc.CMP(eax, gv_case.operand(None))
        #mc.JE(rel32(target_addr))
        #pos = mc.tell()
        #if self.default_case_addr:
        #    mc.JMP(rel32(self.default_case_addr))
        #else:
        #    illegal_start = mc.tell()
        #    mc.JMP(rel32(0))
        #    ud2_addr = mc.tell()
        #    mc.UD2()
        #    illegal_mc = InMemoryCodeBuilder(illegal_start, end)
        #    illegal_mc.JMP(rel32(ud2_addr))
        #mc.done()
        #self.nextfreepos = pos

    def add_default(self):
        log('FlexSwitch.add_default TODO')
        #rgenop = self.rgenop
        #targetbuilder = Builder._new_from_state(rgenop, self.saved_state)
        #self.default_case_addr = targetbuilder.mc.tell()
        #start = self.nextfreepos
        #end   = self.endfreepos
        #mc = InMemoryCodeBuilder(start, end)
        #mc.JMP(rel32(self.default_case_addr))
        #mc.done()
        #return targetbuilder


class Builder(object):  #changed baseclass from (GenBuilder) for better error messages

    def __init__(self, rgenop):
        log('Builder.__init__')
        self.rgenop = rgenop
        self.asm = [] #list of llvm assembly source code lines

    # ----------------------------------------------------------------
    # The public Builder interface

    def end(self):
        log('Builder.end')
        self.asm.append('}')
        asm_string = '\n'.join(self.asm)
        log(asm_string)
        llvmjit.parse(asm_string)
        function   = llvmjit.getNamedFunction(self.rgenop.name)
        entrypoint = llvmjit.getPointerToFunction(function)
        self.rgenop.gv_entrypoint.value = entrypoint
        #print self.rgenop.name, 'entrypoint', entrypoint
        #print self.rgenop.gv_entrypoint, self.rgenop.gv_entrypoint.value

    def _write_prologue(self, sigtoken):
        log('Builder._write_prologue')
        numargs = sigtoken     # for now
        inputargs_gv = [Var() for i in range(numargs)]
        self.asm.append('int %%%s(%s){' % (
            self.rgenop.name, ','.join([v.operand() for v in inputargs_gv])))
        return inputargs_gv

    def _close(self):
        log('Builder._close')
        #self.mc.done()
        #self.rgenop.close_mc(self.mc)
        #self.mc = None

    @specialize.arg(1)
    def genop1(self, opname, gv_arg):
        log('Builder.genop1')
        genmethod = getattr(self, 'op_' + opname)
        return genmethod(gv_arg)

    @specialize.arg(1)
    def genop2(self, opname, gv_arg1, gv_arg2):
        log('Builder.genop2')
        genmethod = getattr(self, 'op_' + opname)
        return genmethod(gv_arg1, gv_arg2)

    def op_int_add(self, gv_x, gv_y):
        log('Builder.op_int_add')
        gv_result = Var()
        self.asm.append(" %s=add %s,%s" % (gv_result.name, gv_x.operand(), gv_y.operand2()))
        return gv_result
        #self.mc.MOV(eax, gv_x.operand(self))
        #self.mc.ADD(eax, gv_y.operand(self))
        #return self.returnvar(eax) 

    def enter_next_block(self, kinds, args_gv):
        log('Builder.enter_next_block TODO')
        #arg_positions = []
        #seen = {}
        #for i in range(len(args_gv)):
        #    gv = args_gv[i]
        #    # turn constants into variables; also make copies of vars that
        #    # are duplicate in args_gv
        #    if not isinstance(gv, Var) or gv.stackpos in seen:
        #        gv = args_gv[i] = self.returnvar(gv.operand(self))
        #    # remember the var's position in the stack
        #    arg_positions.append(gv.stackpos)
        #    seen[gv.stackpos] = None
        #return Label(self.mc.tell(), arg_positions, self.stackdepth)

    def finish_and_return(self, sigtoken, gv_returnvar):
        log('Builder.finish_and_return')
        self.asm.append(' ret ' + gv_returnvar.operand())
        #numargs = sigtoken      # for now
        #initialstackdepth = numargs + 1
        #self.mc.MOV(eax, gv_returnvar.operand(self))
        #self.mc.ADD(esp, imm(WORD * (self.stackdepth - initialstackdepth)))
        #self.mc.RET()
        self._close()

    def finish_and_goto(self, outputargs_gv, target):
        log('Builder.finish_and_goto TODO')
        #remap_stack_layout(self, outputargs_gv, target)
        #self.mc.JMP(rel32(target.startaddr))
        self._close()

    def flexswitch(self, gv_exitswitch):
        log('Builder.flexswitch TODO')
        result = FlexSwitch(self.rgenop)
        result.initialize(self, gv_exitswitch)
        self._close()
        return result

    def show_incremental_progress(self):
        log('Builder.show_incremental_progress')
        pass


class RLLVMGenOp(object):   #changed baseclass from (AbstractRGenOp) for better error messages

    def __init__(self):
        #self.mcs = []   # machine code blocks where no-one is currently writing
        #self.keepalive_gc_refs = []
        pass

    # ----------------------------------------------------------------
    # the public RGenOp interface

    def openbuilder(self):
        log('RLLVMGenOp.openbuilder')
        return Builder(self)

    def newgraph(self, sigtoken, name):
        log('RLLVMGenOp.newgraph')
        numargs = sigtoken          # for now
        self.name = name
        builder = self.openbuilder()
        #entrypoint = builder.asm.mc.tell()
        self.gv_entrypoint = IntConst(0)
        inputargs_gv = builder._write_prologue(sigtoken)
        return builder, self.gv_entrypoint, inputargs_gv

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

