"""
RPython support code for the hotpath policy.
"""

from pypy.jit.codegen.i386.rgenop import cast_whatever_to_int
from pypy.jit.timeshifter import rtimeshift, rvalue
from pypy.rlib.objectmodel import we_are_translated, specialize
from pypy.rpython.annlowlevel import cachedtype, base_ptr_lltype
from pypy.rpython.annlowlevel import llhelper
from pypy.rpython.annlowlevel import cast_instance_to_base_ptr
from pypy.rpython.annlowlevel import cast_base_ptr_to_instance
from pypy.rpython.lltypesystem import lltype, llmemory, lloperation


def setup_jitstate(interp, jitstate, greenargs, redargs,
                   bytecode, graphsigtoken):
    frame = rtimeshift.VirtualFrame(None, None)
    interp.jitstate = jitstate
    interp.frame = jitstate.frame = frame
    interp.frame.pc = 0
    interp.frame.bytecode = bytecode
    interp.frame.local_boxes = redargs
    interp.frame.local_green = greenargs
    interp.graphsigtoken = graphsigtoken

def leave_graph(interp, store_back_exc_data=True):
    jitstate = interp.jitstate
    exceptiondesc = interp.exceptiondesc
    builder = jitstate.curbuilder
    if store_back_exc_data:
        exceptiondesc.store_global_excdata(jitstate)
    jitstate.curbuilder.finish_and_return(interp.graphsigtoken, None)
    jitstate.curbuilder = None
    raise FinishedCompiling

def compile(interp):
    jitstate = interp.jitstate
    builder = jitstate.curbuilder
    try:
        interp.bytecode_loop()
        assert False, "unreachable"
    except FinishedCompiling:
        pass
    builder.show_incremental_progress()

def report_compile_time_exception(interp, e):
    if not we_are_translated():
        from pypy.jit.rainbow.interpreter import log
        import sys, pdb, traceback
        msg = str(e)
        if msg: msg = ': ' + msg
        msg = e.__class__.__name__ + msg
        log.ERROR("*** compilation-time error ***")
        log.ERROR(msg)
        traceback.print_exc()
        print >> sys.stderr
        pdb.post_mortem(sys.exc_info()[2])
    else:
        msg = 'Note: the JIT got a compile-time exception: %s' % (e,)
        lloperation.llop.debug_print(lltype.Void, msg)
    interp.debug_trace("ERROR:", "compile-time exception:", e)

def hp_return(interp, gv_result):
    interp.debug_trace("done at hp_return")
    interp.jitstate.store_back_virtualizables_at_return()
    # XXX slowish
    desc = interp.hotrunnerdesc
    exitfnptr = llhelper(desc.RAISE_DONE_FUNCPTR, desc.raise_done)
    gv_exitfnptr = interp.rgenop.genconst(exitfnptr)
    if gv_result is None:
        args_gv = []
    else:
        args_gv = [gv_result]
    interp.jitstate.curbuilder.genop_call(desc.tok_raise_done,
                                          gv_exitfnptr, args_gv)
    leave_graph(interp)

# ____________________________________________________________

class FinishedCompiling(Exception):
    pass

class HotPromotionDesc:
    __metaclass__ = cachedtype

    def __init__(self, ERASED, RGenOp):
        self.RGenOp = RGenOp
        pathkind = "%s path" % (ERASED,)
        is_signed = (ERASED == RGenOp.erasedType(lltype.Signed))

        def ll_reach_fallback_point(fallback_point_ptr, value, framebase):
            fbp = _cast_base_ptr_to_fallback_point(fallback_point_ptr)
            try:
                # check if we should compile for this value.
                path_is_hot = fbp.check_should_compile(value)

                if path_is_hot:
                    # this is a hot path, compile it
                    interpreter = fbp.hotrunnerdesc.interpreter
                    interpreter.debug_trace("jit_resume", pathkind, value,
                        "in", fbp.saved_jitstate.frame.bytecode.name)
                    fbp.compile_hot_path(value)
                    # Done.  We return without an exception set, which causes
                    # our caller (the machine code produced by hotsplit()) to
                    # loop back to the flexswitch and execute the
                    # newly-generated code.
                    interpreter.debug_trace("resume_machine_code")
                    return
                # else: path is still cold

            except Exception, e:
                interpreter = fbp.hotrunnerdesc.interpreter
                report_compile_time_exception(interpreter, e)

            # exceptions below at run-time exceptions, we let them propagate
            from pypy.jit.rainbow.fallback import FallbackInterpreter
            if is_signed and fbp.check_virtualizables():
                shapemask = value & ~ 1
            else:
                shapemask = -1
            fallbackinterp = FallbackInterpreter(fbp, framebase, shapemask)
            fbp.prepare_fallbackinterp(fallbackinterp, value)
            fallbackinterp.bytecode_loop()
            # If the fallback interpreter reached the next jit_merge_point(),
            # it raised ContinueRunningNormally().  This exception is
            # caught by portal_runner() from hotpath.py in order to loop
            # back to the beginning of the portal.
            assert 0, "unreachable"

        self.ll_reach_fallback_point = ll_reach_fallback_point
        ll_reach_fallback_point._debugexc = True

        FUNCTYPE = lltype.FuncType([base_ptr_lltype(), ERASED,
                                    llmemory.Address], lltype.Void)
        FUNCPTRTYPE = lltype.Ptr(FUNCTYPE)
        self.FUNCPTRTYPE = FUNCPTRTYPE
        self.sigtoken = RGenOp.sigToken(FUNCTYPE)

        def get_gv_reach_fallback_point(builder):
            fnptr = llhelper(FUNCPTRTYPE, ll_reach_fallback_point)
            # ^^^ the llhelper cannot be attached on 'self' directly, because
            # the translator needs to see its construction done by RPython code
            return builder.rgenop.genconst(fnptr)
        self.get_gv_reach_fallback_point = get_gv_reach_fallback_point

    def _freeze_(self):
        return True


class FallbackPoint(object):

    def __init__(self, jitstate, hotrunnerdesc, promotebox):
        # XXX we should probably trim down the jitstate once our caller
        # is done with it, to avoid keeping too much stuff in memory
        self.saved_jitstate = jitstate
        self.hotrunnerdesc = hotrunnerdesc
        self.promotebox = promotebox

    def set_machine_code_info(self, flexswitch, frameinfo):
        self.flexswitch = flexswitch
        self.frameinfo = frameinfo
        # ^^^ 'frameinfo' describes where the machine code stored all
        # its GenVars, so that we can fish these values to pass them
        # to the fallback interpreter

    def check_virtualizables(self):
        return False

    # hack for testing: make the llinterpreter believe this is a Ptr to base
    # instance
    _TYPE = base_ptr_lltype()


class HotSplitFallbackPoint(FallbackPoint):
    falsepath_counter = 0     # -1 after this path was compiled
    truepath_counter = 0      # -1 after this path was compiled

    def __init__(self, jitstate, hotrunnerdesc, promotebox,
                 falsepath_pc, truepath_pc):
        FallbackPoint. __init__(self, jitstate, hotrunnerdesc, promotebox)
        self.falsepath_pc = falsepath_pc
        self.truepath_pc = truepath_pc

    @specialize.arglltype(1)
    def check_should_compile(self, value):
        # 'value' should be a Bool, but depending on the backend
        # it could have been ERASED to about anything else
        value = bool(value)
        threshold = self.hotrunnerdesc.state.threshold
        if value:
            if self.falsepath_counter >= 0: # if other path not compiled either
                bump = self.hotrunnerdesc.state.trace_eagerness
            else:
                bump = 1
            counter = self.truepath_counter + bump
            assert counter > 0, (
                "reaching a fallback point for an already-compiled path")
            if counter >= threshold:
                return True
            self.truepath_counter = counter
            return False
        else:
            if self.truepath_counter >= 0: # if other path not compiled either
                bump = self.hotrunnerdesc.state.trace_eagerness
            else:
                bump = 1
            counter = self.falsepath_counter + bump
            assert counter > 0, (
                "reaching a fallback point for an already-compiled path")
            if counter >= threshold:
                return True
            self.falsepath_counter = counter
            return False   # path is still cold

    @specialize.arglltype(2)
    def prepare_fallbackinterp(self, fallbackinterp, value):
        value = bool(value)
        if value:
            fallbackinterp.pc = self.truepath_pc
        else:
            fallbackinterp.pc = self.falsepath_pc

    @specialize.arglltype(1)
    def compile_hot_path(self, value):
        value = bool(value)
        if value:
            pc = self.truepath_pc
        else:
            pc = self.falsepath_pc
        self._compile_hot_path(value, pc)
        if value:
            self.truepath_counter = -1    # means "compiled"
        else:
            self.falsepath_counter = -1   # means "compiled"

    def _compile_hot_path(self, case, pc):
        if self.falsepath_counter == -1 or self.truepath_counter == -1:
            # the other path was already compiled, we can reuse the jitstate
            jitstate = self.saved_jitstate
            self.saved_jitstate = None
            switchbox = self.promotebox
        else:
            # clone the jitstate
            memo = rvalue.copy_memo()
            jitstate = self.saved_jitstate.clone(memo)
            switchbox = memo.boxes[self.promotebox]
        interpreter = self.hotrunnerdesc.interpreter
        interpreter.newjitstate(jitstate)
        interpreter.frame.pc = pc
        gv_case = self.hotrunnerdesc.interpreter.rgenop.genconst(case)
        jitstate.curbuilder = self.flexswitch.add_case(gv_case)
        switchbox.learn_boolvalue(jitstate, case)
        compile(interpreter)


class PromoteFallbackPoint(FallbackPoint):

    def __init__(self, jitstate, hotrunnerdesc, promotebox, hotpromotiondesc):
        FallbackPoint. __init__(self, jitstate, hotrunnerdesc, promotebox)
        self.hotpromotiondesc = hotpromotiondesc
        self.counters = {}

    @specialize.arglltype(1)
    def check_should_compile(self, value):
        # XXX unsafe with a moving GC
        hash = cast_whatever_to_int(lltype.typeOf(value), value)
        counter = self.counters.setdefault(hash, 0)
        if len(self.counters) == 1:   # if no other path compiled so far
            bump = self.hotrunnerdesc.state.trace_eagerness
        else:
            bump = 1
        counter = counter + bump
        threshold = self.hotrunnerdesc.state.threshold
        assert counter > 0, (
            "reaching a fallback point for an already-compiled path")
        if counter >= threshold:
            return True
        self.counters[hash] = counter
        return False

    @specialize.arglltype(2)
    def prepare_fallbackinterp(self, fallbackinterp, value):
        gv_value = self.hotrunnerdesc.interpreter.rgenop.genconst(value)
        fallbackinterp.local_green.append(gv_value)

    @specialize.arglltype(1)
    def compile_hot_path(self, value):
        hash = cast_whatever_to_int(lltype.typeOf(value), value)
        gv_value = self.hotrunnerdesc.interpreter.rgenop.genconst(value)
        self._compile_hot_path(gv_value, hash)

    def _compile_hot_path(self, gv_value, hash):
        # clone the jitstate
        memo = rvalue.copy_memo()
        jitstate = self.saved_jitstate.clone(memo)
        promotebox = memo.boxes[self.promotebox]
        promotebox.setgenvar(gv_value)
        # compile from that state
        interpreter = self.hotrunnerdesc.interpreter
        interpreter.newjitstate(jitstate)
        jitstate.curbuilder = self.flexswitch.add_case(gv_value)
        self.prepare_compiler(interpreter, gv_value)
        compile(interpreter)
        # done
        self.counters[hash] = -1     # means "compiled"

    def prepare_compiler(self, interpreter, gv_value):
        interpreter.green_result(gv_value)


def hotsplit(jitstate, hotrunnerdesc, switchbox,
             falsepath_pc, truepath_pc):
    # produce a Bool flexswitch for now
    fbp = HotSplitFallbackPoint(jitstate, hotrunnerdesc, switchbox,
                                falsepath_pc, truepath_pc)
    desc = hotrunnerdesc.bool_hotpromotiondesc
    generate_fallback_code(fbp, desc, switchbox)

def hp_promote(jitstate, hotrunnerdesc, promotebox, hotpromotiondesc):
    fbp = PromoteFallbackPoint(jitstate, hotrunnerdesc, promotebox,
                               hotpromotiondesc)
    generate_fallback_code(fbp, hotpromotiondesc, promotebox)

def generate_fallback_code(fbp, hotpromotiondesc, switchbox,
                           check_exceptions=False):
    jitstate = fbp.saved_jitstate
    incoming = jitstate.enter_block_sweep_virtualizables()
    switchblock = rtimeshift.enter_next_block(jitstate, incoming)
    gv_switchvar = switchbox.genvar
    incoming_gv = [box.genvar for box in incoming]
    flexswitch, default_builder = jitstate.curbuilder.flexswitch(gv_switchvar,
                                                                 incoming_gv)
    jitstate.curbuilder = default_builder

    # default case of the switch:
    exceptiondesc = fbp.hotrunnerdesc.exceptiondesc

    if check_exceptions:
        # virtualize the exception (if any) by loading it into the jitstate
        exceptiondesc.fetch_global_excdata(jitstate)
        # xxx a bit fragile
        incoming_gv.append(jitstate.exc_type_box.genvar)
        incoming_gv.append(jitstate.exc_value_box.genvar)

    frameinfo = default_builder.get_frame_info(incoming_gv)
    fbp.set_machine_code_info(flexswitch, frameinfo)
    ll_fbp = _cast_fallback_point_to_base_ptr(fbp)
    gv_fbp = default_builder.rgenop.genconst(ll_fbp)
    gv_switchvar = switchbox.genvar
    gv_fnptr = hotpromotiondesc.get_gv_reach_fallback_point(default_builder)
    gv_framebase = default_builder.genop_get_frame_base()
    default_builder.genop_call(hotpromotiondesc.sigtoken,
                               gv_fnptr,
                               [gv_fbp, gv_switchvar, gv_framebase])
    # The call above may either return normally, meaning that more machine
    # code was compiled and we should loop back to 'switchblock' to enter it,
    # or it may have set an exception.
    gv_exc_type = exceptiondesc.genop_get_exc_type(default_builder)
    gv_noexc = default_builder.genop_ptr_iszero(gv_exc_type)
    excpath_builder = default_builder.jump_if_false(gv_noexc, [])

    if check_exceptions:
        # unvirtualize the exception
        exceptiondesc.store_global_excdata(jitstate)
        # note that the exc_type_box and exc_value_box stay in the jitstate,
        # where the fallback interp can find them.  When compiling more code
        # they are replaced by null boxes if we know that no exception
        # occurred.
        incoming_gv.pop()
        incoming_gv.pop()
    default_builder.finish_and_goto(incoming_gv, switchblock)

    jitstate.curbuilder = excpath_builder
    excpath_builder.start_writing()
    # virtualizables: when we reach this point, the fallback interpreter
    # should already have done the right thing, i.e. stored the values
    # back into the structure (reading them out of framebase+frameinfo)
    leave_graph(fbp.hotrunnerdesc.interpreter, store_back_exc_data=False)

# for testing purposes
def _cast_base_ptr_to_fallback_point(ptr):
    if we_are_translated():
        return cast_base_ptr_to_instance(FallbackPoint, ptr)
    else:
        return ptr

def _cast_fallback_point_to_base_ptr(instance):
    assert isinstance(instance, FallbackPoint)
    if we_are_translated():
        return cast_instance_to_base_ptr(instance)
    else:
        return instance

# ____________________________________________________________

# support for reading the state after a residual call, XXX a bit lengthy

class AfterResidualCallFallbackPoint(PromoteFallbackPoint):

    def __init__(self, jitstate, hotrunnerdesc, promotebox, hotpromotiondesc,
                 check_forced):
        PromoteFallbackPoint.__init__(self, jitstate, hotrunnerdesc,
                                      promotebox, hotpromotiondesc)
        self.check_forced = check_forced

    def check_virtualizables(self):
        return self.check_forced

    @specialize.arglltype(2)
    def prepare_fallbackinterp(self, fallbackinterp, value):
        fallbackinterp.local_red.pop()   # remove the temporary flagbox

    def prepare_compiler(self, interpreter, gv_value):
        # remove the temporary flagbox
        flagbox = interpreter.frame.local_boxes.pop()
        jitstate = interpreter.jitstate
        exceptiondesc = self.hotrunnerdesc.exceptiondesc

        # remove the temporary exception boxes that may have been
        # put on the JITState by generate_fallback_code()
        jitstate.exc_type_box  = exceptiondesc.null_exc_type_box
        jitstate.exc_value_box = exceptiondesc.null_exc_value_box

        rtimeshift.residual_fetch(jitstate, exceptiondesc,
                                  self.check_forced, flagbox)


def hp_after_residual_call(jitstate, hotrunnerdesc, withexc, check_forced):
    if withexc:
        exceptiondesc = hotrunnerdesc.exceptiondesc
    else:
        exceptiondesc = None
    gv_flags = rtimeshift.gvflags_after_residual_call(jitstate,
                                                      exceptiondesc,
                                                      check_forced)
    if gv_flags is None:
        return     # nothing to check
    # XXX slightly hackish: the gv_flags needs to be in local_boxes
    # to be passed along to the new block
    assert not gv_flags.is_const
    tok_signed = hotrunnerdesc.RGenOp.kindToken(lltype.Signed)
    flagbox = rvalue.IntRedBox(gv_flags)
    jitstate.frame.local_boxes.append(flagbox)

    hotpromotiondesc = hotrunnerdesc.signed_hotpromotiondesc
    fbp = AfterResidualCallFallbackPoint(jitstate, hotrunnerdesc,
                                         flagbox, hotpromotiondesc,
                                         check_forced)
    generate_fallback_code(fbp, hotpromotiondesc, flagbox,
                           check_exceptions=withexc)
    assert 0, "unreachable"

# ____________________________________________________________

# support for turning the 'gv_raised' left behind by primitive raising
# operations directly into a virtualized exception on the JITState,
# splitting the machine code in two paths.

class AfterRaisingOpFallbackPoint(PromoteFallbackPoint):
        
    def __init__(self, jitstate, hotrunnerdesc, promotebox, hotpromotiondesc,
                 ll_evalue):
        PromoteFallbackPoint.__init__(self, jitstate, hotrunnerdesc,
                                      promotebox, hotpromotiondesc)
        self.ll_evalue = ll_evalue

    @specialize.arglltype(2)
    def prepare_fallbackinterp(self, fallbackinterp, value):
        value = bool(value)
        fallbackinterp.local_red.pop()   # remove the temporary raisedbox
        if value:
            # got an exception, register it on the fallbackinterp
            fallbackinterp.residual_ll_exception(self.ll_evalue)

    def prepare_compiler(self, interpreter, gv_value):
        # remove the temporary raisedbox
        interpreter.frame.local_boxes.pop()
        if gv_value.revealconst(lltype.Bool):
            # got an exception, register it on the interpreter
            interpreter.jitstate.residual_ll_exception(self.ll_evalue)


def hp_after_raisingop(jitstate, hotrunnerdesc, ll_evalue):
    gv_raised = jitstate.get_gv_op_raised()
    # XXX slightly hackish as well, we actually need gv_raised to be
    # in local_boxes to be passed along to the new block
    if gv_raised.is_const:
        if gv_raised.revealconst(lltype.Bool):
            jitstate.residual_ll_exception(ll_evalue)
        return
    assert not gv_raised.is_const
    raisedbox = rvalue.IntRedBox(gv_raised)
    jitstate.frame.local_boxes.append(raisedbox)
    
    hotpromotiondesc = hotrunnerdesc.bool_hotpromotiondesc
    fbp = AfterRaisingOpFallbackPoint(jitstate, hotrunnerdesc,
                                      raisedbox, hotpromotiondesc,
                                      ll_evalue)
    generate_fallback_code(fbp, hotpromotiondesc, raisedbox,
                           check_exceptions=False)
    # NB. check_exceptions is False because no exception should set
    # set now (the RGenOp's genraisingop cannot set an exception itself)
    assert 0, "unreachable"
