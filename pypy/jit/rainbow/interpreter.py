from pypy.rlib.rarithmetic import intmask
from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.objectmodel import we_are_translated, CDefinedIntSymbolic, noop
from pypy.rlib.debug import debug_print
from pypy.jit.timeshifter import rtimeshift, rcontainer, rvalue
from pypy.jit.timeshifter.greenkey import empty_key, GreenKey, newgreendict
from pypy.jit.timeshifter.rcontainer import SegfaultException
from pypy.jit.rainbow import rhotpath
from pypy.jit.rainbow import typesystem
from pypy.rpython.lltypesystem import lltype, llmemory

import py
from pypy.tool.ansi_print import ansi_log
log = py.log.Producer('rainbow')
py.log.setconsumer('rainbow', ansi_log)

DEBUG_JITCODES = True     # store a dump() of all JitCodes
                          # in the translated program

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
    dump_copy = None

    def __init__(self, name, code, constants, typekinds, redboxclasses,
                 keydescs, structtypedescs, fielddescs, arrayfielddescs,
                 interiordescs, exceptioninstances, oopspecdescs,
                 promotiondescs, called_bytecodes, num_mergepoints,
                 graph_color, calldescs, metacalldescs,
                 indirectcalldescs, is_portal, owncalldesc, gv_ownfnptr):
        # XXX quite a lot of lists of descs here...  At least we
        # share identical lists between the numberous prebuilt
        # JitCode instances.
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
        self.exceptioninstances = exceptioninstances
        self.oopspecdescs = oopspecdescs
        self.promotiondescs = promotiondescs
        self.called_bytecodes = called_bytecodes
        self.num_mergepoints = num_mergepoints
        self.graph_color = graph_color
        self.calldescs = calldescs
        self.metacalldescs = metacalldescs
        self.indirectcalldescs = indirectcalldescs
        self.is_portal = is_portal
        self.owncalldesc = owncalldesc
        self.gv_ownfnptr = gv_ownfnptr

    def _freeze_(self):
        return True

    def __repr__(self):
        return '<JitCode %r>' % (getattr(self, 'name', '?'),)

    def dump(self, file=None):
        from pypy.jit.rainbow import dump
        dump.dump_bytecode(self, file=file)
        print >> file

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

class arguments(object):
    def __init__(self, *argtypes, **kwargs):
        self.result = kwargs.pop("returns", None)
        assert not kwargs
        self.argtypes = argtypes

    def __eq__(self, other):
        if not isinstance(other, arguments):
            return NotImplemented
        return self.argtypes == other.argtypes and self.result == other.result

    def __ne__(self, other):
        if not isinstance(other, arguments):
            return NotImplemented
        return self.argtypes != other.argtypes or self.result != other.result

    def __call__(self, func):
        result = self.result
        argtypes = unrolling_iterable(self.argtypes)
        def wrapped(self):
            args = (self, )
            for argspec in argtypes:
                if argspec == "red":
                    args += (self.get_redarg(), )
                elif argspec == "green":
                    args += (self.get_greenarg(), )
                elif argspec == "kind":
                    args += (self.getjitcode().typekinds[self.load_int()], )
                elif argspec == "jumptarget":
                    args += (self.load_4byte(), )
                elif argspec == "jumptargets":
                    num = self.load_int()
                    args += ([self.load_4byte() for i in range(num)], )
                elif argspec == "bool":
                    args += (self.load_bool(), )
                elif argspec == "redboxcls":
                    args += (self.getjitcode().redboxclasses[self.load_int()], )
                elif argspec == "2byte":
                    args += (self.load_int(), )
                elif argspec == "greenkey":
                    args += (self.get_greenkey(), )
                elif argspec == "promotiondesc":
                    promotiondescnum = self.load_int()
                    promotiondesc = self.getjitcode().promotiondescs[promotiondescnum]
                    args += (promotiondesc, )
                elif argspec == "green_varargs":
                    args += (self.get_green_varargs(), )
                elif argspec == "red_varargs":
                    args += (self.get_red_varargs(), )
                elif argspec == "bytecode":
                    bytecodenum = self.load_int()
                    args += (self.getjitcode().called_bytecodes[bytecodenum], )
                elif argspec == "calldesc":
                    index = self.load_int()
                    function = self.getjitcode().calldescs[index]
                    args += (function, )
                elif argspec == "metacalldesc":
                    index = self.load_int()
                    function = self.getjitcode().metacalldescs[index]
                    args += (function, )
                elif argspec == "indirectcalldesc":
                    index = self.load_int()
                    function = self.getjitcode().indirectcalldescs[index]
                    args += (function, )
                elif argspec == "oopspec":
                    oopspecindex = self.load_int()
                    oopspec = self.getjitcode().oopspecdescs[oopspecindex]
                    args += (oopspec, )
                elif argspec == "structtypedesc":
                    td = self.getjitcode().structtypedescs[self.load_int()]
                    args += (td, )
                elif argspec == "arraydesc":
                    td = self.getjitcode().arrayfielddescs[self.load_int()]
                    args += (td, )
                elif argspec == "fielddesc":
                    d = self.getjitcode().fielddescs[self.load_int()]
                    args += (d, )
                elif argspec == "interiordesc":
                    d = self.getjitcode().interiordescs[self.load_int()]
                    args += (d, )
                elif argspec == "exception":
                    d = self.getjitcode().exceptioninstances[self.load_int()]
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
        wrapped.argspec = self
        return wrapped


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
        self.jit_merge_point_state_dict = newgreendict()
        self.debug_traces = []
        if DEBUG_JITCODES:
            self.find_opcode("trace")     # force it to be compiled in

    def _debug_trace(self, *args):
        "NOT_RPYTHON"
        trace = DebugTrace(*args)
        log.trace(trace)
        self.debug_traces.append(trace)

    # a choice of two RPython-friendly implementation,
    # patched for tests in set_hotrunnerdesc():

    #debug_trace = staticmethod(noop)
    debug_trace = staticmethod(debug_print)

    def set_hotrunnerdesc(self, hotrunnerdesc):
        self.hotrunnerdesc = hotrunnerdesc
        if not hotrunnerdesc.translate_support_code:
            self.debug_trace = self._debug_trace

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
                                   self.exceptiondesc.null_exc_value_box,
                                   self.ts)

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

    def finish_jitstate_gray(self, graphsigtoken):
        jitstate = self.jitstate
        exceptiondesc = self.exceptiondesc
        builder = jitstate.curbuilder
        for virtualizable_box in jitstate.virtualizables:
            assert isinstance(virtualizable_box, rvalue.PtrRedBox)
            content = virtualizable_box.content
            assert isinstance(content, rcontainer.VirtualizableStruct)
            content.store_back(jitstate)        
        exceptiondesc.store_global_excdata(jitstate)
        jitstate.curbuilder.finish_and_return(graphsigtoken, None)

    def bytecode_loop(self):
        while 1:
            bytecode = self.load_int()
            assert bytecode >= 0
            result = self.opcode_implementations[bytecode](self)
            assert (self.frame is None or not self.frame.local_boxes or
                    self.frame.local_boxes[-1] is not None)
            if result is STOP:
                return
            else:
                assert result is None

    def dispatch(self):
        frame = self.frame
        queue = self.queue
        while 1:
            newjitstate = rtimeshift.dispatch_next(queue)
            resumepoint = rtimeshift.getresumepoint(newjitstate)
            self.newjitstate(newjitstate)
            if resumepoint == -1:
                is_portal = frame.bytecode.is_portal
                graph_color = frame.bytecode.graph_color
                if graph_color == "gray":
                    #assert not is_portal
                    newjitstate = rtimeshift.leave_graph_gray(queue)
                elif is_portal or graph_color == "red":
                    newjitstate = rtimeshift.leave_graph_red(
                            queue, is_portal)
                elif graph_color == "yellow":
                    newjitstate = rtimeshift.leave_graph_yellow(queue)
                elif graph_color == "green":
                    assert 0, "green graphs shouldn't be seen by the rainbow interp"
                else:
                    assert 0, "unknown graph color %s" % (graph_color, )

                self.newjitstate(newjitstate)
                if self.frame is not None:
                    newjitstate = rtimeshift.collect_split(
                        self.jitstate, self.frame.pc,
                        self.frame.local_green)
                    assert newjitstate.frame.bytecode is self.frame.bytecode
                    assert newjitstate.frame.pc == self.frame.pc
                    self.newjitstate(newjitstate)
                else:
                    if frame.backframe is not None:
                        frame = frame.backframe
                        queue = frame.dispatchqueue
                        continue
                    return STOP
            else:
                # XXX the 'resumepoint' value is not really needed any more
                assert self.frame.pc == resumepoint
            return

    # operation helper functions
    def getjitcode(self):
        return self.frame.bytecode

    def load_int(self):
        result = 0
        shift = 0
        pc = self.frame.pc
        while 1:
            byte = ord(self.frame.bytecode.code[pc])
            pc += 1
            result += (byte & 0x7F) << shift
            shift += 7
            if not byte & 0x80:
                break
        self.frame.pc = pc
        return intmask(result)

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
        pc = self.frame.pc
        assert pc >= 0
        result = ord(self.frame.bytecode.code[pc])
        self.frame.pc = pc + 1
        return bool(result)

    def get_greenarg(self):
        i = self.load_int()
        if i % 2:
            return self.frame.bytecode.constants[i // 2]
        return self.frame.local_green[i // 2]

    def get_green_varargs(self):
        greenargs = []
        num = self.load_int()
        for i in range(num):
            greenargs.append(self.get_greenarg())
        return greenargs

    def get_red_varargs(self):
        redargs = []
        num = self.load_int()
        for i in range(num):
            redargs.append(self.get_redarg())
        return redargs

    def get_redarg(self):
        return self.frame.local_boxes[self.load_int()]

    def get_greenkey(self):
        keydescnum = self.load_int()
        if keydescnum == 0:
            return empty_key
        else:
            keydesc = self.frame.bytecode.keydescs[keydescnum - 1]
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

    def dump(self):
        # Prints the current frame position and a dump if available.
        # Although this opcode is not actually generated by
        # codewriter.py so far, it can be called manually in a C-level
        # debugger.  More importantly it forces the .name and .dump_copy
        # attributes of JitCode objects to be included in the C
        # executable.
        bytecode = self.frame.bytecode
        msg = '*** opimpl_trace: in %s position %d ***' % (bytecode.name,
                                                           self.frame.pc)
        print msg
        if bytecode.dump_copy is not None:
            print bytecode.dump_copy
        from pypy.jit.timeshifter import rdump
        rdump.dump_jitstate(self.jitstate)
        return msg
    dump._dont_inline_ = True

    # operation implementations
    @arguments()
    def opimpl_trace(self):
        msg = self.dump()
        self.debug_trace(msg)

    @arguments("green", "2byte", returns="red")
    def opimpl_make_redbox(self, genconst, typeid):
        redboxcls = self.frame.bytecode.redboxclasses[typeid]
        kind = self.frame.bytecode.typekinds[typeid]
        return redboxcls(kind, genconst)

    @arguments("red", returns="green_from_red")
    def opimpl_revealconst(self, box):
        return box

    @arguments("jumptarget")
    def opimpl_goto(self, target):
        self.frame.pc = target

    @arguments("green", "jumptarget")
    def opimpl_green_goto_iftrue(self, genconst, target):
        arg = genconst.revealconst(lltype.Bool)
        if arg:
            self.frame.pc = target

    @arguments("green", "green_varargs", "jumptargets")
    def opimpl_green_switch(self, exitcase, cases, targets):
        arg = exitcase.revealconst(lltype.Signed)
        assert len(cases) == len(targets)
        for i in range(len(cases)):
            if arg == cases[i].revealconst(lltype.Signed):
                self.frame.pc = targets[i]
                break


    @arguments("red", "jumptarget")
    def opimpl_red_goto_iftrue(self, switchbox, target):
        # XXX not sure about passing no green vars
        decision = rtimeshift.split(self.jitstate, switchbox, self.frame.pc)
        if decision:
            self.frame.pc = target

    @arguments("red", "jumptarget")
    def opimpl_goto_if_constant(self, valuebox, target):
        if valuebox.is_constant():
            self.frame.pc = target

    @arguments("exception")
    def opimpl_split_raisingop(self, ll_evalue):
        # XXX not sure about passing no green vars
        rtimeshift.split_raisingop(self.jitstate, self.frame.pc, ll_evalue)


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
    def opimpl_learn_nonzeroness(self, redbox, boolval):
        assert isinstance(redbox, rvalue.PtrRedBox)
        redbox.learn_nonzeroness(self.jitstate, boolval)

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

    @arguments("green_varargs")
    def opimpl_make_new_greenvars(self, newgreens):
        self.frame.local_green = newgreens

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

    @arguments("green_varargs", "red_varargs")
    def opimpl_portal_call(self, greenargs, redargs):
        self.portalstate.portal_reentry(greenargs, redargs)
        newjitstate = rtimeshift.collect_split(
            self.jitstate, self.frame.pc,
            self.frame.local_green)
        assert newjitstate.frame.bytecode is self.frame.bytecode
        assert newjitstate.frame.pc == self.frame.pc
        self.newjitstate(newjitstate)

    @arguments("green", "calldesc", "green_varargs")
    def opimpl_green_call(self, fnptr_gv, calldesc, greenargs):
        calldesc.green_call(self, fnptr_gv, greenargs)

    @arguments("green_varargs", "red_varargs", "bytecode")
    def opimpl_yellow_direct_call(self, greenargs, redargs, targetbytecode):
        self.run(self.jitstate, targetbytecode, greenargs, redargs,
                 start_bytecode_loop=False)

    @arguments("green_varargs", "red_varargs", "red", "indirectcalldesc")
    def opimpl_indirect_call_const(self, greenargs, redargs,
                                      funcptrbox, callset):
        gv = funcptrbox.getgenvar(self.jitstate)
        addr = gv.revealconst(llmemory.Address)
        bytecode = callset.bytecode_for_address(addr)
        self.run(self.jitstate, bytecode, greenargs, redargs,
                 start_bytecode_loop=False)

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
        return oopspec.ll_handler(self.jitstate, oopspec, deepfrozen)

    @arguments("oopspec", "bool", "red", returns="red")
    def opimpl_red_oopspec_call_1(self, oopspec, deepfrozen, arg1):
        return oopspec.ll_handler(self.jitstate, oopspec, deepfrozen, arg1)

    @arguments("oopspec", "bool", "red", "red", returns="red")
    def opimpl_red_oopspec_call_2(self, oopspec, deepfrozen, arg1, arg2):
        return oopspec.ll_handler(self.jitstate, oopspec, deepfrozen, arg1, arg2)

    @arguments("oopspec", "bool", "red", "red", "red", returns="red")
    def opimpl_red_oopspec_call_3(self, oopspec, deepfrozen, arg1, arg2, arg3):
        return oopspec.ll_handler(self.jitstate, oopspec, deepfrozen, arg1, arg2, arg3)

    @arguments("oopspec", "bool")
    def opimpl_red_oopspec_call_noresult_0(self, oopspec, deepfrozen):
        oopspec.ll_handler(self.jitstate, oopspec, deepfrozen)

    @arguments("oopspec", "bool", "red")
    def opimpl_red_oopspec_call_noresult_1(self, oopspec, deepfrozen, arg1):
        oopspec.ll_handler(self.jitstate, oopspec, deepfrozen, arg1)

    @arguments("oopspec", "bool", "red", "red")
    def opimpl_red_oopspec_call_noresult_2(self, oopspec, deepfrozen, arg1, arg2):
        oopspec.ll_handler(self.jitstate, oopspec, deepfrozen, arg1, arg2)

    @arguments("oopspec", "bool", "red", "red", "red")
    def opimpl_red_oopspec_call_noresult_3(self, oopspec, deepfrozen, arg1, arg2, arg3):
        oopspec.ll_handler(self.jitstate, oopspec, deepfrozen, arg1, arg2, arg3)

    @arguments("promotiondesc")
    def opimpl_after_oop_residual_call(self, promotiondesc):
        exceptiondesc = self.exceptiondesc
        check_forced = False
        flagbox = rtimeshift.after_residual_call(self.jitstate,
                                                 exceptiondesc, check_forced)
        # XXX slightly hackish: the flagbox needs to be in local_boxes
        # to be passed along to the new block
        self.frame.local_boxes.append(flagbox)
        try:
            done = rtimeshift.promote(self.jitstate, flagbox, promotiondesc)
        finally:
            self.frame.local_boxes.pop()
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
        # XXX slightly hackish: the flagbox needs to be in local_boxes
        # to be passed along to the new block
        self.frame.local_boxes.append(flagbox)
        try:
            done = rtimeshift.promote(self.jitstate, flagbox, promotiondesc)
        finally:
            self.frame.local_boxes.pop()
        if done:
            return self.dispatch()
        gv_flag = flagbox.getgenvar(self.jitstate)
        assert gv_flag.is_const
        rtimeshift.residual_fetch(self.jitstate, self.exceptiondesc,
                                  True, flagbox)

    @arguments("metacalldesc", "red_varargs", returns="red")
    def opimpl_metacall(self, metafunc, redargs):
        return metafunc(self, redargs)


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
        return structtypedesc.factory()

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

    @arguments("green", "fielddesc", returns="green")
    def opimpl_green_getfield(self, gv_struct, fielddesc):
        return fielddesc.perform_getfield(self.rgenop, gv_struct)

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

    @arguments("green", "arraydesc", "green", returns="green")
    def opimpl_green_getarrayitem(self, gv_array, fielddesc, gv_index):
        return fielddesc.perform_getarrayitem(self.rgenop, gv_array, gv_index)

    @arguments("green", "arraydesc", returns="green")
    def opimpl_green_getarraysize(self, gv_array, fielddesc):
        return fielddesc.perform_getarraysize(self.rgenop, gv_array)

    @arguments("red", "interiordesc", "red_varargs", "bool", returns="red")
    def opimpl_red_getinteriorfield(self, structbox, interiordesc,
                                    indexboxes, deepfrozen):
        return interiordesc.gengetinteriorfield(self.jitstate, deepfrozen,
                                                structbox, indexboxes)

    @arguments("green", "interiordesc", "green_varargs", returns="green")
    def opimpl_green_getinteriorfield(self, gv_struct, interiordesc,
                                      indexes_gv):
        return interiordesc.perform_getinteriorfield(self.rgenop, gv_struct,
                                                     indexes_gv)

    @arguments("red", "interiordesc", "red_varargs", "red")
    def opimpl_red_setinteriorfield(self, destbox, interiordesc, indexboxes,
                                    valuebox):
        interiordesc.gensetinteriorfield(self.jitstate, destbox, valuebox, indexboxes)

    @arguments("red", "interiordesc", "red_varargs", returns="red")
    def opimpl_red_getinteriorarraysize(self, arraybox, interiordesc, indexboxes):
        return interiordesc.gengetinteriorarraysize(
            self.jitstate, arraybox, indexboxes)

    @arguments("green", "interiordesc", "green_varargs", returns="green")
    def opimpl_green_getinteriorarraysize(self, gv_array, interiordesc,
                                          indexes_gv):
        return interiordesc.perform_getinteriorarraysize(self.rgenop,
                                                         gv_array,
                                                         indexes_gv)

    @arguments("red", "green", "green", returns="green")
    def opimpl_is_constant(self, arg, true, false):
        if arg.is_constant():
            return true
        return false

    # ____________________________________________________________
    # opcodes used by the 'hotpath' policy

    @arguments("greenkey")
    def opimpl_jit_merge_point(self, key):
        states_dic = self.jit_merge_point_state_dict
        global_resumer = RainbowResumer(self, self.frame)
        done = rtimeshift.retrieve_jitstate_for_merge(states_dic,
                                                      self.jitstate,
                                                      key, None)
        if done:
            self.debug_trace("done at jit_merge_point")
            self.newjitstate(None)
            raise rhotpath.FinishedCompiling

    @arguments()
    def opimpl_can_enter_jit(self):
        pass       # useful for the fallback interpreter only

    @arguments("red", "jumptarget")
    def opimpl_hp_red_goto_iftrue(self, switchbox, target):
        if switchbox.is_constant():
            if switchbox.getgenvar(self.jitstate).revealconst(lltype.Bool):
                self.frame.pc = target
        else:
            self.debug_trace("pause at hotsplit in", self.frame.bytecode.name)
            rhotpath.hotsplit(self.jitstate, self.hotrunnerdesc,
                              switchbox, self.frame.pc, target)
            assert False, "unreachable"

    @arguments("red", "promotiondesc")
    def opimpl_hp_promote(self, promotebox, promotiondesc):
        if promotebox.is_constant():
            self.green_result_from_red(promotebox)
        else:
            self.debug_trace("pause at promote in", self.frame.bytecode.name)
            rhotpath.hp_promote(self.jitstate, self.hotrunnerdesc,
                                promotebox, promotiondesc)
            assert False, "unreachable"

    def hp_direct_call(self, greenargs, redargs, targetbytecode):
        frame = rtimeshift.VirtualFrame(self.frame, None)
        self.frame = self.jitstate.frame = frame
        frame.pc = 0
        frame.bytecode = targetbytecode
        frame.local_boxes = redargs
        frame.local_green = greenargs

    @arguments("green_varargs", "red_varargs", "bytecode")
    def opimpl_hp_red_direct_call(self, greenargs, redargs, targetbytecode):
        self.hp_direct_call(greenargs, redargs, targetbytecode)

    opimpl_hp_gray_direct_call = opimpl_hp_red_direct_call
    opimpl_hp_yellow_direct_call = opimpl_hp_red_direct_call

    @arguments("green_varargs", "red_varargs", "green", "indirectcalldesc")
    def opimpl_hp_red_indirect_call(self, greenargs, redargs, gv_funcptr,
                                    callset):
        addr = gv_funcptr.revealconst(llmemory.Address)
        bytecode = callset.bytecode_for_address(addr)
        self.hp_direct_call(greenargs, redargs, bytecode)

    opimpl_hp_gray_indirect_call = opimpl_hp_red_indirect_call
    opimpl_hp_yellow_indirect_call = opimpl_hp_red_indirect_call

    @arguments("red", "calldesc", "bool", "bool", "red_varargs")
    def opimpl_hp_residual_call(self, funcbox, calldesc, withexc, has_result,
                                redargs):
        result = rtimeshift.gen_residual_call(self.jitstate, calldesc,
                                              funcbox, redargs)
        if has_result:
            self.red_result(result)
        rhotpath.hp_after_residual_call(self.jitstate, self.hotrunnerdesc,
                                        withexc, True)

    @arguments("exception")
    def opimpl_hp_split_raisingop(self, ll_evalue):
        rhotpath.hp_after_raisingop(self.jitstate, self.hotrunnerdesc,
                                    ll_evalue)

    def hp_return(self):
        frame = self.frame.backframe
        if frame is None:
            return True
        else:
            self.frame = self.jitstate.frame = frame
            return False

    @arguments()
    def opimpl_hp_gray_return(self):
        if self.hp_return():
            rhotpath.hp_return(self, None)
            assert False, "unreachable"

    @arguments()
    def opimpl_hp_red_return(self):
        box = self.frame.local_boxes[0]
        if self.hp_return():
            gv_result = box.getgenvar(self.jitstate)
            rhotpath.hp_return(self, gv_result)
            assert False, "unreachable"
        else:
            self.red_result(box)

    @arguments()
    def opimpl_hp_yellow_return(self):
        gv_result = self.frame.local_green[0]
        if self.hp_return():
            rhotpath.hp_return(self, gv_result)
            assert False, "unreachable"
        else:
            self.green_result(gv_result)

    # ____________________________________________________________
    # construction-time interface

    def _register_opcode_if_implemented(self, opname):
        name = "opimpl_" + opname
        if hasattr(self, name):
            self.opname_to_index[opname] = len(self.opcode_implementations)
            self.opcode_implementations.append(getattr(self, name).im_func)
            self.opcode_descs.append(None)

    def find_opcode(self, name):
        if name not in self.opname_to_index:
            self._register_opcode_if_implemented(name)
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
        elif color == "red":
            if opdesc.nb_args == 1:
                if opdesc.canraise:
                    impl = rtimeshift.ll_gen1_canraise
                else:
                    impl = rtimeshift.ll_gen1
            elif opdesc.nb_args == 2:
                if opdesc.canraise:
                    impl = rtimeshift.ll_gen2_canraise
                else:
                    impl = rtimeshift.ll_gen2
            else:
                XXX
            @arguments(*(("red", ) * opdesc.nb_args))  
            def implementation(self, *args):
                result = impl(opdesc, self.jitstate, *args)
                self.red_result(result)
        else:
            assert 0, "unknown color"
        implementation.func_name = "opimpl_%s_%s" % (color, opdesc.opname)
        # build an arguments() for dump.py
        colorarglist = [color] * opdesc.nb_args
        resultdict = {"returns": color}
        implementation.argspec = arguments(*colorarglist, **resultdict)

        opname = "%s_%s" % (color, opdesc.opname)
        index = self.opname_to_index[opname] = len(self.opcode_implementations)
        self.opcode_implementations.append(implementation)
        self.opcode_descs.append(opdesc)
        return index

class LLTypeJitInterpreter(JitInterpreter):
    ts = typesystem.llhelper

class OOTypeJitInterpreter(JitInterpreter):
    ts = typesystem.oohelper

    @arguments("red", "fielddesc", "bool", returns="red")
    def opimpl_red_oogetfield(self, structbox, fielddesc, deepfrozen):
        return rtimeshift.gengetfield(self.jitstate, deepfrozen, fielddesc,
                                      structbox)

    @arguments("red", "fielddesc", "red")
    def opimpl_red_oosetfield(self, destbox, fielddesc, valuebox):
        rtimeshift.gensetfield(self.jitstate, fielddesc, destbox,
                               valuebox)

    @arguments("structtypedesc", returns="red")
    def opimpl_red_new(self, structtypedesc):
        return structtypedesc.factory()


class DebugTrace(object):
    def __init__(self, *args):
        self.args = args or ('--empty--',)
        self.captured_repr = ' '.join(map(str, self.args))
        # if 'args' contains mutable objects, computing
        # map(str, self.args) several times would return different
        # results, which is unexpected for a debug trace

    def __repr__(self):
        return '<DebugTrace %s>' % (self,)

    def __str__(self):
        return self.captured_repr
