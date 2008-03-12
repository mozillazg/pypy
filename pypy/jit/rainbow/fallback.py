from pypy.rlib.rarithmetic import intmask
from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.objectmodel import we_are_translated, CDefinedIntSymbolic
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.jit.rainbow.interpreter import SIGN_EXTEND2, arguments


class SegfaultException(AssertionError):
    pass


class FallbackInterpreter(object):
    """
    The fallback interp takes an existing suspended jitstate and
    actual values for the live red vars, and interprets the jitcode
    normally until it reaches the 'jit_merge_point' or raises.
    """
    def __init__(self, ContinueRunningNormally):
        self.ContinueRunningNormally = ContinueRunningNormally

    def run(self, fallback_point, framebase, pc):
        self.fbp = fallback_point
        self.framebase = framebase
        self.initialize_state(pc)
        self.bytecode_loop()

    def initialize_state(self, pc):
        incoming_gv = self.fbp.saved_jitstate.get_locals_gv()
        self.gv_to_index = {}
        for i in range(len(incoming_gv)):
            self.gv_to_index[incoming_gv[i]] = i
        self.initialize_from_frame(self.fbp.saved_jitstate.frame)
        self.pc = pc

    def initialize_from_frame(self, frame):
        # note that both local_green and local_red contain GenConsts
        rgenop = self.rgenop
        self.pc = frame.pc
        self.bytecode = frame.bytecode
        self.local_green = frame.local_green[:]
        self.local_red = []
        for box in frame.local_boxes:
            assert box.genvar is not None, "XXX Virtuals support missing"
            gv = box.genvar
            if not gv.is_const:
                # fetch the value from the machine code stack
                gv = rgenop.genconst_from_frame_var(box.kind, self.framebase,
                                                    self.fbp.frameinfo,
                                                    self.gv_to_index[gv])
            self.local_red.append(gv)

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

    # ____________________________________________________________
    # Operation implementations

    @arguments()
    def opimpl_trace(self):
        bytecode = self.bytecode
        print '*** fallback trace: in %s position %d ***' % (bytecode.name,
                                                             self.pc)
        if bytecode.dump_copy is not None:
            print bytecode.dump_copy

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
        xxx

    @arguments("green", "green_varargs", "jumptargets")
    def opimpl_green_switch(self, exitcase, cases, targets):
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

    @arguments("red", returns="red")
    def opimpl_red_ptr_nonzero(self, gv_ptr):
        addr = gv_ptr.revealconst(llmemory.Address)
        return self.rgenop.genconst(bool(addr))

    @arguments("red", returns="red")
    def opimpl_red_ptr_iszero(self, gv_ptr):
        addr = gv_ptr.revealconst(llmemory.Address)
        return self.rgenop.genconst(not addr)

    @arguments()
    def opimpl_gray_return(self):
        xxx

    @arguments("green_varargs", "red_varargs", "bytecode")
    def opimpl_red_direct_call(self, greenargs, redargs, targetbytecode):
        xxx

    # exceptions

    @arguments(returns="red")
    def opimpl_read_exctype(self):
        xxx

    @arguments(returns="red")
    def opimpl_read_excvalue(self):
        xxx

    @arguments("red")
    def opimpl_write_exctype(self, typebox):
        xxx

    @arguments("red")
    def opimpl_write_excvalue(self, valuebox):
        xxx

    @arguments("red", "red")
    def opimpl_setexception(self, typebox, valuebox):
        xxx

    # structs and arrays

    @arguments("structtypedesc", returns="red")
    def opimpl_red_malloc(self, structtypedesc):
        xxx

    @arguments("red", "fielddesc", "bool", returns="red")
    def opimpl_red_getfield(self, gv_struct, fielddesc, deepfrozen):
        gv_res = fielddesc.getfield_if_non_null(self.rgenop, gv_struct)
        if gv_res is None:
            raise SegfaultException
        return gv_res

    @arguments("red", "fielddesc", "red")
    def opimpl_red_setfield(self, destbox, fielddesc, valuebox):
        xxx

    # hotpath-specific operations

    @arguments()
    def opimpl_jit_merge_point(self):
        raise self.ContinueRunningNormally(self.local_green + self.local_red)

    @arguments("red", "jumptarget")
    def opimpl_red_hot_goto_iftrue(self, gv_switch, target):
        if gv_switch.revealconst(lltype.Bool):
            self.pc = target

    # ____________________________________________________________
    # construction-time interface

    def register_opcode_impls(self, interp):
        self.rgenop = interp.rgenop
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
