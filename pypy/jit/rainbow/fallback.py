from pypy.rlib.rarithmetic import intmask
from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.objectmodel import we_are_translated, CDefinedIntSymbolic
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.jit.timeshifter.greenkey import empty_key, GreenKey
from pypy.jit.rainbow.interpreter import SIGN_EXTEND2, arguments


class FallbackInterpreter(object):
    """
    The fallback interp takes an existing suspended jitstate and
    actual values for the live red vars, and interprets the jitcode
    normally until it reaches the 'jit_merge_point' or raises.
    """
    def __init__(self, interpreter, ContinueRunningNormally, exceptiondesc):
        self.interpreter = interpreter
        self.rgenop = interpreter.rgenop
        self.ContinueRunningNormally = ContinueRunningNormally
        self.exceptiondesc = exceptiondesc
        self.register_opcode_impls(interpreter)

    def run(self, fallback_point, framebase, pc):
        self.interpreter.debug_trace("fallback_interp")
        self.fbp = fallback_point
        self.framebase = framebase
        self.initialize_state(pc)
        self.bytecode_loop()

    def initialize_state(self, pc):
        jitstate = self.fbp.saved_jitstate
        incoming_gv = jitstate.get_locals_gv()
        self.gv_to_index = {}
        for i in range(len(incoming_gv)):
            self.gv_to_index[incoming_gv[i]] = i

        self.initialize_from_frame(jitstate.frame)
        self.pc = pc
        self.gv_exc_type  = self.getinitialboxgv(jitstate.exc_type_box)
        self.gv_exc_value = self.getinitialboxgv(jitstate.exc_value_box)
        self.seen_can_enter_jit = False

    def getinitialboxgv(self, box):
        assert box.genvar is not None, "XXX Virtuals support missing"
        gv = box.genvar
        if not gv.is_const:
            # fetch the value from the machine code stack
            gv = self.rgenop.genconst_from_frame_var(box.kind, self.framebase,
                                                     self.fbp.frameinfo,
                                                     self.gv_to_index[gv])
        return gv

    def initialize_from_frame(self, frame):
        # note that both local_green and local_red contain GenConsts
        self.current_source_jitframe = frame
        self.pc = frame.pc
        self.bytecode = frame.bytecode
        self.local_green = frame.local_green[:]
        self.local_red = []
        for box in frame.local_boxes:
            self.local_red.append(self.getinitialboxgv(box))

    def run_directly(self, greenargs, redargs, targetbytecode):
        assert not (greenargs and redargs)  # XXX for now
        calldesc = targetbytecode.owncalldesc
        try:
            gv_res = calldesc.perform_call(self.rgenop,
                                           targetbytecode.gv_ownfnptr,
                                           greenargs or redargs)
        except Exception, e:
            XXX
        return gv_res

    # ____________________________________________________________
    # XXX Lots of copy and paste from interp.py!

    def bytecode_loop(self):
        while 1:
            bytecode = self.load_2byte()
            assert bytecode >= 0
            result = self.opcode_implementations[bytecode](self)

    # operation helper functions
    def getjitcode(self):
        return self.bytecode

    def load_byte(self):
        pc = self.pc
        assert pc >= 0
        result = ord(self.bytecode.code[pc])
        self.pc = pc + 1
        return result

    def load_2byte(self):
        pc = self.pc
        assert pc >= 0
        result = ((ord(self.bytecode.code[pc]) << 8) |
                   ord(self.bytecode.code[pc + 1]))
        self.pc = pc + 2
        return intmask((result ^ SIGN_EXTEND2) - SIGN_EXTEND2)

    def load_4byte(self):
        pc = self.pc
        assert pc >= 0
        result = ((ord(self.bytecode.code[pc + 0]) << 24) |
                  (ord(self.bytecode.code[pc + 1]) << 16) |
                  (ord(self.bytecode.code[pc + 2]) <<  8) |
                  (ord(self.bytecode.code[pc + 3]) <<  0))
        self.pc = pc + 4
        return intmask(result)

    def load_bool(self):
        return bool(self.load_byte())

    def get_greenarg(self):
        i = self.load_2byte()
        if i < 0:
            return self.bytecode.constants[~i]
        return self.local_green[i]

    def get_green_varargs(self):
        greenargs = []
        num = self.load_2byte()
        for i in range(num):
            greenargs.append(self.get_greenarg())
        return greenargs

    def get_red_varargs(self):
        redargs = []
        num = self.load_2byte()
        for i in range(num):
            redargs.append(self.get_redarg())
        return redargs

    def get_redarg(self):
        return self.local_red[self.load_2byte()]

    def get_greenkey(self):
        keydescnum = self.load_2byte()
        if keydescnum == -1:
            return empty_key
        else:
            keydesc = self.bytecode.keydescs[keydescnum]
            return GreenKey(self.local_green[:keydesc.nb_vals], keydesc)

    def red_result(self, gv):
        assert gv.is_const
        self.local_red.append(gv)

    def green_result(self, gv):
        assert gv.is_const
        self.local_green.append(gv)

    def green_result_from_red(self, gv):
        self.green_result(gv)

    def trace(self):
        bytecode = self.bytecode
        msg = '*** fallback trace: in %s position %d ***' % (bytecode.name,
                                                             self.pc)
        print msg
        if bytecode.dump_copy is not None:
            print bytecode.dump_copy
        return msg

    # ____________________________________________________________
    # Operation implementations

    @arguments()
    def opimpl_trace(self):
        msg = self.trace()
        self.interpreter.debug_trace(msg)

    @arguments("green", "2byte", returns="red")
    def opimpl_make_redbox(self, genconst, typeid):
        return genconst

    @arguments("red", returns="green_from_red")
    def opimpl_revealconst(self, gv_value):
        return gv_value

    @arguments("jumptarget")
    def opimpl_goto(self, target):
        self.pc = target

    @arguments("green", "jumptarget")
    def opimpl_green_goto_iftrue(self, genconst, target):
        if genconst.revealconst(lltype.Bool):
            self.pc = target

    @arguments("green", "green_varargs", "jumptargets")
    def opimpl_green_switch(self, exitcase, cases, targets):
        xxx

    @arguments("bool", "red", "red", "jumptarget")
    def opimpl_red_goto_ifptrnonzero(self, reverse, gv_ptr, gv_switch, target):
        xxx

    @arguments("red", "jumptarget")
    def opimpl_goto_if_constant(self, gv_value, target):
        xxx


    @arguments("red", returns="red")
    def opimpl_red_ptr_nonzero(self, gv_ptr):
        addr = gv_ptr.revealconst(llmemory.Address)
        return self.rgenop.genconst(bool(addr))

    @arguments("red", returns="red")
    def opimpl_red_ptr_iszero(self, gv_ptr):
        addr = gv_ptr.revealconst(llmemory.Address)
        return self.rgenop.genconst(not addr)

    @arguments("red", "red", returns="red")
    def opimpl_red_ptr_eq(self, gv_ptr1, gv_ptr2):
        xxx

    @arguments("red", "red", returns="red")
    def opimpl_red_ptr_ne(self, gv_ptr1, gv_ptr2):
        xxx


    @arguments("red_varargs")
    def opimpl_make_new_redvars(self, local_red):
        self.local_red = local_red

    def opimpl_make_new_greenvars(self):
        # this uses a "green_varargs" argument, but we do the decoding
        # manually for the fast case
        num = self.load_2byte()
        if num == 0 and len(self.local_green) == 0:
            # fast (very common) case
            return
        newgreens = []
        for i in range(num):
            newgreens.append(self.get_greenarg())
        self.local_green = newgreens
    opimpl_make_new_greenvars.argspec = arguments("green_varargs")

    @arguments("green", "calldesc", "green_varargs")
    def opimpl_green_call(self, fnptr_gv, calldesc, greenargs):
        xxx

    @arguments("green_varargs", "red_varargs", "red", "indirectcalldesc")
    def opimpl_indirect_call_const(self, greenargs, redargs,
                                      gv_funcptr, callset):
        xxx

    @arguments("red", "calldesc", "bool", "bool", "red_varargs",
               "promotiondesc")
    def opimpl_red_residual_call(self, gv_func, calldesc, withexc, has_result,
                                 redargs, promotiondesc):
        xxx

    @arguments("metacalldesc", "red_varargs", returns="red")
    def opimpl_metacall(self, metafunc, redargs):
        xxx

    @arguments("green_varargs", "red_varargs", "bytecode")
    def opimpl_red_direct_call(self, greenargs, redargs, targetbytecode):
        gv_res = self.run_directly(greenargs, redargs, targetbytecode)
        if gv_res is not None:
            self.red_result(gv_res)

    # exceptions

    @arguments(returns="red")
    def opimpl_read_exctype(self):
        return self.gv_exc_type

    @arguments(returns="red")
    def opimpl_read_excvalue(self):
        return self.gv_exc_value

    @arguments("red")
    def opimpl_write_exctype(self, gv_type):
        self.gv_exc_type = gv_type

    @arguments("red")
    def opimpl_write_excvalue(self, gv_value):
        self.gv_exc_value = gv_value

    @arguments("red", "red")
    def opimpl_setexception(self, gv_type, gv_value):
        self.gv_exc_type  = gv_type
        self.gv_exc_value = gv_value

    # structs and arrays

    @arguments("structtypedesc", returns="red")
    def opimpl_red_malloc(self, structtypedesc):
        return structtypedesc.allocate(self.rgenop)

    @arguments("structtypedesc", "red", returns="red")
    def opimpl_red_malloc_varsize_struct(self, structtypedesc, gv_size):
        xxx

    @arguments("arraydesc", "red", returns="red")
    def opimpl_red_malloc_varsize_array(self, arraytypedesc, gv_size):
        xxx

    @arguments("red", "fielddesc", "bool", returns="red")
    def opimpl_red_getfield(self, gv_struct, fielddesc, deepfrozen):
        gv_res = fielddesc.getfield_if_non_null(self.rgenop, gv_struct)
        assert gv_res is not None, "segfault!"
        return gv_res

    @arguments("red", "fielddesc", "bool", returns="green_from_red")
    def opimpl_green_getfield(self, gv_struct, fielddesc, deepfrozen):
        xxx

    @arguments("red", "fielddesc", "red")
    def opimpl_red_setfield(self, gv_dest, fielddesc, gv_value):
        fielddesc.setfield(self.rgenop, gv_dest, gv_value)

    @arguments("red", "arraydesc", "red", "bool", returns="red")
    def opimpl_red_getarrayitem(self, gv_array, fielddesc, gv_index, deepfrozen):
        xxx

    @arguments("red", "arraydesc", "red", "red")
    def opimpl_red_setarrayitem(self, gv_dest, fielddesc, gv_index, gv_value):
        xxx

    @arguments("red", "arraydesc", returns="red")
    def opimpl_red_getarraysize(self, gv_array, fielddesc):
        xxx

    @arguments("red", "arraydesc", returns="green_from_red")
    def opimpl_green_getarraysize(self, gv_array, fielddesc):
        xxx

    @arguments("red", "interiordesc", "bool", "red_varargs", returns="red")
    def opimpl_red_getinteriorfield(self, gv_struct, interiordesc, deepfrozen,
                                    indexes_gv):
        xxx

    @arguments("red", "interiordesc", "bool", "red_varargs",
               returns="green_from_red")
    def opimpl_green_getinteriorfield(self, gv_struct, interiordesc, deepfrozen,
                                      indexes_gv):
        xxx

    @arguments("red", "interiordesc", "red_varargs", "red")
    def opimpl_red_setinteriorfield(self, gv_dest, interiordesc, indexes_gv,
                                    gv_value):
        xxx

    @arguments("red", "interiordesc", "red_varargs", returns="red")
    def opimpl_red_getinteriorarraysize(self, gv_array, interiordesc, indexes_gv):
        xxx

    @arguments("red", "interiordesc", "red_varargs", returns="green_from_red")
    def opimpl_green_getinteriorarraysize(self, gv_array, interiordesc,
                                          indexes_gv):
        xxx

    @arguments("red", "green", "green", returns="green")
    def opimpl_is_constant(self, arg, true, false):
        xxx

    # hotpath-specific operations

    @arguments("greenkey")
    def opimpl_jit_merge_point(self, key):
        raise self.ContinueRunningNormally(self.local_green + self.local_red,
                                           self.seen_can_enter_jit)

    @arguments()
    def opimpl_can_enter_jit(self):
        self.seen_can_enter_jit = True

    @arguments("red", "jumptarget")
    def opimpl_hp_red_goto_iftrue(self, gv_switch, target):
        if gv_switch.revealconst(lltype.Bool):
            self.pc = target

    @arguments("green_varargs", "red_varargs", "bytecode")
    def opimpl_hp_yellow_direct_call(self, greenargs, redargs, targetbytecode):
        gv_res = self.run_directly(greenargs, redargs, targetbytecode)
        self.green_result(gv_res)

    @arguments()
    def opimpl_hp_gray_return(self):
        assert self.current_source_jitframe.backframe is None   # XXX for now
        # at this point we should have an exception set in self.gv_exc_xxx
        # and we have to really raise it.  XXX non-translatable hack follows...
        from pypy.rpython.llinterp import LLException, type_name
        exceptiondesc = self.exceptiondesc
        lltype = self.gv_exc_type.revealconst(exceptiondesc.LL_EXC_TYPE)
        llvalue = self.gv_exc_value.revealconst(exceptiondesc.LL_EXC_VALUE)
        assert lltype and llvalue
        self.interpreter.debug_trace("fb_raise", type_name(lltype))
        raise LLException(lltype, llvalue)

    @arguments()
    def opimpl_hp_yellow_return(self):
        xxx

    # ____________________________________________________________
    # construction-time helpers

    def register_opcode_impls(self, interp):
        impl = [None] * len(interp.opcode_implementations)
        for opname, index in interp.opname_to_index.items():
            argspec = interp.opcode_implementations[index].argspec
            name = 'opimpl_' + opname
            if hasattr(self, name):
                fbopimpl = getattr(self, name).im_func
                assert fbopimpl.argspec == argspec
            else:
                opdesc = interp.opcode_descs[index]
                if opdesc is None:
                    raise Exception("no fallback interpreter support for %r" %
                                    (opname,))
                fbopimpl = self.get_opcode_implementation(name, argspec,
                                                          opdesc)
            impl[index] = fbopimpl
        self.opcode_implementations = impl

    def get_opcode_implementation(self, func_name, argspec, opdesc):
        numargs = unrolling_iterable(range(opdesc.nb_args))
        def implementation(self, *args_gv):
            args = (opdesc.RESULT, )
            for i in numargs:
                arg = args_gv[i].revealconst(opdesc.ARGS[i])
                args += (arg, )
            if not we_are_translated():
                if opdesc.opname == "int_is_true":
                    # special case for tests, as in llinterp.py
                    if type(args[1]) is CDefinedIntSymbolic:
                        args = (args[0], args[1].default)
            return self.rgenop.genconst(opdesc.llop(*args))
        implementation.func_name = func_name
        # the argspec may unwrap *args_gv from local_red or local_green
        # and put the result back into local_red or local_green
        return argspec(implementation)
