from pypy.rlib.rarithmetic import intmask
from pypy.rlib.unroll import unrolling_iterable
from pypy.jit.timeshifter import rtimeshift, rcontainer
from pypy.jit.timeshifter.greenkey import empty_key, GreenKey
from pypy.rpython.lltypesystem import lltype

class JitCode(object):
    """
    normal operations have the following format:
    2 byte - operation
    n * 2 byte - arguments
    
    for nonvoid results the result is appended to the varlist

    red vars are just indexes
    green vars are positive indexes
    green consts are negative indexes
    """

    def __init__(self, name, code, constants, typekinds, redboxclasses,
                 keydescs, structtypedescs, fielddescs, arrayfielddescs,
                 interiordescs, called_bytecodes, num_mergepoints, graph_color,
                 nonrainbow_functions, is_portal):
        self.name = name
        self.code = code
        self.constants = constants
        self.typekinds = typekinds
        self.redboxclasses = redboxclasses
        self.keydescs = keydescs
        self.structtypedescs = structtypedescs
        self.fielddescs = fielddescs
        self.arrayfielddescs = arrayfielddescs
        self.interiordescs = interiordescs
        self.called_bytecodes = called_bytecodes
        self.num_mergepoints = num_mergepoints
        self.graph_color = graph_color
        self.nonrainbow_functions = nonrainbow_functions
        self.is_portal = is_portal

    def _freeze_(self):
        return True

SIGN_EXTEND2 = 1 << 15

class STOP(object):
    pass
STOP = STOP()

class JitInterpreter(object):
    def __init__(self, exceptiondesc):
        self.exceptiondesc = exceptiondesc
        self.opcode_implementations = []
        self.opcode_descs = []
        self.opname_to_index = {}
        self.jitstate = None
        self.queue = None
        self._add_implemented_opcodes()

    def run(self, jitstate, bytecode, greenargs, redargs,
            start_bytecode_loop=True):
        self.jitstate = jitstate
        self.queue = rtimeshift.DispatchQueue(bytecode.num_mergepoints)
        rtimeshift.enter_frame(self.jitstate, self.queue)
        self.frame = self.jitstate.frame
        self.frame.pc = 0
        self.frame.bytecode = bytecode
        self.frame.local_boxes = redargs
        self.frame.local_green = greenargs
        if start_bytecode_loop:
            self.bytecode_loop()
        return self.jitstate

    def bytecode_loop(self):
        while 1:
            bytecode = self.load_2byte()
            assert bytecode >= 0
            result = self.opcode_implementations[bytecode](self)
            if result is STOP:
                return
            else:
                assert result is None

    def dispatch(self):
        is_portal = self.frame.bytecode.is_portal
        graph_color = self.frame.bytecode.graph_color
        queue = self.queue
        newjitstate = rtimeshift.dispatch_next(queue)
        resumepoint = rtimeshift.getresumepoint(newjitstate)
        self.newjitstate(newjitstate)
        if resumepoint == -1:
            if graph_color == "red":
                newjitstate = rtimeshift.leave_graph_red(
                        queue, is_portal)
            elif graph_color == "yellow":
                newjitstate = rtimeshift.leave_graph_yellow(queue)
            elif graph_color == "green":
                assert 0, "green graphs shouldn't be seen by the rainbow interp"
            elif graph_color == "gray":
                assert not is_portal
                newjitstate = rtimeshift.leave_graph_gray(queue)
            else:
                assert 0, "unknown graph color %s" % (graph_color, )

            self.newjitstate(newjitstate)
            if self.frame is None:
                return STOP
        else:
            self.frame.pc = resumepoint

    # operation helper functions
    def load_byte(self):
        pc = self.frame.pc
        assert pc >= 0
        result = ord(self.frame.bytecode.code[pc])
        self.frame.pc = pc + 1
        return result

    def load_2byte(self):
        pc = self.frame.pc
        assert pc >= 0
        result = ((ord(self.frame.bytecode.code[pc]) << 8) |
                   ord(self.frame.bytecode.code[pc + 1]))
        self.frame.pc = pc + 2
        return intmask((result ^ SIGN_EXTEND2) - SIGN_EXTEND2)

    def load_4byte(self):
        pc = self.frame.pc
        assert pc >= 0
        result = ((ord(self.frame.bytecode.code[pc + 0]) << 24) |
                  (ord(self.frame.bytecode.code[pc + 1]) << 16) |
                  (ord(self.frame.bytecode.code[pc + 2]) <<  8) |
                  (ord(self.frame.bytecode.code[pc + 3]) <<  0))
        self.frame.pc = pc + 4
        return intmask(result)

    def load_bool(self):
        return bool(self.load_byte())

    def get_greenarg(self):
        i = self.load_2byte()
        if i < 0:
            return self.frame.bytecode.constants[~i]
        return self.frame.local_green[i]

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
        return self.frame.local_boxes[self.load_2byte()]

    def red_result(self, box):
        self.frame.local_boxes.append(box)

    def green_result(self, gv):
        self.frame.local_green.append(gv)

    def newjitstate(self, newjitstate):
        self.jitstate = newjitstate
        self.queue = None
        if newjitstate is not None:
            frame = newjitstate.frame
            self.frame = frame
            if frame is not None:
                self.queue = frame.dispatchqueue
        else:
            self.frame = None

    # operation implementations
    def opimpl_make_redbox(self):
        genconst = self.get_greenarg()
        typeindex = self.load_2byte()
        kind = self.frame.bytecode.typekinds[typeindex]
        redboxcls = self.frame.bytecode.redboxclasses[typeindex]
        self.red_result(redboxcls(kind, genconst))

    def opimpl_goto(self):
        target = self.load_4byte()
        self.frame.pc = target

    def opimpl_green_goto_iftrue(self):
        genconst = self.get_greenarg()
        target = self.load_4byte()
        arg = genconst.revealconst(lltype.Bool)
        if arg:
            self.frame.pc = target

    def opimpl_red_goto_iftrue(self):
        switchbox = self.get_redarg()
        target = self.load_4byte()
        # XXX not sure about passing no green vars
        descision = rtimeshift.split(self.jitstate, switchbox, self.frame.pc)
        if descision:
            self.frame.pc = target

    def opimpl_red_goto_ifptrnonzero(self):
        reverse = self.load_bool()
        ptrbox = self.get_redarg()
        switchbox = self.get_redarg()
        target = self.load_4byte()
        # XXX not sure about passing no green vars
        descision = rtimeshift.split_ptr_nonzero(self.jitstate, switchbox,
                                                 self.frame.pc, ptrbox, reverse)
        if descision:
            self.frame.pc = target

    def opimpl_red_ptr_nonzero(self, reverse=False):
        ptrbox = self.get_redarg()
        resultbox = rtimeshift.genptrnonzero(self.jitstate, ptrbox, reverse)
        self.red_result(resultbox)

    def opimpl_red_ptr_iszero(self):
        self.opimpl_red_ptr_nonzero(reverse=True)

    def opimpl_red_ptr_eq(self, reverse=False):
        ptrbox1 = self.get_redarg()
        ptrbox2 = self.get_redarg()
        resultbox = rtimeshift.genptreq(self.jitstate, ptrbox1,
                                        ptrbox2, reverse)
        self.red_result(resultbox)

    def opimpl_red_ptr_ne(self):
        self.opimpl_red_ptr_eq(reverse=True)

    def opimpl_red_return(self):
        rtimeshift.save_return(self.jitstate)
        return self.dispatch()

    def opimpl_gray_return(self):
        rtimeshift.save_return(self.jitstate)
        return self.dispatch()

    def opimpl_yellow_return(self):
        # save the greens to make the return value findable by collect_split
        rtimeshift.save_greens(self.jitstate, self.frame.local_green)
        rtimeshift.save_return(self.jitstate)
        return self.dispatch()

    def opimpl_make_new_redvars(self):
        self.frame.local_boxes = self.get_red_varargs()

    def opimpl_make_new_greenvars(self):
        # an opcode with a variable number of args
        # num_args arg_old_1 arg_new_1 ...
        num = self.load_2byte()
        if num == 0 and len(self.frame.local_green) == 0:
            # fast (very common) case
            return
        newgreens = []
        for i in range(num):
            newgreens.append(self.get_greenarg())
        self.frame.local_green = newgreens

    def opimpl_merge(self):
        mergepointnum = self.load_2byte()
        keydescnum = self.load_2byte()
        if keydescnum == -1:
            key = empty_key
        else:
            keydesc = self.frame.bytecode.keydescs[keydescnum]
            key = GreenKey(self.frame.local_green[:keydesc.nb_vals], keydesc)
        states_dic = self.queue.local_caches[mergepointnum]
        done = rtimeshift.retrieve_jitstate_for_merge(states_dic, self.jitstate,
                                                      key, None)
        if done:
            return self.dispatch()

    def opimpl_red_direct_call(self):
        greenargs = self.get_green_varargs()
        redargs = self.get_red_varargs()
        bytecodenum = self.load_2byte()
        targetbytecode = self.frame.bytecode.called_bytecodes[bytecodenum]
        self.run(self.jitstate, targetbytecode, greenargs, redargs,
                 start_bytecode_loop=False)
        # this frame will be resumed later in the next bytecode, which is
        # red_after_direct_call

    def opimpl_red_after_direct_call(self):
        newjitstate = rtimeshift.collect_split(
            self.jitstate, self.frame.pc,
            self.frame.local_green)
        assert newjitstate is self.jitstate

    def opimpl_green_direct_call(self):
        greenargs = self.get_green_varargs()
        redargs = self.get_red_varargs()
        index = self.load_2byte()
        function = self.frame.bytecode.nonrainbow_functions[index]
        function(self, greenargs, redargs)

    def opimpl_yellow_direct_call(self):
        greenargs = self.get_green_varargs()
        redargs = self.get_red_varargs()
        bytecodenum = self.load_2byte()
        targetbytecode = self.frame.bytecode.called_bytecodes[bytecodenum]
        self.run(self.jitstate, targetbytecode, greenargs, redargs,
                 start_bytecode_loop=False)
        # this frame will be resumed later in the next bytecode, which is
        # yellow_after_direct_call

    def opimpl_yellow_after_direct_call(self):
        newjitstate = rtimeshift.collect_split(
            self.jitstate, self.frame.pc,
            self.frame.local_green)
        assert newjitstate is self.jitstate

    def opimpl_yellow_retrieve_result(self):
        # XXX all this jitstate.greens business is a bit messy
        self.green_result(self.jitstate.greens[0])


    # exceptions

    def opimpl_read_exctype(self):
        XXX

    def opimpl_read_excvalue(self):
        XXX

    def opimpl_write_exctype(self):
        typebox = self.get_redarg()
        rtimeshift.setexctypebox(self.jitstate, typebox)

    def opimpl_write_excvalue(self):
        valuebox = self.get_redarg()
        rtimeshift.setexcvaluebox(self.jitstate, valuebox)

    # structs and arrays

    def opimpl_red_malloc(self):
        structtypedesc = self.frame.bytecode.structtypedescs[self.load_2byte()]
        redbox = rcontainer.create(self.jitstate, structtypedesc)
        self.red_result(redbox)

    def opimpl_red_malloc_varsize_struct(self):
        structtypedesc = self.frame.bytecode.structtypedescs[self.load_2byte()]
        sizebox = self.get_redarg()
        redbox = rcontainer.create_varsize(self.jitstate, structtypedesc,
                                           sizebox)
        self.red_result(redbox)

    def opimpl_red_malloc_varsize_array(self):
        arraytypedesc = self.frame.bytecode.arrayfielddescs[self.load_2byte()]
        sizebox = self.get_redarg()
        redbox = rtimeshift.genmalloc_varsize(self.jitstate, arraytypedesc,
                                              sizebox)
        self.red_result(redbox)

    def opimpl_red_getfield(self):
        structbox = self.get_redarg()
        fielddesc = self.frame.bytecode.fielddescs[self.load_2byte()]
        deepfrozen = self.load_bool()
        resbox = rtimeshift.gengetfield(self.jitstate, deepfrozen, fielddesc,
                                        structbox)
        self.red_result(resbox)

    def opimpl_red_setfield(self):
        destbox = self.get_redarg()
        fielddesc = self.frame.bytecode.fielddescs[self.load_2byte()]
        valuebox = self.get_redarg()
        resbox = rtimeshift.gensetfield(self.jitstate, fielddesc, destbox,
                valuebox)

    def opimpl_red_getarrayitem(self):
        arraybox = self.get_redarg()
        fielddesc = self.frame.bytecode.arrayfielddescs[self.load_2byte()]
        indexbox = self.get_redarg()
        deepfrozen = self.load_bool()
        resbox = rtimeshift.gengetarrayitem(self.jitstate, deepfrozen, fielddesc,
                                        arraybox, indexbox)
        self.red_result(resbox)

    def opimpl_red_setarrayitem(self):
        destbox = self.get_redarg()
        fielddesc = self.frame.bytecode.arrayfielddescs[self.load_2byte()]
        indexbox = self.get_redarg()
        valuebox = self.get_redarg()
        resbox = rtimeshift.gensetarrayitem(self.jitstate, fielddesc, destbox,
                indexbox, valuebox)

    def opimpl_red_getarraysize(self):
        arraybox = self.get_redarg()
        fielddesc = self.frame.bytecode.arrayfielddescs[self.load_2byte()]
        resbox = rtimeshift.gengetarraysize(self.jitstate, fielddesc, arraybox)
        self.red_result(resbox)

    # ____________________________________________________________
    # construction-time interface

    def _add_implemented_opcodes(self):
        for name in dir(self):
            if not name.startswith("opimpl_"):
                continue
            opname = name[len("opimpl_"):]
            self.opname_to_index[opname] = len(self.opcode_implementations)
            self.opcode_implementations.append(getattr(self, name).im_func)
            self.opcode_descs.append(None)

    def find_opcode(self, name):
        return self.opname_to_index.get(name, -1)

    def make_opcode_implementation(self, color, opdesc):
        numargs = unrolling_iterable(range(opdesc.nb_args))
        if color == "green":
            def implementation(self):
                args = (opdesc.RESULT, )
                for i in numargs:
                    genconst = self.get_greenarg()
                    arg = genconst.revealconst(opdesc.ARGS[i])
                    args += (arg, )
                rgenop = self.jitstate.curbuilder.rgenop
                result = rgenop.genconst(opdesc.llop(*args))
                self.green_result(result)
        elif color == "red":
            if opdesc.nb_args == 1:
                impl = rtimeshift.ll_gen1
            elif opdesc.nb_args == 2:
                impl = rtimeshift.ll_gen2
            else:
                XXX
            def implementation(self):
                args = (opdesc, self.jitstate, )
                for i in numargs:
                    args += (self.get_redarg(), )
                result = impl(*args)
                self.red_result(result)
        else:
            assert 0, "unknown color"
        implementation.func_name = "opimpl_%s_%s" % (color, opdesc.opname)
        opname = "%s_%s" % (color, opdesc.opname)
        index = self.opname_to_index[opname] = len(self.opcode_implementations)
        self.opcode_implementations.append(implementation)
        self.opcode_descs.append(opdesc)
        return index


