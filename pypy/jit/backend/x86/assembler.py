import sys
import ctypes
from pypy.jit.backend.x86 import symbolic
from pypy.jit.metainterp.history import Const, ConstInt, Box, MergePoint
from pypy.rpython.lltypesystem import lltype, rffi, ll2ctypes, rstr
from pypy.rpython.lltypesystem.rclass import OBJECT
from pypy.annotation import model as annmodel
from pypy.tool.uid import fixid
from pypy.jit.backend.x86.regalloc import (RegAlloc, FRAMESIZE, WORD, REGS,
                                      arg_pos, lower_byte, stack_pos, Perform)
from pypy.rlib.objectmodel import we_are_translated, specialize
from pypy.jit.backend.x86 import codebuf
from pypy.jit.backend.x86.support import gc_malloc_fnaddr
from pypy.jit.backend.x86.ri386 import *

# our calling convention - we pass three first args as edx, ecx and eax
# and the rest stays on stack

class Assembler386(object):
    MC_SIZE = 1024*1024     # 1MB, but assumed infinite for now

    def __init__(self, cpu):
        self.cpu = cpu
        self.verbose = False
        self.mc = None
        self.mc2 = None
        self.rtyper = cpu.rtyper
        self.malloc_func_addr = 0

    def make_sure_mc_exists(self):
        if self.mc is None:
            # we generate the loop body in 'mc'
            # 'mc2' is for guard recovery code
            self.mc = codebuf.MachineCodeBlock(self.MC_SIZE)
            self.mc2 = codebuf.MachineCodeBlock(self.MC_SIZE)
            self.generic_return_addr = self.assemble_generic_return()
            # the address of the function called by 'new': directly use
            # Boehm's GC_malloc function.
            self.malloc_func_addr = gc_malloc_fnaddr() 

    def assemble(self, operations, guard_op, verbose=False):
        self.verbose = verbose
        # the last operation can be 'jump', 'return' or 'guard_pause';
        # a 'jump' can either close a loop, or end a bridge to some
        # previously-compiled code.
        self.make_sure_mc_exists()
        op0 = operations[0]
        op0.position = self.mc.tell()
        self._regalloc = RegAlloc(operations, guard_op) # for debugging
        self.max_stack_depth = self._regalloc.current_stack_depth
        computed_ops = self._regalloc.computed_ops
        if guard_op is not None:
            new_rel_addr = self.mc.tell() - guard_op._jmp_from
            TP = rffi.CArrayPtr(lltype.Signed)
            ptr = rffi.cast(TP, guard_op._jmp_from - WORD)
            ptr[0] = new_rel_addr
            self.mc.redone(guard_op._jmp_from - WORD, guard_op._jmp_from)
        if self.verbose and not we_are_translated():
            import pprint
            print
            pprint.pprint(operations)
            print
            pprint.pprint(computed_ops)
            print
        for i in range(len(computed_ops)):
            op = computed_ops[i]
            if not we_are_translated():
                self.dump_op(op)
            self.position = i
            if op.opname == 'load':
                self.regalloc_load(op)
            elif op.opname == 'store':
                self.regalloc_store(op)
            elif op.opname == 'perform_discard':
                self.regalloc_perform_discard(op)
            elif op.opname == 'perform':
                self.regalloc_perform(op)
        if not we_are_translated():
            self.dump_op('')
        self.mc.done()
        self.mc2.done()

    def assemble_bootstrap_code(self, arglocs):
        self.make_sure_mc_exists()
        addr = self.mc.tell()
        self.mc.SUB(esp, imm(FRAMESIZE))
        self.mc.MOV(eax, arg_pos(1))
        for i in range(len(arglocs)):
            loc = arglocs[i]
            if not isinstance(loc, REG):
                self.mc.MOV(ecx, mem(eax, i * WORD))
                self.mc.MOV(loc, ecx)
        for i in range(len(arglocs)):
            loc = arglocs[i]
            if isinstance(loc, REG):
                self.mc.MOV(loc, mem(eax, i * WORD))
        self.mc.JMP(arg_pos(0))
        self.mc.done()
        return addr

    def dump_op(self, op):
        if not self.verbose:
            return
        _prev = Box._extended_display
        try:
            Box._extended_display = False
            print >> sys.stderr, ' 0x%x  %s' % (fixid(self.mc.tell()), op)
        finally:
            Box._extended_display = _prev

    def assemble_comeback_bootstrap(self, mp):
        entry_point_addr = self.mc2.tell()
        for i in range(len(mp.arglocs)):
            argloc = mp.arglocs[i]
            if isinstance(argloc, REG):
                self.mc2.MOV(argloc, stack_pos(mp.stacklocs[i]))
            elif not we_are_translated():
                # debug checks
                if not isinstance(argloc, (IMM8, IMM32)):
                    assert repr(argloc) == repr(stack_pos(mp.stacklocs[i]))
        self.mc2.JMP(rel32(mp.position))
        self.mc2.done()
        return entry_point_addr

    def assemble_generic_return(self):
        # generate a generic stub that just returns, taking the
        # return value from *esp (i.e. stack position 0).
        addr = self.mc.tell()
        self.mc.MOV(eax, mem(esp, 0))
        self.mc.ADD(esp, imm(FRAMESIZE))
        self.mc.RET()
        self.mc.done()
        return addr

    def copy_var_if_used(self, v, to_v):
        """ Gives new loc
        """
        loc = self.loc(v)
        if isinstance(loc, REG):
            if self.regalloc.used(v) > self.regalloc.position:
                newloc = self.regalloc.allocate_loc(v)
                self.regalloc.move(loc, newloc)
            self.regalloc.force_loc(to_v, loc)
        else:
            newloc = self.regalloc.allocate_loc(to_v, force_reg=True)
            self.mc.MOV(newloc, loc)
            loc = newloc
        return loc
            
    def next_stack_position(self):
        position = self.current_stack_depth
        self.current_stack_depth += 1
        return position

    def regalloc_load(self, op):
        self.mc.MOV(op.to_loc, op.from_loc)

    regalloc_store = regalloc_load

    def regalloc_perform(self, op):
        assert isinstance(op, Perform)
        resloc = op.result_loc
        genop_dict[op.op.opname](self, op.op, op.arglocs, resloc)

    def regalloc_perform_discard(self, op):
        genop_discard_dict[op.op.opname](self, op.op, op.arglocs)

    def regalloc_store_to_arg(self, op):
        self.mc.MOV(arg_pos(op.pos), op.from_loc)

    def _unaryop(asmop):
        def genop_unary(self, op, arglocs, resloc):
            getattr(self.mc, asmop)(arglocs[0])
        return genop_unary

    def _binaryop(asmop, can_swap=False):
        def genop_binary(self, op, arglocs, result_loc):
            getattr(self.mc, asmop)(arglocs[0], arglocs[1])
        return genop_binary

    def _cmpop(cond):
        def genop_cmp(self, op, arglocs, result_loc):
            self.mc.CMP(arglocs[0], arglocs[1])
            self.mc.MOV(result_loc, imm8(0))
            getattr(self.mc, 'SET' + cond)(lower_byte(result_loc))
        return genop_cmp

    def call(self, addr, args, res):
        for arg in args:
            self.mc.PUSH(arg)
        self.mc.CALL(rel32(addr))
        self.mc.ADD(esp, imm(len(args) * WORD))
        assert res is eax

    genop_int_neg = _unaryop("NEG")
    genop_int_add = _binaryop("ADD", True)
    genop_int_sub = _binaryop("SUB")
    genop_int_mul = _binaryop("IMUL", True)
    genop_int_and = _binaryop("AND", True)

    genop_int_lt = _cmpop("L")
    genop_int_le = _cmpop("LE")
    genop_int_eq = _cmpop("E")
    genop_int_ne = _cmpop("NE")
    genop_int_gt = _cmpop("G")
    genop_int_ge = _cmpop("GE")

    # for now all chars are being considered ints, although we should make
    # a difference at some point
    genop_char_eq = genop_int_eq

    def genop_bool_not(self, op, arglocs, resloc):
        self.mc.XOR(arglocs[0], imm8(1))

    #def genop_int_lshift(self, op):
    #    self.load(eax, op.args[0])
    #    self.load(ecx, op.args[1])
    #    self.mc.SHL(eax, cl)
    #    self.mc.CMP(ecx, imm8(32))
    #    self.mc.SBB(ecx, ecx)
    #    self.mc.AND(eax, ecx)
    #    self.save(eax, op.results[0])

    def genop_int_rshift(self, op, arglocs, resloc):
        (x, y, tmp) = arglocs
        assert tmp is ecx
        yv = op.args[1]
        if isinstance(yv, ConstInt):
            intval = yv.value
            if intval < 0 or intval > 31:
                intval = 31
            self.mc.MOV(tmp, imm8(intval))
        else:
            self.mc.MOV(tmp, imm8(31)) 
            self.mc.CMP(y, tmp)
            self.mc.CMOVBE(tmp, y)
        self.mc.SAR(resloc, cl)

    def genop_int_is_true(self, op, arglocs, resloc):
        argloc = arglocs[0]
        self.mc.TEST(argloc, argloc)
        self.mc.MOV(resloc, imm8(0))
        self.mc.SETNZ(lower_byte(resloc))

    def genop_oononnull(self, op, arglocs, resloc):
        self.mc.CMP(arglocs[0], imm8(0))
        self.mc.MOV(resloc, imm8(0))
        self.mc.SETNE(lower_byte(resloc))

    def genop_ooisnull(self, op, arglocs, resloc):
        self.mc.CMP(arglocs[0], imm8(0))
        self.mc.MOV(resloc, imm8(0))
        self.mc.SETE(lower_byte(resloc))

    def genop_int_mod(self, op, arglocs, resloc):
        self.mc.CDQ()
        self.mc.IDIV(ecx)

    def genop_int_floordiv(self, op, arglocs, resloc):
        self.mc.CDQ()
        self.mc.IDIV(ecx)

    def genop_new_with_vtable(self, op, arglocs, result_loc):
        assert result_loc is eax
        loc_size, loc_vtable = arglocs
        self.mc.PUSH(loc_vtable)
        self.call(self.malloc_func_addr, [loc_size], eax)
        # xxx ignore NULL returns for now
        self.mc.POP(mem(eax, 0))

    def genop_new(self, op, arglocs, result_loc):
        assert result_loc is eax
        loc_size = arglocs[0]
        self.call(self.malloc_func_addr, [loc_size], eax)

    def genop_newstr(self, op, arglocs, result_loc):
        loc_size = arglocs[0]
        self.call(self.malloc_func_addr, [loc_size], eax)

    def genop_getfield_gc(self, op, arglocs, resloc):
        base_loc, ofs_loc = arglocs
        #if isinstance(op.args[0], Constant):
        #    x, _ = self.cpu.get_value_as_int(op.args[0].value)
        #    pos = mem(None, offset + x)
        #else:
        #    ...
        self.mc.MOV(resloc, addr_add(base_loc, ofs_loc))

    genop_getfield_raw = genop_getfield_gc

    def genop_setfield_gc(self, op, arglocs):
        base_loc, ofs_loc, value_loc = arglocs
        self.mc.MOV(addr_add(base_loc, ofs_loc), value_loc)

    def genop_strsetitem(self, op, arglocs):
        base_loc, ofs_loc, val_loc = arglocs
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR)
        self.mc.MOV(addr8_add(base_loc, ofs_loc, basesize),
                    lower_byte(val_loc))

    genop_setfield_raw = genop_setfield_gc

    def genop_strlen(self, op, arglocs, resloc):
        base_loc = arglocs[0]
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR)
        self.mc.MOV(resloc, addr_add_const(base_loc, ofs_length))

    def genop_strgetitem(self, op, arglocs, resloc):
        base_loc, ofs_loc = arglocs
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR)
        self.mc.MOVZX(resloc, addr8_add(base_loc, ofs_loc, basesize))

    def genop_merge_point(self, op, locs):
        # encode the current machine code position and the current stack
        # position of the live values into a flat array of c_long's.
        # XXX update comment
        # we load constants into arguments
        op.position = self.mc.tell()
        op.comeback_bootstrap_addr = self.assemble_comeback_bootstrap(op)
        #nb_args = len(op.args)
        #array_type = ctypes.c_long * (2 + nb_args)
        #label = array_type()
        #label[0] = nb_args
        #label[1] = self.mc.tell()
        #for i in range(nb_args):
        #    v = op.args[i]
        #    label[2 + i] = self.stack_positions[v]
        #op._asm_label = label

    genop_catch = genop_merge_point

    def genop_return(self, op, locs):
        if op.args:
            loc = locs[0]
            if loc is not eax:
                self.mc.MOV(eax, loc)
        self.mc.ADD(esp, imm(FRAMESIZE))
        self.mc.RET()

    def genop_jump(self, op, locs):
        targetmp = op.jump_target
        assert isinstance(targetmp, MergePoint)
        self.mc.JMP(rel32(targetmp.position))

    def genop_guard_true(self, op, locs):
        loc = locs[0]
        self.mc.TEST(loc, loc)
        self.implement_guard(op, self.mc.JZ, locs[1:])

    def genop_guard_no_exception(self, op, locs):
        pass # XXX # exception handling

    def genop_guard_false(self, op, locs):
        loc = locs[0]
        self.mc.TEST(loc, loc)
        self.implement_guard(op, self.mc.JNZ, locs[1:])

    genop_guard_nonzero = genop_guard_true
    genop_guard_iszero  = genop_guard_false
    genop_guard_nonnull = genop_guard_true
    genop_guard_isnull  = genop_guard_false

    def genop_guard_lt(self, op, locs):
        self.mc.CMP(locs[0], locs[1])
        self.implement_guard(op, self.mc.JGE, locs[2:])

    def genop_guard_le(self, op, locs):
        self.mc.CMP(locs[0], locs[1])
        self.implement_guard(op, self.mc.JG, locs[2:])

    def genop_guard_eq(self, op, locs):
        self.mc.CMP(locs[0], locs[1])
        self.implement_guard(op, self.mc.JNE, locs[2:])

    def genop_guard_ne(self, op, locs):
        self.mc.CMP(locs[0], locs[1])
        self.implement_guard(op, self.mc.JE, locs[2:])

    def genop_guard_gt(self, op, locs):
        self.mc.CMP(locs[0], locs[1])
        self.implement_guard(op, self.mc.JLE, locs[2:])

    def genop_guard_ge(self, op, locs):
        self.mc.CMP(locs[0], locs[1])
        self.implement_guard(op, self.mc.JL, locs[2:])

    genop_guard_is = genop_guard_eq
    genop_guard_isnot = genop_guard_ne

    def genop_guard_value(self, op, locs):
        arg0 = locs[0]
        arg1 = locs[1]
        self.mc.CMP(arg0, arg1)
        self.implement_guard(op, self.mc.JNE, locs[2:])

    def genop_guard_class(self, op, locs):
        offset = 0    # XXX for now, the vtable ptr is at the start of the obj
        self.mc.CMP(mem(locs[0], offset), locs[1])
        self.implement_guard(op, self.mc.JNE, locs[2:])

    def genop_guard_pause(self, op, locs):
        self.implement_guard(op, self.mc.JMP, locs)

    #def genop_guard_nonvirtualized(self, op):
    #    STRUCT = op.args[0].concretetype.TO
    #    offset, size = symbolic.get_field_token(STRUCT, 'vable_rti')
    #    assert size == WORD
    #    self.load(eax, op.args[0])
    #    self.mc.CMP(mem(eax, offset), imm(0))
    #    self.implement_guard(op, self.mc.JNE)

    @specialize.arg(2)
    def implement_guard(self, guard_op, emit_jump, locs):
        # XXX add caching, as we need only one for each combination
        # of locs
        recovery_addr = self.get_recovery_code(guard_op, locs)
        emit_jump(rel32(recovery_addr))
        guard_op._jmp_from = self.mc.tell()

    def get_recovery_code(self, guard_op, locs):
        index = self.cpu.make_guard_index(guard_op)
        recovery_code_addr = self.mc2.tell()
        stacklocs = guard_op.stacklocs
        assert len(locs) == len(stacklocs)
        for i in range(len(locs)):
            loc = locs[i]
            if isinstance(loc, REG):
                self.mc2.MOV(stack_pos(stacklocs[i]), loc)
        self.mc2.PUSH(esp)           # frame address
        self.mc2.PUSH(imm(index))    # index of guard that failed
        self.mc2.CALL(rel32(self.cpu.get_failure_recovery_func_addr()))
        self.mc2.ADD(esp, imm(8))
        self.mc2.JMP(eax)
        return recovery_code_addr

    def _new_gen_call():
        def gen_call(self, op, arglocs, resloc):
            extra_on_stack = 0
            for i in range(len(op.args) - 1, 0, -1):
                v = op.args[i]
                loc = arglocs[i]
                if not isinstance(loc, MODRM):
                    self.mc.PUSH(loc)
                else:
                    # we need to add a bit, ble
                    self.mc.PUSH(stack_pos(loc.position + extra_on_stack))
                extra_on_stack += 1
            if isinstance(op.args[0], Const):
                x = rel32(self.cpu.get_box_value_as_int(op.args[0]))
            else:
                # XXX add extra_on_stack?
                x = arglocs[0]
            self.mc.CALL(x)
            self.mc.ADD(esp, imm(WORD * extra_on_stack))
        return gen_call

    genop_call__4 = _new_gen_call()
    gen_call = _new_gen_call()
    genop_call_ptr = gen_call
    genop_getitem = _new_gen_call()

    def genop_call_void(self, op, arglocs):
        extra_on_stack = 0
        for i in range(len(op.args) - 1, 0, -1):
            v = op.args[i]
            loc = arglocs[i]
            if not isinstance(loc, MODRM):
                self.mc.PUSH(loc)
            else:
                # we need to add a bit, ble
                self.mc.PUSH(stack_pos(loc.position + extra_on_stack))
            extra_on_stack += 1
        if isinstance(op.args[0], Const):
            x = rel32(self.cpu.get_box_value_as_int(op.args[0]))
        else:
            # XXX add extra_on_stack?
            x = arglocs[0]
        self.mc.CALL(x)
        self.mc.ADD(esp, imm(WORD * extra_on_stack))        

    def genop_call__1(self, op, arglocs, resloc):
        self.gen_call(op, arglocs, resloc)
        self.mc.MOVZX(eax, al)

    def genop_call__2(self, op, arglocs, resloc):
        # XXX test it test it test it
        self.gen_call(op, arglocs, resloc)
        self.mc.MOVZX(eax, eax)

genop_discard_dict = {}
genop_dict = {}

for name, value in Assembler386.__dict__.iteritems():
    if name.startswith('genop_'):
        opname = name[len('genop_'):]
        if value.func_code.co_argcount == 3:
            genop_discard_dict[opname] = value
        else:
            genop_dict[opname] = value

genop_discard_dict['call_void'] = Assembler386.genop_call_void

def addr_add(reg_or_imm1, reg_or_imm2, offset=0):
    if isinstance(reg_or_imm1, IMM32):
        if isinstance(reg_or_imm2, IMM32):
            return heap(reg_or_imm1.value + offset + reg_or_imm2.value)
        else:
            return mem(reg_or_imm2, reg_or_imm1.value + offset)
    else:
        if isinstance(reg_or_imm2, IMM32):
            return mem(reg_or_imm1, offset + reg_or_imm2.value)
        else:
            return memSIB(reg_or_imm1, reg_or_imm2, 0, offset)

def addr8_add(reg_or_imm1, reg_or_imm2, offset=0):
    if isinstance(reg_or_imm1, IMM32):
        if isinstance(reg_or_imm2, IMM32):
            return heap8(reg_or_imm1.value + offset + reg_or_imm2.value)
        else:
            return mem8(reg_or_imm2, reg_or_imm1.value + offset)
    else:
        if isinstance(reg_or_imm2, IMM32):
            return mem8(reg_or_imm1, offset + reg_or_imm2.value)
        else:
            return memSIB8(reg_or_imm1, reg_or_imm2, 0, offset)

def addr_add_const(reg_or_imm1, offset):
    if isinstance(reg_or_imm1, IMM32):
        return heap(reg_or_imm1.value + offset)
    else:
        return mem(reg_or_imm1, offset)
