
from pypy.jit.codegen.model import GenVar, GenConst, CodeGenSwitch
from pypy.rpython.lltypesystem import lltype, rffi, llmemory
from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.objectmodel import specialize
from pypy.jit.codegen.i386.ri386 import *

WORD = 4

class Var(GenVar):
    token = 'x'
    # XXX hack for annotator
    stackpos = 0

    def __init__(self, stackpos):
        # 'stackpos' is an index relative to the pushed arguments
        # (where N is the number of arguments of the function
        #  and B is a small integer for stack alignment purposes):
        #
        # B + 0  = last arg
        #        = ...
        # B +N-1 = 1st arg
        # B + N  = return address
        # B +N+1 = local var
        # B +N+2 = ...
        #          ...              <--- esp+4
        #          local var        <--- esp
        #
        self.stackpos = stackpos

    def nonimmoperand(self, builder, tmpregister):
        return self.operand(builder)

    def operand(self, builder):
        raise NotImplementedError

    def movetonewaddr(self, builder, addr):
        raise NotImplementedError

    def __repr__(self):
        return self.token + 'var@%d' % (self.stackpos,)

    repr = __repr__

class IntVar(Var):
    ll_type = lltype.Signed
    token = 'i'
    SIZE = 1

    def operand(self, builder):
        return builder.stack_access(self.stackpos)

    def newvar(self, builder):
        return builder.returnintvar(self.operand(builder))

    def movetonewaddr(self, builder, addr):
        dstop = builder.mem_access(addr)
        builder.mc.MOV(eax, self.operand(builder))
        builder.mc.MOV(dstop, eax)

class AddrVar(IntVar):
    ll_type = llmemory.Address
    token = 'a'
    SIZE = 1

class BoolVar(Var):
    ll_type = lltype.Bool
    token = 'b'
    SIZE = 1

    # represents a boolean as an integer which *must* be exactly 0 or 1
    def operand(self, builder):
        return builder.stack_access(self.stackpos)

    def newvar(self, builder):
        return builder.returnboolvar(self.operand(builder))

    def movetonewaddr(self, builder, addr):
        destop = builder.mem_access(addr)
        builder.mc.MOV(eax, self.operand(builder))
        builder.mc.MOV(destop, al)

class FloatVar(Var):
    def operand(self, builder):
        return builder.stack_access64(self.stackpos)

    def newvar(self, builder):
        ofs = (builder.stackdepth - self.stackpos - 1) * WORD
        return builder.newfloatfrommem((esp, None, 0, ofs))

    def movetonewaddr(self, builder, addr):
        dstop1 = builder.mem_access(addr)
        dstop2 = builder.mem_access(addr, WORD)
        builder.mc.MOV(eax, builder.stack_access(self.stackpos))
        builder.mc.MOV(dstop1, eax)
        builder.mc.MOV(eax, builder.stack_access(self.stackpos - 1))
        builder.mc.MOV(dstop2, eax)

    ll_type = lltype.Float
    token = 'f'
    SIZE = 2

LL_TO_GENVAR = {}
TOKEN_TO_GENVAR = {}
TOKEN_TO_SIZE = {}
for value in [IntVar, FloatVar, BoolVar, AddrVar]:
    assert hasattr(value, 'll_type')
    LL_TO_GENVAR[value.ll_type] = value.token
    TOKEN_TO_GENVAR[value.token] = value
    TOKEN_TO_SIZE[value.token] = value.SIZE
LL_TO_GENVAR[lltype.Unsigned] = 'i'
LL_TO_GENVAR[lltype.Char] = 'i'
# we might want to have different value for chare
# but I see no point now
LL_TO_GENVAR[lltype.Void] = 'v'

UNROLLING_TOKEN_TO_GENVAR = unrolling_iterable(TOKEN_TO_GENVAR.items())

def token_to_genvar(i, arg):
    for tok, value in UNROLLING_TOKEN_TO_GENVAR:
        if tok == i:
            return value(arg)

##class Const(GenConst):

##    def revealconst(self, TYPE):
##        if isinstance(self, IntConst):
##            self.revealconst_int(TYPE)
##        elif isinstance(self, PtrConst):
##            self.revealconst_ptr(TYPE)
        
##        if isinstance(TYPE, lltype.Ptr):
##            if isinstance(self, PtrConst):
##                return self.revealconst_ptr(TYPE)
##            el
##                return self.revealconst_ptr(TYPE)
##        elif TYPE is lltype.Float:
##            assert isinstance(self, DoubleConst)
##            return self.revealconst_double()
##        else:
##            assert isinstance(TYPE, lltype.Primitive)
##            assert TYPE is not lltype.Void, "cannot make red boxes of voids"
##            assert isinstance(self, IntConst)
##            return self.revealconst_primitive(TYPE)
##        return self.value
##    revealconst._annspecialcase_ = 'specialize:arg(1)'


class Const(GenConst):

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

    def movetonewaddr(self, builder, addr):
        raise NotImplementedError

    def repr(self):
        return "const=$%s" % (self.value,)

class IntConst(Const):
    SIZE = 1
    
    def newvar(self, builder):
        return builder.returnintvar(self.operand(builder))

    def movetonewaddr(self, builder, addr):
        dstop = builder.mem_access(addr)
        builder.mc.MOV(dstop, self.operand(builder))

class FloatConst(Const):
    SIZE = 2
    # XXX hack for annotator
    rawbuf = lltype.nullptr(rffi.DOUBLEP.TO)
    
    def __init__(self, floatval):
        # XXX we should take more care who is creating this and
        #     eventually release this buffer
        # never moves and never dies
        self.rawbuf = lltype.malloc(rffi.DOUBLEP.TO, 1, flavor='raw')
        self.rawbuf[0] = floatval

    def newvar(self, builder):
        return builder.newfloatfrommem((None, None, 0,
            rffi.cast(rffi.INT, self.rawbuf)))

    def operand(self, builder):
        return heap64(rffi.cast(rffi.INT, self.rawbuf))

    def movetonewaddr(self, builder, addr):
        dstop1 = builder.mem_access(addr)
        dstop2 = builder.mem_access(addr, WORD)
        builder.mc.MOV(dstop1, imm(rffi.cast(rffi.INTP, self.rawbuf)[0]))
        builder.mc.MOV(dstop2, imm(rffi.cast(rffi.INTP, self.rawbuf)[1]))

    def repr(self):
        return "const=$%s" % (self.rawbuf[0],)

    __repr__ = repr

class BoolConst(Const):
    SIZE = 1

    def operand(self, builder):
        return imm8(self.value)

    def newvar(self, builder):
        return builder.returnboolvar(self.operand(builder))

    def movetonewaddr(self, builder, addr):
        dstop = builder.mem_access(addr)
        builder.mc.MOV(dstop, self.operand(builder))

##class FnPtrConst(IntConst):
##    def __init__(self, value, mc):
##        self.value = value
##        self.mc = mc    # to keep it alive


class AddrConst(IntConst):
    SIZE = 1

    def __init__(self, addr):
        self.addr = addr

    def operand(self, builder):
        return imm(llmemory.cast_adr_to_int(self.addr))

    def newvar(self, builder):
        return builder.returnintvar(self.operand(builder))

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
