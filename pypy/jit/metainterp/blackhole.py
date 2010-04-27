from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.rarithmetic import intmask, LONG_BIT, r_uint
from pypy.rlib.objectmodel import we_are_translated
from pypy.tool.sourcetools import func_with_new_name
from pypy.rpython.lltypesystem import lltype, llmemory, rclass
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.llinterp import LLException
from pypy.jit.codewriter.flatten import SwitchDictDescr


def arguments(*argtypes, **kwds):
    resulttype = kwds.pop('returns', None)
    assert not kwds
    def decorate(function):
        function.argtypes = argtypes
        function.resulttype = resulttype
        return function
    return decorate

class LeaveFrame(Exception):
    pass

class MissingValue(object):
    "NOT_RPYTHON"

def signedord(c):
    value = ord(c)
    value = intmask(value << (LONG_BIT-8)) >> (LONG_BIT-8)
    return value


class BlackholeInterpBuilder(object):
    verbose = True

    def __init__(self, codewriter):
        self.cpu = codewriter.cpu
        self.setup_insns(codewriter.assembler.insns)
        self.setup_descrs(codewriter.assembler.descrs)
        self._freeze_()

    def _freeze_(self):
        self.blackholeinterps = []
        return False

    def setup_insns(self, insns):
        assert len(insns) <= 256, "too many instructions!"
        self._insns = [None] * len(insns)
        for key, value in insns.items():
            assert self._insns[value] is None
            self._insns[value] = key
        self.op_catch_exception = insns.get('catch_exception/L', -1)
        #
        all_funcs = []
        for key in self._insns:
            assert key.count('/') == 1, "bad key: %r" % (key,)
            name, argcodes = key.split('/')
            all_funcs.append(self._get_method(name, argcodes))
        all_funcs = unrolling_iterable(enumerate(all_funcs))
        #
        def dispatch_loop(self, code, position):
            while True:
                opcode = ord(code[position])
                position += 1
                for i, func in all_funcs:
                    if opcode == i:
                        position = func(self, code, position)
                        break
                else:
                    raise AssertionError("bad opcode")
        dispatch_loop._dont_inline_ = True
        self.dispatch_loop = dispatch_loop

    def setup_descrs(self, descrs):
        self.descrs = descrs

    def _get_method(self, name, argcodes):
        #
        def handler(self, code, position):
            args = ()
            next_argcode = 0
            for argtype in argtypes:
                if argtype == 'i' or argtype == 'r' or argtype == 'f':
                    # if argtype is 'i', then argcode can be 'i' or 'c';
                    # 'c' stands for a single signed byte that gives the
                    # value of a small constant.
                    argcode = argcodes[next_argcode]
                    next_argcode = next_argcode + 1
                    if argcode == 'i':
                        value = self.registers_i[ord(code[position])]
                    elif argcode == 'c':
                        value = signedord(code[position])
                    elif argcode == 'r':
                        value = self.registers_r[ord(code[position])]
                    elif argcode == 'f':
                        value = self.registers_f[ord(code[position])]
                    else:
                        raise AssertionError("bad argcode")
                    position += 1
                elif argtype == 'L':
                    # argcode should be 'L' too
                    assert argcodes[next_argcode] == 'L'
                    next_argcode = next_argcode + 1
                    value = ord(code[position]) | (ord(code[position+1])<<8)
                    position += 2
                elif argtype == 'I' or argtype == 'R' or argtype == 'F':
                    assert argcodes[next_argcode] == argtype
                    next_argcode = next_argcode + 1
                    length = ord(code[position])
                    position += 1
                    value = []
                    for i in range(length):
                        index = ord(code[position+i])
                        if   argtype == 'I': reg = self.registers_i[index]
                        elif argtype == 'R': reg = self.registers_r[index]
                        elif argtype == 'F': reg = self.registers_f[index]
                        value.append(reg)
                    position += length
                elif argtype == 'pc':
                    value = position
                elif argtype == 'd':
                    assert argcodes[next_argcode] == 'd'
                    next_argcode = next_argcode + 1
                    index = ord(code[position]) | (ord(code[position+1])<<8)
                    value = self.descrs[index]
                    position += 2
                else:
                    raise AssertionError("bad argtype: %r" % (argtype,))
                args += (value,)

            if verbose and not we_are_translated():
                print '\t', name, list(args),

            # call the method opimpl_xxx()
            try:
                result = unboundmethod(self, *args)
            except Exception, e:
                if verbose and not we_are_translated():
                    print '-> %s!' % (e.__class__.__name__,)
                if resulttype == 'i' or resulttype == 'r' or resulttype == 'f':
                    position += 1
                self.exception_pc = position
                raise

            if verbose and not we_are_translated():
                if result is None:
                    print
                else:
                    print '->', result

            if resulttype == 'i':
                # argcode should be 'i' too
                assert argcodes[next_argcode] == 'i'
                next_argcode = next_argcode + 1
                assert lltype.typeOf(result) == lltype.Signed
                self.registers_i[ord(code[position])] = result
                position += 1
            elif resulttype == 'r':
                # argcode should be 'r' too
                assert argcodes[next_argcode] == 'r'
                next_argcode = next_argcode + 1
                assert lltype.typeOf(result) == llmemory.GCREF
                self.registers_r[ord(code[position])] = result
                position += 1
            elif resulttype == 'f':
                # argcode should be 'f' too
                assert argcodes[next_argcode] == 'f'
                next_argcode = next_argcode + 1
                assert lltype.typeOf(result) == lltype.Float
                self.registers_f[ord(code[position])] = result
                position += 1
            elif resulttype == 'L':
                position = result
            else:
                assert resulttype is None
                assert result is None
            assert next_argcode == len(argcodes)
            return position
        #
        verbose = self.verbose
        unboundmethod = getattr(BlackholeInterpreter, 'opimpl_' + name)
        argtypes = unrolling_iterable(unboundmethod.argtypes)
        resulttype = unboundmethod.resulttype
        handler = func_with_new_name(handler, 'handler_' + name)
        return handler

    def acquire_interp(self):
        if len(self.blackholeinterps) > 0:
            return self.blackholeinterps.pop()
        else:
            return BlackholeInterpreter(self)

    def release_interp(self, interp):
        self.blackholeinterps.append(interp)


class BlackholeInterpreter(object):

    def __init__(self, builder):
        self.cpu                = builder.cpu
        self.dispatch_loop      = builder.dispatch_loop
        self.descrs             = builder.descrs
        self.op_catch_exception = builder.op_catch_exception
        #
        if we_are_translated():
            default_i = 0
            default_r = lltype.nullptr(llmemory.GCREF.TO)
            default_f = 0.0
        else:
            default_i = MissingValue()
            default_r = MissingValue()
            default_f = MissingValue()
        self.registers_i = [default_i] * 256
        self.registers_r = [default_r] * 256
        self.registers_f = [default_f] * 256

    def setarg_i(self, index, value):
        self.registers_i[index] = value

    def run(self, jitcode, position):
        self.copy_constants(self.registers_i, jitcode.constants_i)
        self.copy_constants(self.registers_r, jitcode.constants_r)
        self.copy_constants(self.registers_f, jitcode.constants_f)
        code = jitcode.code
        while True:
            try:
                self.dispatch_loop(self, code, position)
            except LeaveFrame:
                return
            #except JitException:
            #    ...
            except Exception, e:
                if not we_are_translated():
                    if not isinstance(e, LLException):
                        raise
                position = self.handle_exception_in_frame(e, code)

    def handle_exception_in_frame(self, e, code):
        # This frame raises an exception.  First try to see if
        # the exception is handled in the frame itself.
        position = self.exception_pc    # <-- just after the insn that raised
        opcode = ord(code[position])
        if opcode != self.op_catch_exception:
            raise e      # no 'catch_exception' insn follows: just reraise
        else:
            # else store the exception on 'self', and jump to the handler
            if not we_are_translated():     # get the lltyped exception
                e = e.args[1]               #   object out of the LLException
            self.exception_last_value = e
            target = ord(code[position+1]) | (ord(code[position+2])<<8)
            return target

    # XXX must be specialized
    # XXX the real performance impact of the following loop is unclear
    def copy_constants(self, registers, constants):
        """Copy jitcode.constants[0] to registers[255],
                jitcode.constants[1] to registers[254],
                jitcode.constants[2] to registers[253], etc."""
        i = len(constants) - 1
        while i >= 0:
            j = 255 - i
            assert j >= 0
            registers[j] = constants[i]
            i -= 1

    # ----------

    @arguments("i", "i", returns="i")
    def opimpl_int_add(self, a, b):
        return a + b

    @arguments("i", "i", returns="i")
    def opimpl_int_sub(self, a, b):
        return a - b

    @arguments("i", "i", returns="i")
    def opimpl_int_mul(self, a, b):
        return a * b

    @arguments("i", "i", returns="i")
    def opimpl_uint_floordiv(self, a, b):
        c = llop.uint_floordiv(lltype.Unsigned, r_uint(a), r_uint(b))
        return intmask(c)

    @arguments("i")
    def opimpl_int_return(self, a):
        self.result_i = a
        raise LeaveFrame

    @arguments("i", returns="i")
    def opimpl_int_copy(self, a):
        return a

    @arguments("r", returns="r")
    def opimpl_ref_copy(self, a):
        return a

    @arguments("f", returns="f")
    def opimpl_float_copy(self, a):
        return a

    opimpl_int_guard_value = opimpl_int_copy
    opimpl_ref_guard_value = opimpl_ref_copy
    opimpl_float_guard_value = opimpl_float_copy

    @arguments("L", "i", "i", "pc", returns="L")
    def opimpl_goto_if_not_int_lt(self, target, a, b, pc):
        if a < b:
            return pc
        else:
            return target

    @arguments("L", "i", "i", "pc", returns="L")
    def opimpl_goto_if_not_int_le(self, target, a, b, pc):
        if a <= b:
            return pc
        else:
            return target

    @arguments("L", "i", "i", "pc", returns="L")
    def opimpl_goto_if_not_int_eq(self, target, a, b, pc):
        if a == b:
            return pc
        else:
            return target

    @arguments("L", "i", "i", "pc", returns="L")
    def opimpl_goto_if_not_int_ne(self, target, a, b, pc):
        if a != b:
            return pc
        else:
            return target

    @arguments("L", "i", "i", "pc", returns="L")
    def opimpl_goto_if_not_int_gt(self, target, a, b, pc):
        if a > b:
            return pc
        else:
            return target

    @arguments("L", "i", "i", "pc", returns="L")
    def opimpl_goto_if_not_int_ge(self, target, a, b, pc):
        if a >= b:
            return pc
        else:
            return target

    @arguments("L", returns="L")
    def opimpl_goto(self, target):
        return target

    @arguments("i", "d", "pc", returns="L")
    def opimpl_switch(self, switchvalue, switchdict, pc):
        assert isinstance(switchdict, SwitchDictDescr)
        try:
            return switchdict.dict[switchvalue]
        except KeyError:
            return pc

    @arguments("L")
    def opimpl_catch_exception(self, target):
        """This is a no-op when run normally.  When an exception occurs
        and the instruction that raised is immediately followed by a
        catch_exception, then the code in handle_exception_in_frame()
        will capture the exception and jump to 'target'."""

    @arguments("i", "L", "pc", returns="L")
    def opimpl_goto_if_exception_mismatch(self, vtable, target, pc):
        adr = llmemory.cast_int_to_adr(vtable)
        bounding_class = llmemory.cast_adr_to_ptr(adr, rclass.CLASSTYPE)
        real_instance = self.exception_last_value
        assert real_instance
        if rclass.ll_issubclass(real_instance.typeptr, bounding_class):
            return pc
        else:
            return target

    @arguments(returns="i")
    def opimpl_last_exception(self):
        real_instance = self.exception_last_value
        assert real_instance
        adr = llmemory.cast_ptr_to_adr(real_instance.typeptr)
        return llmemory.cast_adr_to_int(adr)

    @arguments(returns="r")
    def opimpl_last_exc_value(self):
        real_instance = self.exception_last_value
        assert real_instance
        return lltype.cast_opaque_ptr(llmemory.GCREF, real_instance)

    @arguments()
    def opimpl_reraise(self):
        real_instance = self.exception_last_value
        assert real_instance
        raise real_instance

    # ----------
    # the following operations are directly implemented by the backend

    @arguments("i", "d", "R", returns="i")
    def opimpl_residual_call_r_i(self, func, calldescr, args_r):
        return self.cpu.bh_call_i(func, calldescr, None, args_r, None)
    @arguments("i", "d", "R", returns="r")
    def opimpl_residual_call_r_r(self, func, calldescr, args_r):
        return self.cpu.bh_call_r(func, calldescr, None, args_r, None)
    @arguments("i", "d", "R", returns="f")
    def opimpl_residual_call_r_f(self, func, calldescr, args_r):
        return self.cpu.bh_call_f(func, calldescr, None, args_r, None)
    @arguments("i", "d", "R", returns="v")
    def opimpl_residual_call_r_v(self, func, calldescr, args_r):
        return self.cpu.bh_call_v(func, calldescr, None, args_r, None)

    @arguments("i", "d", "I", "R", returns="i")
    def opimpl_residual_call_ir_i(self, func, calldescr, args_i, args_r):
        return self.cpu.bh_call_i(func, calldescr, args_i, args_r, None)
    @arguments("i", "d", "I", "R", returns="r")
    def opimpl_residual_call_ir_r(self, func, calldescr, args_i, args_r):
        return self.cpu.bh_call_r(func, calldescr, args_i, args_r, None)
    @arguments("i", "d", "I", "R", returns="f")
    def opimpl_residual_call_ir_f(self, func, calldescr, args_i, args_r):
        return self.cpu.bh_call_f(func, calldescr, args_i, args_r, None)
    @arguments("i", "d", "I", "R", returns="v")
    def opimpl_residual_call_ir_v(self, func, calldescr, args_i, args_r):
        return self.cpu.bh_call_v(func, calldescr, args_i, args_r, None)

    @arguments("i", "d", "I", "R", "F", returns="i")
    def opimpl_residual_call_irf_i(self, func, calldescr,args_i,args_r,args_f):
        return self.cpu.bh_call_i(func, calldescr, args_i, args_r, args_f)
    @arguments("i", "d", "I", "R", "F", returns="r")
    def opimpl_residual_call_irf_r(self, func, calldescr,args_i,args_r,args_f):
        return self.cpu.bh_call_r(func, calldescr, args_i, args_r, args_f)
    @arguments("i", "d", "I", "R", "F", returns="f")
    def opimpl_residual_call_irf_f(self, func, calldescr,args_i,args_r,args_f):
        return self.cpu.bh_call_f(func, calldescr, args_i, args_r, args_f)
    @arguments("i", "d", "I", "R", "F", returns="v")
    def opimpl_residual_call_irf_v(self, func, calldescr,args_i,args_r,args_f):
        return self.cpu.bh_call_v(func, calldescr, args_i, args_r, args_f)

    @arguments("d", "i", returns="r")
    def opimpl_new_array(self, arraydescr, length):
        return self.cpu.bh_new_array(arraydescr, length)
    @arguments("d", "r", "i", "r")
    def opimpl_setarrayitem_gc_r(self, arraydescr, array, index, newvalue):
        self.cpu.bh_setarrayitem_gc_r(arraydescr, array, index, newvalue)

    @arguments("r", "d", returns="i")
    def opimpl_getfield_gc_i(self, struct, fielddescr):
        return self.cpu.bh_getfield_gc_i(struct, fielddescr)
    @arguments("r", "d", returns="i")
    def opimpl_getfield_gc_c(self, struct, fielddescr):
        return self.cpu.bh_getfield_gc_c(struct, fielddescr)
    @arguments("r", "d", returns="i")
    def opimpl_getfield_gc_u(self, struct, fielddescr):
        return self.cpu.bh_getfield_gc_u(struct, fielddescr)
    @arguments("r", "d", returns="r")
    def opimpl_getfield_gc_r(self, struct, fielddescr):
        return self.cpu.bh_getfield_gc_r(struct, fielddescr)
    @arguments("r", "d", returns="f")
    def opimpl_getfield_gc_f(self, struct, fielddescr):
        return self.cpu.bh_getfield_gc_f(struct, fielddescr)

    opimpl_getfield_gc_i_pure = opimpl_getfield_gc_i
    opimpl_getfield_gc_c_pure = opimpl_getfield_gc_c
    opimpl_getfield_gc_u_pure = opimpl_getfield_gc_u
    opimpl_getfield_gc_r_pure = opimpl_getfield_gc_r
    opimpl_getfield_gc_f_pure = opimpl_getfield_gc_f

    @arguments("r", "d", returns="i")
    def opimpl_getfield_raw_i(self, struct, fielddescr):
        return self.cpu.bh_getfield_raw_i(struct, fielddescr)
    @arguments("r", "d", returns="i")
    def opimpl_getfield_raw_c(self, struct, fielddescr):
        return self.cpu.bh_getfield_raw_c(struct, fielddescr)
    @arguments("r", "d", returns="i")
    def opimpl_getfield_raw_u(self, struct, fielddescr):
        return self.cpu.bh_getfield_raw_u(struct, fielddescr)
    @arguments("r", "d", returns="r")
    def opimpl_getfield_raw_r(self, struct, fielddescr):
        return self.cpu.bh_getfield_raw_r(struct, fielddescr)
    @arguments("r", "d", returns="f")
    def opimpl_getfield_raw_f(self, struct, fielddescr):
        return self.cpu.bh_getfield_raw_f(struct, fielddescr)

    opimpl_getfield_raw_i_pure = opimpl_getfield_raw_i
    opimpl_getfield_raw_c_pure = opimpl_getfield_raw_c
    opimpl_getfield_raw_u_pure = opimpl_getfield_raw_u
    opimpl_getfield_raw_r_pure = opimpl_getfield_raw_r
    opimpl_getfield_raw_f_pure = opimpl_getfield_raw_f
