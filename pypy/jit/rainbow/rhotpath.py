"""
RPython support code for the hotpath policy.
"""

from pypy.jit.timeshifter import rtimeshift
from pypy.rlib.objectmodel import we_are_translated
from pypy.rpython.annlowlevel import cachedtype, base_ptr_lltype
from pypy.rpython.annlowlevel import llhelper
from pypy.rpython.lltypesystem import lltype, llmemory

import py
from pypy.tool.ansi_print import ansi_log
log = py.log.Producer('hotpath')
py.log.setconsumer('hotpath', ansi_log)


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

def leave_graph(interp):
    jitstate = interp.jitstate
    exceptiondesc = interp.exceptiondesc
    builder = jitstate.curbuilder
    #for virtualizable_box in jitstate.virtualizables:
    #    assert isinstance(virtualizable_box, rvalue.PtrRedBox)
    #    content = virtualizable_box.content
    #    assert isinstance(content, rcontainer.VirtualizableStruct)
    #    content.store_back(jitstate)        
    exceptiondesc.store_global_excdata(jitstate)
    jitstate.curbuilder.finish_and_return(interp.graphsigtoken, None)

def compile(interp):
    jitstate = interp.jitstate
    builder = jitstate.curbuilder
    builder.start_writing()
    try:
        try:
            interp.bytecode_loop()
        except GenerateReturn:
            pass
    except FinishedCompiling:
        pass
    else:
        leave_graph(interp)
    builder.end()
    builder.show_incremental_progress()

def report_compile_time_exception(e):
    if not we_are_translated():
        import sys, pdb, traceback
        msg = str(e)
        if msg: msg = ': ' + msg
        msg = e.__class__.__name__ + msg
        log.ERROR("*** compilation-time error ***")
        log.ERROR(msg)
        traceback.print_exc()
        print >> sys.stderr
        pdb.post_mortem(sys.exc_info()[2])
    # XXX I think compile-time errors don't have to be fatal
    # any more
    lloperation.llop.debug_fatalerror(
        lltype.Void, "compilation-time error %s" % e)

# ____________________________________________________________

class FinishedCompiling(Exception):
    pass

class GenerateReturn(Exception):
    pass

class MesurePoint(object):
    pass

class HotPromotionDesc:
    __metaclass__ = cachedtype

    def __init__(self, ERASED, interpreter, threshold):
        self.exceptiondesc = interpreter.exceptiondesc

        def ll_reach_fallback_point(fallback_point_ptr, value, framebase):
            try:
                promotion_point = _cast_base_ptr_to_promotion_point(
                    promotion_point_ptr)
                path = [None]
                root = promotion_point.promotion_path.follow_path(path)
                gv_value = root.rgenop.genconst(value)
                resuminginfo = ResumingInfo(promotion_point, gv_value, path)
                root.reach_fallback_point(resuminginfo)
                interpreter.portalstate.compile_more_functions()
            except Exception, e:
                report_compile_time_exception(e)
        self.ll_reach_fallback_point = ll_reach_fallback_point
        ll_reach_fallback_point._debugexc = True

        FUNCTYPE = lltype.FuncType([base_ptr_lltype(), ERASED,
                                    llmemory.Address], lltype.Void)
        FUNCPTRTYPE = lltype.Ptr(FUNCTYPE)
        self.FUNCPTRTYPE = FUNCPTRTYPE
        self.sigtoken = interpreter.rgenop.sigToken(FUNCTYPE)

        def get_gv_reach_fallback_point(builder):
            fnptr = llhelper(FUNCPTRTYPE, ll_reach_fallback_point)
            # ^^^ the llhelper cannot be attached on 'self' directly, because
            # the translator needs to see its construction done by RPython code
            return builder.rgenop.genconst(fnptr)
        self.get_gv_reach_fallback_point = get_gv_reach_fallback_point

    def _freeze_(self):
        return True


class FallbackPoint(object):
    falsepath_counter = 0     # -1 after this path was compiled
    truepath_counter = 0      # -1 after this path was compiled

    def __init__(self, jitstate, flexswitch, frameinfo):
        self.saved_jitstate = jitstate
        self.flexswitch = flexswitch
        self.frameinfo = frameinfo
        # ^^^ 'frameinfo' describes where the machine code stored all
        # its GenVars, so that we can fish these values to pass them
        # to the fallback interpreter

    # hack for testing: make the llinterpreter believe this is a Ptr to base
    # instance
    _TYPE = base_ptr_lltype()


def hotsplit(jitstate, hotpromotiondesc, switchbox):
    # produce a Bool flexswitch for now
    incoming = jitstate.enter_block()
    switchblock = rtimeshift.enter_next_block(jitstate, incoming)
    gv_switchvar = switchbox.genvar
    incoming_gv = [box.genvar for box in incoming]
    flexswitch, default_builder = jitstate.curbuilder.flexswitch(gv_switchvar,
                                                                 incoming_gv)
    jitstate.curbuilder = default_builder
    # default case of the switch:
    frameinfo = default_builder.get_frame_info(incoming_gv)
    fbp = FallbackPoint(jitstate, flexswitch, frameinfo)
    ll_fbp = fbp        # XXX doesn't translate
    gv_fbp = default_builder.rgenop.genconst(ll_fbp)
    gv_switchvar = switchbox.genvar
    gv_fnptr = hotpromotiondesc.get_gv_reach_fallback_point(default_builder)
    gv_framebase = default_builder.genop_get_frame_base()
    default_builder.genop_call(hotpromotiondesc.sigtoken,
                               gv_fnptr,
                               [gv_fbp, gv_switchvar, gv_framebase])
    # loop back to 'switchblock' unless an exception occurred
    # (only "real" run-time exceptions should arrive here, not
    # compile-time exceptions)
    exceptiondesc = hotpromotiondesc.exceptiondesc
    gv_exc_type = exceptiondesc.genop_get_exc_type(default_builder)
    gv_occurred = default_builder.genop_ptr_nonzero(
        exceptiondesc.exc_type_token, gv_exc_type)
    excpath_builder = default_builder.jump_if_true(gv_occurred, [])
    default_builder.finish_and_goto(incoming_gv, switchblock)

    jitstate.curbuilder = excpath_builder
    excpath_builder.start_writing()
    raise GenerateReturn

# ____________________________________________________________
# The fallback interp takes an existing suspended jitstate and
# actual values for the live red vars, and interprets the jitcode
# normally until it reaches the 'jit_merge_point' or raises.
