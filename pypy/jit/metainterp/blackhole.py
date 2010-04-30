from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.rarithmetic import intmask, LONG_BIT, r_uint, ovfcheck
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.debug import make_sure_not_resized
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

NULL = lltype.nullptr(llmemory.GCREF.TO)


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
            assert position >= 0
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
                        assert argtype == 'i'
                        value = self.registers_i[ord(code[position])]
                    elif argcode == 'c':
                        assert argtype == 'i'
                        value = signedord(code[position])
                    elif argcode == 'r':
                        assert argtype == 'r'
                        value = self.registers_r[ord(code[position])]
                    elif argcode == 'f':
                        assert argtype == 'f'
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
                    make_sure_not_resized(value)
                    position += length
                elif argtype == 'self':
                    value = self
                elif argtype == 'cpu':
                    value = self.cpu
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
                args = args + (value,)

            if verbose and not we_are_translated():
                print '\t', name, list(args),

            # call the method bhimpl_xxx()
            try:
                result = unboundmethod(*args)
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
                if lltype.typeOf(result) is lltype.Bool:
                    result = int(result)
                assert lltype.typeOf(result) is lltype.Signed
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
                assert lltype.typeOf(result) is lltype.Float
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
        # Get the bhimpl_xxx method.  If we get an AttributeError here,
        # it means that either the implementation is missing, or that it
        # should not appear here at all but instead be transformed away
        # by codewriter/jitter.py.
        unboundmethod = getattr(BlackholeInterpreter, 'bhimpl_' + name).im_func
        verbose = self.verbose
        argtypes = unrolling_iterable(unboundmethod.argtypes)
        resulttype = unboundmethod.resulttype
        handler.func_name = 'handler_' + name
        return handler

    def acquire_interp(self):
        if len(self.blackholeinterps) > 0:
            return self.blackholeinterps.pop()
        else:
            return BlackholeInterpreter(self)

    def release_interp(self, interp):
        interp.cleanup_registers_r()
        self.blackholeinterps.append(interp)


class BlackholeInterpreter(object):

    def __init__(self, builder):
        self.cpu                = builder.cpu
        self.dispatch_loop      = builder.dispatch_loop
        self.descrs             = builder.descrs
        self.op_catch_exception = builder.op_catch_exception
        self.cleanup_required_in_registers_r = 0
        #
        if we_are_translated():
            default_i = 0
            default_r = NULL
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

    def setarg_r(self, index, value):
        self.registers_r[index] = value

    def setarg_f(self, index, value):
        self.registers_f[index] = value

    def run(self, jitcode, position):
        self.copy_constants(self.registers_i, jitcode.constants_i)
        self.copy_constants(self.registers_r, jitcode.constants_r)
        self.copy_constants(self.registers_f, jitcode.constants_f)
        code = jitcode.code
        self.cleanup_required_in_registers_r = max(
            self.cleanup_required_in_registers_r,
            jitcode.num_regs_r())
        while True:
            try:
                self.dispatch_loop(self, code, position)
            except LeaveFrame:
                return
            #except JitException:
            #    ...
            except Exception, e:
                if not we_are_translated():
                    if isinstance(e, LLException):
                        pass    # ok
                    elif isinstance(e, OverflowError):
                        e = self.get_standard_error_exception(OverflowError)
                    else:
                        raise   # leave other exceptions be propagated
                position = self.handle_exception_in_frame(e, code)

    def get_result_i(self):
        return self.tmpreg_i

    def get_result_r(self):
        return self.tmpreg_r

    def get_result_f(self):
        return self.tmpreg_f

    def _get_result_anytype(self):
        "NOT_RPYTHON"
        if self._return_type == 'int': return self.get_result_i()
        if self._return_type == 'ref': return self.get_result_r()
        if self._return_type == 'float': return self.get_result_f()
        if self._return_type == 'void': return None
        raise ValueError(self._return_type)

    def cleanup_registers_r(self):
        # To avoid keeping references alive, this cleans up the registers_r.
        # It does not clear the references set by copy_constants(), but
        # these are all prebuilt constants anyway.
        for i in range(self.cleanup_required_in_registers_r):
            self.registers_r[i] = NULL
        self.cleanup_required_in_registers_r = 0
        self.tmpreg_r = NULL
        self.exception_last_value = None

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

    def get_standard_error_exception(self, Class):
        rtyper = self.cpu.rtyper
        exdata = rtyper.getexceptiondata()
        clsdef = rtyper.annotator.bookkeeper.getuniqueclassdef(Class)
        evalue = exdata.get_standard_ll_exc_instance(rtyper, clsdef)
        etype = rclass.ll_type(evalue)
        return LLException(etype, evalue)

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
    def bhimpl_int_add(a, b):
        return intmask(a + b)

    @arguments("i", "i", returns="i")
    def bhimpl_int_sub(a, b):
        return intmask(a - b)

    @arguments("i", "i", returns="i")
    def bhimpl_int_mul(a, b):
        return intmask(a * b)

    @arguments("i", "i", returns="i")
    def bhimpl_int_add_ovf(a, b):
        return ovfcheck(a + b)

    @arguments("i", "i", returns="i")
    def bhimpl_int_sub_ovf(a, b):
        return ovfcheck(a - b)

    @arguments("i", "i", returns="i")
    def bhimpl_int_mul_ovf(a, b):
        return ovfcheck(a * b)

    @arguments("i", "i", returns="i")
    def bhimpl_int_floordiv(a, b):
        return llop.int_floordiv(lltype.Signed, a, b)

    @arguments("i", "i", returns="i")
    def bhimpl_uint_floordiv(a, b):
        c = llop.uint_floordiv(lltype.Unsigned, r_uint(a), r_uint(b))
        return intmask(c)

    @arguments("i", "i", returns="i")
    def bhimpl_int_mod(a, b):
        return llop.int_mod(lltype.Signed, a, b)

    @arguments("i", "i", returns="i")
    def bhimpl_int_and(a, b):
        return a & b

    @arguments("i", "i", returns="i")
    def bhimpl_int_or(a, b):
        return a | b

    @arguments("i", "i", returns="i")
    def bhimpl_int_xor(a, b):
        return a ^ b

    @arguments("i", "i", returns="i")
    def bhimpl_int_rshift(a, b):
        return a >> b

    @arguments("i", "i", returns="i")
    def bhimpl_int_lshift(a, b):
        return intmask(a << b)

    @arguments("i", "i", returns="i")
    def bhimpl_uint_rshift(a, b):
        c = r_uint(a) >> r_uint(b)
        return intmask(c)

    @arguments("i", returns="i")
    def bhimpl_int_neg(a):
        return intmask(-a)

    @arguments("i", returns="i")
    def bhimpl_int_invert(a):
        return intmask(~a)

    @arguments("i", "i", returns="i")
    def bhimpl_int_lt(a, b):
        return a < b
    @arguments("i", "i", returns="i")
    def bhimpl_int_le(a, b):
        return a <= b
    @arguments("i", "i", returns="i")
    def bhimpl_int_eq(a, b):
        return a == b
    @arguments("i", "i", returns="i")
    def bhimpl_int_ne(a, b):
        return a != b
    @arguments("i", "i", returns="i")
    def bhimpl_int_gt(a, b):
        return a > b
    @arguments("i", "i", returns="i")
    def bhimpl_int_ge(a, b):
        return a >= b
    @arguments("i", returns="i")
    def bhimpl_int_is_zero(a):
        return not a
    @arguments("i", returns="i")
    def bhimpl_int_is_true(a):
        return bool(a)

    @arguments("i", "i", returns="i")
    def bhimpl_uint_lt(a, b):
        return r_uint(a) < r_uint(b)
    @arguments("i", "i", returns="i")
    def bhimpl_uint_le(a, b):
        return r_uint(a) <= r_uint(b)
    @arguments("i", "i", returns="i")
    def bhimpl_uint_gt(a, b):
        return r_uint(a) > r_uint(b)
    @arguments("i", "i", returns="i")
    def bhimpl_uint_ge(a, b):
        return r_uint(a) >= r_uint(b)

    @arguments("r", "r", returns="i")
    def bhimpl_ptr_eq(a, b):
        return a == b
    @arguments("r", "r", returns="i")
    def bhimpl_ptr_ne(a, b):
        return a != b
    @arguments("r", returns="i")
    def bhimpl_ptr_iszero(a):
        return not a
    @arguments("r", returns="i")
    def bhimpl_ptr_nonzero(a):
        return bool(a)

    @arguments("i", returns="i")
    def bhimpl_int_copy(a):
        return a
    @arguments("r", returns="r")
    def bhimpl_ref_copy(a):
        return a
    @arguments("f", returns="f")
    def bhimpl_float_copy(a):
        return a

    bhimpl_int_guard_value = bhimpl_int_copy
    bhimpl_ref_guard_value = bhimpl_ref_copy
    bhimpl_float_guard_value = bhimpl_float_copy

    @arguments("self", "i")
    def bhimpl_int_push(self, a):
        self.tmpreg_i = a
    @arguments("self", "r")
    def bhimpl_ref_push(self, a):
        self.tmpreg_r = a
    @arguments("self", "f")
    def bhimpl_float_push(self, a):
        self.tmpreg_f = a

    @arguments("self", returns="i")
    def bhimpl_int_pop(self):
        return self.tmpreg_i
    @arguments("self", returns="r")
    def bhimpl_ref_pop(self):
        return self.tmpreg_r
    @arguments("self", returns="f")
    def bhimpl_float_pop(self):
        return self.tmpreg_f

    # ----------
    # float operations

    @arguments("f", returns="f")
    def bhimpl_float_neg(a):
        return -a
    @arguments("f", returns="f")
    def bhimpl_float_abs(a):
        return abs(a)
    @arguments("f", returns="i")
    def bhimpl_float_is_true(a):
        return bool(a)

    @arguments("f", "f", returns="f")
    def bhimpl_float_add(a, b):
        return a + b
    @arguments("f", "f", returns="f")
    def bhimpl_float_sub(a, b):
        return a - b
    @arguments("f", "f", returns="f")
    def bhimpl_float_mul(a, b):
        return a * b
    @arguments("f", "f", returns="f")
    def bhimpl_float_truediv(a, b):
        return a / b

    @arguments("f", "f", returns="i")
    def bhimpl_float_lt(a, b):
        return a < b
    @arguments("f", "f", returns="i")
    def bhimpl_float_le(a, b):
        return a <= b
    @arguments("f", "f", returns="i")
    def bhimpl_float_eq(a, b):
        return a == b
    @arguments("f", "f", returns="i")
    def bhimpl_float_ne(a, b):
        return a != b
    @arguments("f", "f", returns="i")
    def bhimpl_float_gt(a, b):
        return a > b
    @arguments("f", "f", returns="i")
    def bhimpl_float_ge(a, b):
        return a >= b

    @arguments("f", returns="i")
    def bhimpl_cast_float_to_int(a):
        # note: we need to call int() twice to care for the fact that
        # int(-2147483648.0) returns a long :-(
        return int(int(a))

    @arguments("i", returns="f")
    def bhimpl_cast_int_to_float(a):
        return float(a)

    # ----------
    # control flow operations

    @arguments("self", "i")
    def bhimpl_int_return(self, a):
        self.tmpreg_i = a
        if not we_are_translated():
            self._return_type = "int"
        raise LeaveFrame

    @arguments("self", "r")
    def bhimpl_ref_return(self, a):
        self.tmpreg_r = a
        if not we_are_translated():
            self._return_type = "ref"
        raise LeaveFrame

    @arguments("self", "f")
    def bhimpl_float_return(self, a):
        self.tmpreg_f = a
        if not we_are_translated():
            self._return_type = "float"
        raise LeaveFrame

    @arguments("self")
    def bhimpl_void_return(self):
        if not we_are_translated():
            self._return_type = "void"
        raise LeaveFrame

    @arguments("L", "i", "pc", returns="L")
    def bhimpl_goto_if_not(target, a, pc):
        if a:
            return pc
        else:
            return target

    @arguments("L", "i", "i", "pc", returns="L")
    def bhimpl_goto_if_not_int_lt(target, a, b, pc):
        if a < b:
            return pc
        else:
            return target

    @arguments("L", "i", "i", "pc", returns="L")
    def bhimpl_goto_if_not_int_le(target, a, b, pc):
        if a <= b:
            return pc
        else:
            return target

    @arguments("L", "i", "i", "pc", returns="L")
    def bhimpl_goto_if_not_int_eq(target, a, b, pc):
        if a == b:
            return pc
        else:
            return target

    @arguments("L", "i", "i", "pc", returns="L")
    def bhimpl_goto_if_not_int_ne(target, a, b, pc):
        if a != b:
            return pc
        else:
            return target

    @arguments("L", "i", "i", "pc", returns="L")
    def bhimpl_goto_if_not_int_gt(target, a, b, pc):
        if a > b:
            return pc
        else:
            return target

    @arguments("L", "i", "i", "pc", returns="L")
    def bhimpl_goto_if_not_int_ge(target, a, b, pc):
        if a >= b:
            return pc
        else:
            return target

    @arguments("L", "i", "pc", returns="L")
    def bhimpl_goto_if_not_int_is_zero(target, a, pc):
        if not a:
            return pc
        else:
            return target

    @arguments("L", "r", "r", "pc", returns="L")
    def bhimpl_goto_if_not_ptr_eq(target, a, b, pc):
        if a == b:
            return pc
        else:
            return target

    @arguments("L", "r", "r", "pc", returns="L")
    def bhimpl_goto_if_not_ptr_ne(target, a, b, pc):
        if a != b:
            return pc
        else:
            return target

    @arguments("L", "r", "pc", returns="L")
    def bhimpl_goto_if_not_ptr_iszero(target, a, pc):
        if not a:
            return pc
        else:
            return target

    @arguments("L", "r", "pc", returns="L")
    def bhimpl_goto_if_not_ptr_nonzero(target, a, pc):
        if a:
            return pc
        else:
            return target

    @arguments("L", returns="L")
    def bhimpl_goto(target):
        return target

    @arguments("i", "d", "pc", returns="L")
    def bhimpl_switch(switchvalue, switchdict, pc):
        assert isinstance(switchdict, SwitchDictDescr)
        try:
            return switchdict.dict[switchvalue]
        except KeyError:
            return pc

    @arguments("L")
    def bhimpl_catch_exception(target):
        """This is a no-op when run normally.  When an exception occurs
        and the instruction that raised is immediately followed by a
        catch_exception, then the code in handle_exception_in_frame()
        will capture the exception and jump to 'target'."""

    @arguments("self", "i", "L", "pc", returns="L")
    def bhimpl_goto_if_exception_mismatch(self, vtable, target, pc):
        adr = llmemory.cast_int_to_adr(vtable)
        bounding_class = llmemory.cast_adr_to_ptr(adr, rclass.CLASSTYPE)
        real_instance = self.exception_last_value
        assert real_instance
        if rclass.ll_issubclass(real_instance.typeptr, bounding_class):
            return pc
        else:
            return target

    @arguments("self", returns="i")
    def bhimpl_last_exception(self):
        real_instance = self.exception_last_value
        assert real_instance
        adr = llmemory.cast_ptr_to_adr(real_instance.typeptr)
        return llmemory.cast_adr_to_int(adr)

    @arguments("self", returns="r")
    def bhimpl_last_exc_value(self):
        real_instance = self.exception_last_value
        assert real_instance
        return lltype.cast_opaque_ptr(llmemory.GCREF, real_instance)

    @arguments("self")
    def bhimpl_reraise(self):
        real_instance = self.exception_last_value
        assert real_instance
        raise real_instance

    # ----------
    # the following operations are directly implemented by the backend

    @arguments("cpu", "i", "d", "R", returns="i")
    def bhimpl_residual_call_r_i(cpu, func, calldescr, args_r):
        return cpu.bh_call_i(func, calldescr, None, args_r, None)
    @arguments("cpu", "i", "d", "R", returns="r")
    def bhimpl_residual_call_r_r(cpu, func, calldescr, args_r):
        return cpu.bh_call_r(func, calldescr, None, args_r, None)
    @arguments("cpu", "i", "d", "R", returns="f")
    def bhimpl_residual_call_r_f(cpu, func, calldescr, args_r):
        return cpu.bh_call_f(func, calldescr, None, args_r, None)
    @arguments("cpu", "i", "d", "R")
    def bhimpl_residual_call_r_v(cpu, func, calldescr, args_r):
        cpu.bh_call_v(func, calldescr, None, args_r, None)

    @arguments("cpu", "i", "d", "I", "R", returns="i")
    def bhimpl_residual_call_ir_i(cpu, func, calldescr, args_i, args_r):
        return cpu.bh_call_i(func, calldescr, args_i, args_r, None)
    @arguments("cpu", "i", "d", "I", "R", returns="r")
    def bhimpl_residual_call_ir_r(cpu, func, calldescr, args_i, args_r):
        return cpu.bh_call_r(func, calldescr, args_i, args_r, None)
    @arguments("cpu", "i", "d", "I", "R", returns="f")
    def bhimpl_residual_call_ir_f(cpu, func, calldescr, args_i, args_r):
        return cpu.bh_call_f(func, calldescr, args_i, args_r, None)
    @arguments("cpu", "i", "d", "I", "R")
    def bhimpl_residual_call_ir_v(cpu, func, calldescr, args_i, args_r):
        cpu.bh_call_v(func, calldescr, args_i, args_r, None)

    @arguments("cpu", "i", "d", "I", "R", "F", returns="i")
    def bhimpl_residual_call_irf_i(cpu, func, calldescr,args_i,args_r,args_f):
        return cpu.bh_call_i(func, calldescr, args_i, args_r, args_f)
    @arguments("cpu", "i", "d", "I", "R", "F", returns="r")
    def bhimpl_residual_call_irf_r(cpu, func, calldescr,args_i,args_r,args_f):
        return cpu.bh_call_r(func, calldescr, args_i, args_r, args_f)
    @arguments("cpu", "i", "d", "I", "R", "F", returns="f")
    def bhimpl_residual_call_irf_f(cpu, func, calldescr,args_i,args_r,args_f):
        return cpu.bh_call_f(func, calldescr, args_i, args_r, args_f)
    @arguments("cpu", "i", "d", "I", "R", "F")
    def bhimpl_residual_call_irf_v(cpu, func, calldescr,args_i,args_r,args_f):
        cpu.bh_call_v(func, calldescr, args_i, args_r, args_f)

    @arguments("cpu", "d", "i", returns="r")
    def bhimpl_new_array(cpu, arraydescr, length):
        return cpu.bh_new_array(arraydescr, length)
    @arguments("cpu", "d", "r", "i", "r")
    def bhimpl_setarrayitem_gc_r(cpu, arraydescr, array, index, newvalue):
        cpu.bh_setarrayitem_gc_r(arraydescr, array, index, newvalue)

    @arguments("cpu", "r", "d", returns="i")
    def bhimpl_getfield_gc_i(cpu, struct, fielddescr):
        return cpu.bh_getfield_gc_i(struct, fielddescr)
    @arguments("cpu", "r", "d", returns="i")
    def bhimpl_getfield_gc_c(cpu, struct, fielddescr):
        return cpu.bh_getfield_gc_c(struct, fielddescr)
    @arguments("cpu", "r", "d", returns="i")
    def bhimpl_getfield_gc_u(cpu, struct, fielddescr):
        return cpu.bh_getfield_gc_u(struct, fielddescr)
    @arguments("cpu", "r", "d", returns="r")
    def bhimpl_getfield_gc_r(cpu, struct, fielddescr):
        return cpu.bh_getfield_gc_r(struct, fielddescr)
    @arguments("cpu", "r", "d", returns="f")
    def bhimpl_getfield_gc_f(cpu, struct, fielddescr):
        return cpu.bh_getfield_gc_f(struct, fielddescr)

    bhimpl_getfield_gc_i_pure = bhimpl_getfield_gc_i
    bhimpl_getfield_gc_c_pure = bhimpl_getfield_gc_c
    bhimpl_getfield_gc_u_pure = bhimpl_getfield_gc_u
    bhimpl_getfield_gc_r_pure = bhimpl_getfield_gc_r
    bhimpl_getfield_gc_f_pure = bhimpl_getfield_gc_f

    @arguments("cpu", "i", "d", returns="i")
    def bhimpl_getfield_raw_i(cpu, struct, fielddescr):
        return cpu.bh_getfield_raw_i(struct, fielddescr)
    @arguments("cpu", "i", "d", returns="i")
    def bhimpl_getfield_raw_c(cpu, struct, fielddescr):
        return cpu.bh_getfield_raw_c(struct, fielddescr)
    @arguments("cpu", "i", "d", returns="i")
    def bhimpl_getfield_raw_u(cpu, struct, fielddescr):
        return cpu.bh_getfield_raw_u(struct, fielddescr)
    @arguments("cpu", "i", "d", returns="r")
    def bhimpl_getfield_raw_r(cpu, struct, fielddescr):
        return cpu.bh_getfield_raw_r(struct, fielddescr)
    @arguments("cpu", "i", "d", returns="f")
    def bhimpl_getfield_raw_f(cpu, struct, fielddescr):
        return cpu.bh_getfield_raw_f(struct, fielddescr)

    bhimpl_getfield_raw_i_pure = bhimpl_getfield_raw_i
    bhimpl_getfield_raw_c_pure = bhimpl_getfield_raw_c
    bhimpl_getfield_raw_u_pure = bhimpl_getfield_raw_u
    bhimpl_getfield_raw_r_pure = bhimpl_getfield_raw_r
    bhimpl_getfield_raw_f_pure = bhimpl_getfield_raw_f

    @arguments("cpu", "r", "d", "i")
    def bhimpl_setfield_gc_i(cpu, struct, fielddescr, newvalue):
        cpu.bh_setfield_gc_i(struct, fielddescr, newvalue)
    @arguments("cpu", "r", "d", "i")
    def bhimpl_setfield_gc_c(cpu, struct, fielddescr, newvalue):
        cpu.bh_setfield_gc_c(struct, fielddescr, newvalue)
    @arguments("cpu", "r", "d", "i")
    def bhimpl_setfield_gc_u(cpu, struct, fielddescr, newvalue):
        cpu.bh_setfield_gc_u(struct, fielddescr, newvalue)
    @arguments("cpu", "r", "d", "r")
    def bhimpl_setfield_gc_r(cpu, struct, fielddescr, newvalue):
        cpu.bh_setfield_gc_r(struct, fielddescr, newvalue)
    @arguments("cpu", "r", "d", "f")
    def bhimpl_setfield_gc_f(cpu, struct, fielddescr, newvalue):
        cpu.bh_setfield_gc_f(struct, fielddescr, newvalue)

    @arguments("cpu", "i", "d", "i")
    def bhimpl_setfield_raw_i(cpu, struct, fielddescr, newvalue):
        cpu.bh_setfield_raw_i(struct, fielddescr, newvalue)
    @arguments("cpu", "i", "d", "i")
    def bhimpl_setfield_raw_c(cpu, struct, fielddescr, newvalue):
        cpu.bh_setfield_raw_c(struct, fielddescr, newvalue)
    @arguments("cpu", "i", "d", "i")
    def bhimpl_setfield_raw_u(cpu, struct, fielddescr, newvalue):
        cpu.bh_setfield_raw_u(struct, fielddescr, newvalue)
    @arguments("cpu", "i", "d", "r")
    def bhimpl_setfield_raw_r(cpu, struct, fielddescr, newvalue):
        cpu.bh_setfield_raw_r(struct, fielddescr, newvalue)
    @arguments("cpu", "i", "d", "f")
    def bhimpl_setfield_raw_f(cpu, struct, fielddescr, newvalue):
        cpu.bh_setfield_raw_f(struct, fielddescr, newvalue)

    @arguments("cpu", "d", returns="r")
    def bhimpl_new(cpu, descr):
        return cpu.bh_new(descr)

    @arguments("cpu", "d", returns="r")
    def bhimpl_new_with_vtable(cpu, descr):
        return cpu.bh_new_with_vtable(descr)

    @arguments("cpu", "r", returns="i")
    def bhimpl_guard_class(cpu, struct):
        return cpu.bh_classof(struct)

    @arguments("cpu", "r", returns="i")
    def bhimpl_cast_ptr_to_int(cpu, p):
        return cpu.bh_cast_ptr_to_int(p)
