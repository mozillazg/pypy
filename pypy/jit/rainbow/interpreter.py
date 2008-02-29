from pypy.rlib.rarithmetic import intmask
from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.objectmodel import we_are_translated, CDefinedIntSymbolic
from pypy.jit.timeshifter import rtimeshift, rcontainer
from pypy.jit.timeshifter.greenkey import empty_key, GreenKey, newgreendict
from pypy.rpython.lltypesystem import lltype, llmemory

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
    is_portal = False

    def __init__(self, name, code, constants, typekinds, redboxclasses,
                 keydescs, structtypedescs, fielddescs, arrayfielddescs,
                 interiordescs, oopspecdescs, promotiondescs,
                 called_bytecodes, num_mergepoints,
                 graph_color, calldescs, indirectcalldescs, is_portal):
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
        self.oopspecdescs = oopspecdescs
        self.promotiondescs = promotiondescs
        self.called_bytecodes = called_bytecodes
        self.num_mergepoints = num_mergepoints
        self.graph_color = graph_color
        self.calldescs = calldescs
        self.indirectcalldescs = indirectcalldescs
        self.is_portal = is_portal

    def _freeze_(self):
        return True

    def dump(self, file=None):
        from pypy.jit.rainbow import dump
        dump.dump_bytecode(self, file=file)

SIGN_EXTEND2 = 1 << 15

class STOP(object):
    pass
STOP = STOP()


class RainbowResumer(rtimeshift.Resumer):
    def __init__(self, interpreter, frame):
        self.interpreter = interpreter
        self.bytecode = frame.bytecode
        self.pc = frame.pc

    def resume(self, jitstate, resuming):
        interpreter = self.interpreter
        dispatchqueue = rtimeshift.DispatchQueue(self.bytecode.num_mergepoints)
        dispatchqueue.resuming = resuming
        jitstate.frame.dispatchqueue = dispatchqueue
        interpreter.newjitstate(jitstate)
        interpreter.frame.pc = self.pc
        interpreter.frame.bytecode = self.bytecode
        interpreter.frame.local_green = jitstate.greens[:]
        jitstate.frame.dispatchqueue = dispatchqueue
        interpreter.bytecode_loop()
        finaljitstate = interpreter.jitstate
        if finaljitstate is not None:
            interpreter.finish_jitstate(interpreter.portalstate.sigtoken)

def arguments(*argtypes, **kwargs):
    result = kwargs.pop("returns", None)
    assert not kwargs
    argtypes = unrolling_iterable(argtypes)
    def decorator(func):
        def wrapped(self):
            args = (self, )
            for argspec in argtypes:
                if argspec == "red":
                    args += (self.get_redarg(), )
                elif argspec == "green":
                    args += (self.get_greenarg(), )
                elif argspec == "kind":
                    args += (self.frame.bytecode.typekinds[self.load_2byte()], )
                elif argspec == "jumptarget":
                    args += (self.load_4byte(), )
                elif argspec == "bool":
                    args += (self.load_bool(), )
                elif argspec == "redboxcls":
                    args += (self.frame.bytecode.redboxclasses[self.load_2byte()], )
                elif argspec == "2byte":
                    args += (self.load_2byte(), )
                elif argspec == "greenkey":
                    args += (self.get_greenkey(), )
                elif argspec == "promotiondesc":
                    promotiondescnum = self.load_2byte()
                    promotiondesc = self.frame.bytecode.promotiondescs[promotiondescnum]
                    args += (promotiondesc, )
                elif argspec == "green_varargs":
                    args += (self.get_green_varargs(), )
                elif argspec == "red_varargs":
                    args += (self.get_red_varargs(), )
                elif argspec == "bytecode":
                    bytecodenum = self.load_2byte()
                    args += (self.frame.bytecode.called_bytecodes[bytecodenum], )
                elif argspec == "calldesc":
                    index = self.load_2byte()
                    function = self.frame.bytecode.calldescs[index]
                    args += (function, )
                elif argspec == "indirectcalldesc":
                    index = self.load_2byte()
                    function = self.frame.bytecode.indirectcalldescs[index]
                    args += (function, )
                elif argspec == "oopspec":
                    oopspecindex = self.load_2byte()
                    oopspec = self.frame.bytecode.oopspecdescs[oopspecindex]
                    args += (oopspec, )
                elif argspec == "structtypedesc":
                    td = self.frame.bytecode.structtypedescs[self.load_2byte()]
                    args += (td, )
                elif argspec == "arraydesc":
                    td = self.frame.bytecode.arrayfielddescs[self.load_2byte()]
                    args += (td, )
                elif argspec == "fielddesc":
                    d = self.frame.bytecode.fielddescs[self.load_2byte()]
                    args += (d, )
                elif argspec == "interiordesc":
                    d = self.frame.bytecode.interiordescs[self.load_2byte()]
                    args += (d, )
                else:
                    assert 0, "unknown argtype declaration"
            val = func(*args)
            if result is not None:
                if result == "red":
                    self.red_result(val)
                elif result == "green":
                    self.green_result(val)
                elif result == "green_from_red":
                    self.green_result_from_red(val)
                else:
                    assert 0, "unknown result declaration"
                return
            return val
        wrapped.func_name = "wrap_" + func.func_name
        wrapped.argspec = tuple(argtypes)
        wrapped.resultspec = result
        return wrapped
    return decorator


class JitInterpreter(object):
    def __init__(self, exceptiondesc, RGenOp):
        self.exceptiondesc = exceptiondesc
        self.opcode_implementations = []
        self.opcode_descs = []
        self.opname_to_index = {}
        self.jitstate = None
        self.queue = None
        self.rgenop = RGenOp()
        self.portalstate = None
        self.num_global_mergepoints = -1
        self.global_state_dicts = None
        self._add_implemented_opcodes()

    def set_portalstate(self, portalstate):
        assert self.portalstate is None
        self.portalstate = portalstate

    def set_num_global_mergepoints(self, num_global_mergepoints):
        assert self.num_global_mergepoints == -1
        self.num_global_mergepoints = num_global_mergepoints
        dicts = [newgreendict() for i in range(self.num_global_mergepoints)]
        self.global_state_dicts = dicts

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

    def resume(self, jitstate, greenargs, redargs):
        self.newjitstate(jitstate)
        self.frame.local_boxes = redargs
        self.frame.local_green = greenargs
        self.frame.gc = rtimeshift.getresumepoint(jitstate)
        self.bytecode_loop()
        return self.jitstate

    def fresh_jitstate(self, builder):
        return rtimeshift.JITState(builder, None,
                                   self.exceptiondesc.null_exc_type_box,
                                   self.exceptiondesc.null_exc_value_box)

    def finish_jitstate(self, graphsigtoken):
        jitstate = self.jitstate
        exceptiondesc = self.exceptiondesc
        returnbox = rtimeshift.getreturnbox(jitstate)
        gv_ret = returnbox.getgenvar(jitstate)
        builder = jitstate.curbuilder
        for virtualizable_box in jitstate.virtualizables:
            assert isinstance(virtualizable_box, rvalue.PtrRedBox)
            content = virtualizable_box.content
            assert isinstance(content, rcontainer.VirtualizableStruct)
            content.store_back(jitstate)        
        exceptiondesc.store_global_excdata(jitstate)
        jitstate.curbuilder.finish_and_return(graphsigtoken, gv_ret)

    def bytecode_loop(self):
        while 1:
            bytecode = self.load_2byte()
            assert bytecode >= 0
            result = self.opcode_implementations[bytecode](self)
            #assert (self.frame is None or not self.frame.local_boxes or
            #        self.frame.local_boxes[-1] is not None)
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

    def get_greenkey(self):
        keydescnum = self.load_2byte()
        if keydescnum == -1:
            return empty_key
        else:
            keydesc = self.frame.bytecode.keydescs[keydescnum]
            return GreenKey(self.frame.local_green[:keydesc.nb_vals], keydesc)

    def red_result(self, box):
        self.frame.local_boxes.append(box)

    def green_result(self, gv):
        assert gv.is_const
        self.frame.local_green.append(gv)

    def green_result_from_red(self, box):
        assert box.is_constant()
        self.green_result(box.getgenvar(self.jitstate))

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
    @arguments("green", "2byte", returns="red")
    def opimpl_make_redbox(self, genconst, typeid):
        redboxcls = self.frame.bytecode.redboxclasses[typeid]
        kind = self.frame.bytecode.typekinds[typeid]
        return redboxcls(kind, genconst)

    @arguments("jumptarget")
    def opimpl_goto(self, target):
        self.frame.pc = target

    @arguments("green", "jumptarget")
    def opimpl_green_goto_iftrue(self, genconst, target):
        arg = genconst.revealconst(lltype.Bool)
        if arg:
            self.frame.pc = target

    @arguments("red", "jumptarget")
    def opimpl_red_goto_iftrue(self, switchbox, target):
        # XXX not sure about passing no green vars
        descision = rtimeshift.split(self.jitstate, switchbox, self.frame.pc)
        if descision:
            self.frame.pc = target

    @arguments("bool", "red", "red", "jumptarget")
    def opimpl_red_goto_ifptrnonzero(self, reverse, ptrbox, switchbox, target):
        # XXX not sure about passing no green vars
        descision = rtimeshift.split_ptr_nonzero(self.jitstate, switchbox,
                                                 self.frame.pc, ptrbox, reverse)
        if descision:
            self.frame.pc = target

    @arguments("red", "jumptarget")
    def opimpl_goto_if_constant(self, valuebox, target):
        if valuebox.is_constant():
            self.frame.pc = target

    @arguments("jumptarget")
    def opimpl_goto_if_oopcall_was_virtual(self, target):
        if not rtimeshift.oopspec_was_residual(self.jitstate):
            self.frame.pc = target

    @arguments("red", returns="red")
    def opimpl_red_ptr_nonzero(self, ptrbox):
        return rtimeshift.genptrnonzero(self.jitstate, ptrbox, False)

    @arguments("red", returns="red")
    def opimpl_red_ptr_iszero(self, ptrbox):
        return rtimeshift.genptrnonzero(self.jitstate, ptrbox, True)

    @arguments("red", "red", returns="red")
    def opimpl_red_ptr_eq(self, ptrbox1, ptrbox2):
        return rtimeshift.genptreq(self.jitstate, ptrbox1,
                                   ptrbox2, False)

    @arguments("red", "red", returns="red")
    def opimpl_red_ptr_ne(self, ptrbox1, ptrbox2):
        return rtimeshift.genptreq(self.jitstate, ptrbox1,
                                   ptrbox2, True)

    @arguments("red", "bool")
    def opimpl_learn_nonzeroness(self, ptrbox, nonzero):
        rtimeshift.learn_nonzeroness(self.jitstate, ptrbox, nonzero)

    @arguments()
    def opimpl_red_return(self):
        rtimeshift.save_return(self.jitstate)
        return self.dispatch()

    @arguments()
    def opimpl_gray_return(self):
        rtimeshift.save_return(self.jitstate)
        return self.dispatch()

    @arguments()
    def opimpl_yellow_return(self):
        # save the greens to make the return value findable by collect_split
        rtimeshift.save_greens(self.jitstate, self.frame.local_green)
        rtimeshift.save_return(self.jitstate)
        return self.dispatch()

    @arguments("red_varargs")
    def opimpl_make_new_redvars(self, local_boxes):
        self.frame.local_boxes = local_boxes

    def opimpl_make_new_greenvars(self):
        # this uses a "green_varargs" argument, but we do the decoding
        # manually for the fast case
        num = self.load_2byte()
        if num == 0 and len(self.frame.local_green) == 0:
            # fast (very common) case
            return
        newgreens = []
        for i in range(num):
            newgreens.append(self.get_greenarg())
        self.frame.local_green = newgreens
    opimpl_make_new_greenvars.argspec = ("green_varargs",)  # for dump.py
    opimpl_make_new_greenvars.resultspec = None

    @arguments("2byte", "greenkey")
    def opimpl_local_merge(self, mergepointnum, key):
        states_dic = self.queue.local_caches[mergepointnum]
        done = rtimeshift.retrieve_jitstate_for_merge(states_dic, self.jitstate,
                                                      key, None)
        if done:
            return self.dispatch()

    @arguments("2byte", "greenkey")
    def opimpl_global_merge(self, mergepointnum, key):
        states_dic = self.global_state_dicts[mergepointnum]
        global_resumer = RainbowResumer(self, self.frame)
        done = rtimeshift.retrieve_jitstate_for_merge(states_dic, self.jitstate,
                                                      key, global_resumer)
        if done:
            return self.dispatch()

    @arguments()
    def opimpl_guard_global_merge(self):
        rtimeshift.save_greens(self.jitstate, self.frame.local_green)
        rtimeshift.guard_global_merge(self.jitstate, self.frame.pc)
        return self.dispatch()

    @arguments("red", "promotiondesc")
    def opimpl_promote(self, promotebox, promotiondesc):
        done = rtimeshift.promote(self.jitstate, promotebox, promotiondesc)
        if done:
            return self.dispatch()
        gv_switchvar = promotebox.getgenvar(self.jitstate)
        assert gv_switchvar.is_const
        self.green_result(gv_switchvar)

    @arguments()
    def opimpl_reverse_split_queue(self):
        rtimeshift.reverse_split_queue(self.frame.dispatchqueue)

    @arguments("green_varargs", "red_varargs", "bytecode")
    def opimpl_red_direct_call(self, greenargs, redargs, targetbytecode):
        self.run(self.jitstate, targetbytecode, greenargs, redargs,
                 start_bytecode_loop=False)
        # this frame will be resumed later in the next bytecode, which is
        # red_after_direct_call

    @arguments()
    def opimpl_red_after_direct_call(self):
        newjitstate = rtimeshift.collect_split(
            self.jitstate, self.frame.pc,
            self.frame.local_green)
        assert newjitstate is self.jitstate

    @arguments("green_varargs", "red_varargs")
    def opimpl_portal_call(self, greenargs, redargs):
        self.portalstate.portal_reentry(greenargs, redargs)

    @arguments("green", "calldesc", "green_varargs")
    def opimpl_green_direct_call(self, fnptr_gv, calldesc, greenargs):
        calldesc.green_call(self, fnptr_gv, greenargs)

    @arguments("green_varargs", "red_varargs", "bytecode")
    def opimpl_yellow_direct_call(self, greenargs, redargs, targetbytecode):
        self.run(self.jitstate, targetbytecode, greenargs, redargs,
                 start_bytecode_loop=False)
        # this frame will be resumed later in the next bytecode, which is
        # yellow_after_direct_call

    @arguments("green_varargs", "red_varargs", "red", "indirectcalldesc")
    def opimpl_indirect_call_const(self, greenargs, redargs,
                                      funcptrbox, callset):
        gv = funcptrbox.getgenvar(self.jitstate)
        addr = gv.revealconst(llmemory.Address)
        bytecode = callset.bytecode_for_address(addr)
        self.run(self.jitstate, bytecode, greenargs, redargs,
                 start_bytecode_loop=False)

    @arguments()
    def opimpl_yellow_after_direct_call(self):
        newjitstate = rtimeshift.collect_split(
            self.jitstate, self.frame.pc,
            self.frame.local_green)
        assert newjitstate is self.jitstate

    @arguments(returns="green")
    def opimpl_yellow_retrieve_result(self):
        # XXX all this jitstate.greens business is a bit messy
        return self.jitstate.greens[0]

    @arguments("2byte", returns="red")
    def opimpl_yellow_retrieve_result_as_red(self, typeid):
        # XXX all this jitstate.greens business is a bit messy
        redboxcls = self.frame.bytecode.redboxclasses[typeid]
        kind = self.frame.bytecode.typekinds[typeid]
        return redboxcls(kind, self.jitstate.greens[0])

    @arguments("oopspec", "bool", returns="red")
    def opimpl_red_oopspec_call_0(self, oopspec, deepfrozen):
        return oopspec.ll_handler_0(self.jitstate, oopspec, deepfrozen)

    @arguments("oopspec", "bool", "red", returns="red")
    def opimpl_red_oopspec_call_1(self, oopspec, deepfrozen, arg1):
        return oopspec.ll_handler_1(self.jitstate, oopspec, deepfrozen, arg1)

    @arguments("oopspec", "bool", "red", "red", returns="red")
    def opimpl_red_oopspec_call_2(self, oopspec, deepfrozen, arg1, arg2):
        return oopspec.ll_handler_2(self.jitstate, oopspec, deepfrozen, arg1, arg2)

    @arguments("oopspec", "bool", "red", "red", "red", returns="red")
    def opimpl_red_oopspec_call_3(self, oopspec, deepfrozen, arg1, arg2, arg3):
        return oopspec.ll_handler_3(self.jitstate, oopspec, deepfrozen, arg1, arg2, arg3)

    @arguments("oopspec", "bool")
    def opimpl_red_oopspec_call_noresult_0(self, oopspec, deepfrozen):
        oopspec.ll_handler_0(self.jitstate, oopspec, deepfrozen)

    @arguments("oopspec", "bool", "red")
    def opimpl_red_oopspec_call_noresult_1(self, oopspec, deepfrozen, arg1):
        oopspec.ll_handler_1(self.jitstate, oopspec, deepfrozen, arg1)

    @arguments("oopspec", "bool", "red", "red")
    def opimpl_red_oopspec_call_noresult_2(self, oopspec, deepfrozen, arg1, arg2):
        oopspec.ll_handler_2(self.jitstate, oopspec, deepfrozen, arg1, arg2)

    @arguments("oopspec", "bool", "red", "red", "red")
    def opimpl_red_oopspec_call_noresult_3(self, oopspec, deepfrozen, arg1, arg2, arg3):
        oopspec.ll_handler_3(self.jitstate, oopspec, deepfrozen, arg1, arg2, arg3)

    @arguments("promotiondesc")
    def opimpl_after_oop_residual_call(self, promotiondesc):
        exceptiondesc = self.exceptiondesc
        check_forced = False
        flagbox = rtimeshift.after_residual_call(self.jitstate,
                                                 exceptiondesc, check_forced)
        done = rtimeshift.promote(self.jitstate, flagbox, promotiondesc)
        if done:
            return self.dispatch()
        gv_flag = flagbox.getgenvar(self.jitstate)
        assert gv_flag.is_const
        rtimeshift.residual_fetch(self.jitstate, self.exceptiondesc,
                                  check_forced, flagbox)

    @arguments("red", "calldesc", "bool", "bool", "red_varargs",
               "promotiondesc")
    def opimpl_red_residual_call(self, funcbox, calldesc, withexc, has_result,
                                 redargs, promotiondesc):
        result = rtimeshift.gen_residual_call(self.jitstate, calldesc,
                                              funcbox, redargs)
        if has_result:
            self.red_result(result)
        if withexc:
            exceptiondesc = self.exceptiondesc
        else:
            exceptiondesc = None
        flagbox = rtimeshift.after_residual_call(self.jitstate,
                                                 exceptiondesc, True)
        done = rtimeshift.promote(self.jitstate, flagbox, promotiondesc)
        if done:
            return self.dispatch()
        gv_flag = flagbox.getgenvar(self.jitstate)
        assert gv_flag.is_const
        rtimeshift.residual_fetch(self.jitstate, self.exceptiondesc,
                                  True, flagbox)

    # exceptions

    @arguments(returns="red")
    def opimpl_read_exctype(self):
        return rtimeshift.getexctypebox(self.jitstate)

    @arguments(returns="red")
    def opimpl_read_excvalue(self):
        return rtimeshift.getexcvaluebox(self.jitstate)
        self.red_result(box)

    @arguments("red")
    def opimpl_write_exctype(self, typebox):
        rtimeshift.setexctypebox(self.jitstate, typebox)

    @arguments("red")
    def opimpl_write_excvalue(self, valuebox):
        rtimeshift.setexcvaluebox(self.jitstate, valuebox)

    @arguments("red", "red")
    def opimpl_setexception(self, typebox, valuebox):
        rtimeshift.setexception(self.jitstate, typebox, valuebox)

    # structs and arrays

    @arguments("structtypedesc", returns="red")
    def opimpl_red_malloc(self, structtypedesc):
        redbox = rcontainer.create(self.jitstate, structtypedesc)
        return redbox

    @arguments("structtypedesc", "red", returns="red")
    def opimpl_red_malloc_varsize_struct(self, structtypedesc, sizebox):
        redbox = rcontainer.create_varsize(self.jitstate, structtypedesc,
                                           sizebox)
        return redbox

    @arguments("arraydesc", "red", returns="red")
    def opimpl_red_malloc_varsize_array(self, arraytypedesc, sizebox):
        return rtimeshift.genmalloc_varsize(self.jitstate, arraytypedesc,
                                            sizebox)

    @arguments("red", "fielddesc", "bool", returns="red")
    def opimpl_red_getfield(self, structbox, fielddesc, deepfrozen):
        return rtimeshift.gengetfield(self.jitstate, deepfrozen, fielddesc,
                                      structbox)

    @arguments("red", "fielddesc", "bool", returns="green_from_red")
    def opimpl_green_getfield(self, structbox, fielddesc, deepfrozen):
        return rtimeshift.gengetfield(self.jitstate, deepfrozen, fielddesc,
                                      structbox)

    @arguments("red", "fielddesc", "red")
    def opimpl_red_setfield(self, destbox, fielddesc, valuebox):
        rtimeshift.gensetfield(self.jitstate, fielddesc, destbox,
                               valuebox)

    @arguments("red", "arraydesc", "red", "bool", returns="red")
    def opimpl_red_getarrayitem(self, arraybox, fielddesc, indexbox, deepfrozen):
        return rtimeshift.gengetarrayitem(self.jitstate, deepfrozen, fielddesc,
                                          arraybox, indexbox)

    @arguments("red", "arraydesc", "red", "red")
    def opimpl_red_setarrayitem(self, destbox, fielddesc, indexbox, valuebox):
        rtimeshift.gensetarrayitem(self.jitstate, fielddesc, destbox,
                                   indexbox, valuebox)

    @arguments("red", "arraydesc", returns="red")
    def opimpl_red_getarraysize(self, arraybox, fielddesc):
        return rtimeshift.gengetarraysize(self.jitstate, fielddesc, arraybox)

    @arguments("red", "arraydesc", returns="green_from_red")
    def opimpl_green_getarraysize(self, arraybox, fielddesc):
        return rtimeshift.gengetarraysize(self.jitstate, fielddesc, arraybox)

    @arguments("red", "interiordesc", "bool", "red_varargs", returns="red")
    def opimpl_red_getinteriorfield(self, structbox, interiordesc, deepfrozen,
                                    indexboxes):
        return interiordesc.gengetinteriorfield(self.jitstate, deepfrozen,
                                                structbox, indexboxes)

    @arguments("red", "interiordesc", "bool", "red_varargs",
               returns="green_from_red")
    def opimpl_green_getinteriorfield(self, structbox, interiordesc, deepfrozen,
                                      indexboxes):
        # XXX make a green version that does not use the constant folding of
        # the red one
        return interiordesc.gengetinteriorfield(self.jitstate, deepfrozen,
                                                structbox, indexboxes)

    @arguments("red", "interiordesc", "red_varargs", "red")
    def opimpl_red_setinteriorfield(self, destbox, interiordesc, indexboxes,
                                    valuebox):
        interiordesc.gensetinteriorfield(self.jitstate, destbox, valuebox, indexboxes)

    @arguments("red", "interiordesc", "red_varargs", returns="red")
    def opimpl_red_getinteriorarraysize(self, arraybox, interiordesc, indexboxes):
        return interiordesc.gengetinteriorarraysize(
            self.jitstate, arraybox, indexboxes)

    @arguments("red", "interiordesc", "red_varargs", returns="green_from_red")
    def opimpl_green_getinteriorarraysize(self, arraybox, interiordesc,
                                          indexboxes):
        # XXX make a green version that does not use the constant folding of
        # the red one
        return interiordesc.gengetinteriorarraysize(
            self.jitstate, arraybox, indexboxes)

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
                if not we_are_translated():
                    if opdesc.opname == "int_is_true":
                        # special case for tests, as in llinterp.py
                        if type(args[1]) is CDefinedIntSymbolic:
                            args = (args[0], args[1].default)
                result = self.rgenop.genconst(opdesc.llop(*args))
                self.green_result(result)
            implementation.argspec = ("green",) * len(list(numargs))
            implementation.resultspec = "green"
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
            implementation.argspec = ("red",) * len(list(numargs))
            implementation.resultspec = "red"
        else:
            assert 0, "unknown color"
        implementation.func_name = "opimpl_%s_%s" % (color, opdesc.opname)
        opname = "%s_%s" % (color, opdesc.opname)
        index = self.opname_to_index[opname] = len(self.opcode_implementations)
        self.opcode_implementations.append(implementation)
        self.opcode_descs.append(opdesc)
        return index


