import operator, weakref
from pypy.annotation import model as annmodel
from pypy.rpython.lltypesystem import lltype, lloperation, llmemory
from pypy.jit.hintannotator.model import originalconcretetype
from pypy.jit.timeshifter import rvalue, rcontainer, rvirtualizable
from pypy.jit.timeshifter.greenkey import newgreendict, empty_key
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.unroll import unrolling_iterable
from pypy.rpython.annlowlevel import cachedtype, base_ptr_lltype
from pypy.rpython.annlowlevel import cast_instance_to_base_ptr
from pypy.rpython.annlowlevel import cast_base_ptr_to_instance, llhelper

FOLDABLE_GREEN_OPS = dict.fromkeys(lloperation.enum_foldable_ops())
FOLDABLE_GREEN_OPS['getfield'] = None
FOLDABLE_GREEN_OPS['getarrayitem'] = None
FOLDABLE_GREEN_OPS['getinteriorfield'] = None

NULL_OBJECT = base_ptr_lltype()._defl()

debug_view = lloperation.llop.debug_view
debug_print = lloperation.llop.debug_print
debug_pdb = lloperation.llop.debug_pdb


# ____________________________________________________________
# emit ops


class OpDesc(object):
    """
    Description of a low-level operation
    that can be passed around to low level helpers
    to inform op generation
    """
    canraise = False

    def _freeze_(self):
        return True

    def __init__(self, RGenOp, opname, ARGS, RESULT):
        self.RGenOp = RGenOp
        self.opname = opname
        self.llop = lloperation.LL_OPERATIONS[opname]
        self.nb_args = len(ARGS)
        self.ARGS = ARGS
        self.RESULT = RESULT
        self.whatever_result = RESULT._defl()
        self.redboxcls = rvalue.ll_redboxcls(RESULT)
        self.canfold = self.llop.canfold
        self.tryfold = self.llop.tryfold
        if self.tryfold and self.llop.canraise:
            self.canraise = True
            self.gv_True  = RGenOp.constPrebuiltGlobal(True)
            self.gv_False = RGenOp.constPrebuiltGlobal(False)

    def __getattr__(self, name): # .ARGx -> .ARGS[x]
        if name.startswith('ARG'):
            index = int(name[3:])
            return self.ARGS[index]
        else:
            raise AttributeError("don't know about %r in OpDesc" % name)

    def compact_repr(self): # goes in ll helper names
        return self.opname.upper()

_opdesc_cache = {}

def make_opdesc(RGenOp, opname, args_s, s_result):
    op_key = (RGenOp, opname,
              tuple([originalconcretetype(s_arg) for s_arg in args_s]),
              originalconcretetype(s_result))
    try:
        return _opdesc_cache[op_key]
    except KeyError:
        opdesc = OpDesc(*op_key)
        _opdesc_cache[op_key] = opdesc
        return opdesc

def ll_gen1(opdesc, jitstate, argbox):
    ARG0 = opdesc.ARG0
    RESULT = opdesc.RESULT
    opname = opdesc.opname
    if opdesc.tryfold and argbox.is_constant():
        arg = rvalue.ll_getvalue(argbox, ARG0)
        res = opdesc.llop(RESULT, arg)
        return rvalue.ll_fromvalue(jitstate, res)
    gv_arg = argbox.getgenvar(jitstate)
    genvar = jitstate.curbuilder.genop1(opdesc.opname, gv_arg)
    return opdesc.redboxcls(genvar)

def ll_gen1_canraise(opdesc, jitstate, argbox):
    ARG0 = opdesc.ARG0
    RESULT = opdesc.RESULT
    opname = opdesc.opname
    if opdesc.tryfold and argbox.is_constant():
        arg = rvalue.ll_getvalue(argbox, ARG0)
        try:
            res = opdesc.llop(RESULT, arg)
        except Exception:   # shouldn't raise anything unexpected
            res = opdesc.whatever_result
            gv_flag = opdesc.gv_True
        else:
            gv_flag = opdesc.gv_False
        jitstate.gv_op_raised = gv_flag
        return rvalue.ll_fromvalue(jitstate, res)
    gv_arg = argbox.getgenvar(jitstate)
    genvar, gv_raised = jitstate.curbuilder.genraisingop1(opdesc.opname,
                                                          gv_arg)
    jitstate.gv_op_raised = gv_raised    # for split_raisingop()
    return opdesc.redboxcls(genvar)

def ll_gen2(opdesc, jitstate, argbox0, argbox1):
    ARG0 = opdesc.ARG0
    ARG1 = opdesc.ARG1
    RESULT = opdesc.RESULT
    opname = opdesc.opname
    if opdesc.tryfold and argbox0.is_constant() and argbox1.is_constant():
        # const propagate
        arg0 = rvalue.ll_getvalue(argbox0, ARG0)
        arg1 = rvalue.ll_getvalue(argbox1, ARG1)
        return rvalue.ll_fromvalue(jitstate, opdesc.llop(RESULT, arg0, arg1))
    gv_arg0 = argbox0.getgenvar(jitstate)
    gv_arg1 = argbox1.getgenvar(jitstate)
    genvar = jitstate.curbuilder.genop2(opdesc.opname, gv_arg0, gv_arg1)
    return opdesc.redboxcls(genvar)

def ll_gen2_canraise(opdesc, jitstate, argbox0, argbox1):
    ARG0 = opdesc.ARG0
    ARG1 = opdesc.ARG1
    RESULT = opdesc.RESULT
    opname = opdesc.opname
    if opdesc.tryfold and argbox0.is_constant() and argbox1.is_constant():
        # const propagate
        arg0 = rvalue.ll_getvalue(argbox0, ARG0)
        arg1 = rvalue.ll_getvalue(argbox1, ARG1)
        try:
            res = opdesc.llop(RESULT, arg0, arg1)
        except Exception:   # shouldn't raise anything unexpected
            res = opdesc.whatever_result
            gv_flag = opdesc.gv_True
        else:
            gv_flag = opdesc.gv_False
        jitstate.gv_op_raised = gv_flag
        return rvalue.ll_fromvalue(jitstate, res)
    gv_arg0 = argbox0.getgenvar(jitstate)
    gv_arg1 = argbox1.getgenvar(jitstate)
    genvar, gv_raised = jitstate.curbuilder.genraisingop2(opdesc.opname,
                                                          gv_arg0, gv_arg1)
    jitstate.gv_op_raised = gv_raised    # for split_raisingop()
    return opdesc.redboxcls(genvar)

def genmalloc_varsize(jitstate, contdesc, sizebox):
    gv_size = sizebox.getgenvar(jitstate)
    alloctoken = contdesc.varsizealloctoken
    genvar = jitstate.curbuilder.genop_malloc_varsize(alloctoken, gv_size)
    # XXX MemoryError handling
    return rvalue.PtrRedBox(genvar, known_nonzero=True)

def gengetfield(jitstate, deepfrozen, fielddesc, argbox):
    assert isinstance(argbox, rvalue.AbstractPtrRedBox)
    if (fielddesc.immutable or deepfrozen) and argbox.is_constant():
        try:
            resgv = fielddesc.perform_getfield(
                jitstate.curbuilder.rgenop, argbox.getgenvar(jitstate))
        except rcontainer.SegfaultException:
            pass
        else:
            return fielddesc.makebox(jitstate, resgv)
    return argbox.op_getfield(jitstate, fielddesc)

def gensetfield(jitstate, fielddesc, destbox, valuebox):
    assert isinstance(destbox, rvalue.AbstractPtrRedBox)
    destbox.op_setfield(jitstate, fielddesc, valuebox)

def ll_gengetsubstruct(jitstate, fielddesc, argbox):
    assert isinstance(argbox, rvalue.PtrRedBox)
    if argbox.is_constant():
        ptr = rvalue.ll_getvalue(argbox, fielddesc.PTRTYPE)
        if ptr:    # else don't constant-fold - we'd get a bogus pointer
            res = getattr(ptr, fielddesc.fieldname)
            return rvalue.ll_fromvalue(jitstate, res)
    return argbox.op_getsubstruct(jitstate, fielddesc)

def gengetarrayitem(jitstate, deepfrozen, fielddesc, argbox, indexbox):
    if ((fielddesc.immutable or deepfrozen) and argbox.is_constant()
                                            and indexbox.is_constant()):
        try:
            resgv = fielddesc.perform_getarrayitem(
                jitstate.curbuilder.rgenop, argbox.getgenvar(jitstate),
                indexbox.getgenvar(jitstate))
        except rcontainer.SegfaultException:
            pass
        else:
            return fielddesc.makebox(jitstate, resgv)
    genvar = jitstate.curbuilder.genop_getarrayitem(
        fielddesc.arraytoken,
        argbox.getgenvar(jitstate),
        indexbox.getgenvar(jitstate))
                                                    
    return fielddesc.makebox(jitstate, genvar)

def ll_gengetarraysubstruct(jitstate, fielddesc, argbox, indexbox):
    if argbox.is_constant() and indexbox.is_constant():
        array = rvalue.ll_getvalue(argbox, fielddesc.PTRTYPE)
        index = rvalue.ll_getvalue(indexbox, lltype.Signed)
        if array and 0 <= index < len(array):  # else don't constant-fold
            res = array[index]
            return rvalue.ll_fromvalue(jitstate, res)
    genvar = jitstate.curbuilder.genop_getarraysubstruct(
        fielddesc.arraytoken,
        argbox.getgenvar(jitstate),
        indexbox.getgenvar(jitstate))
                                                    
    return fielddesc.makebox(jitstate, genvar)


def gensetarrayitem(jitstate, fielddesc, destbox, indexbox, valuebox):
    genvar = jitstate.curbuilder.genop_setarrayitem(
        fielddesc.arraytoken,
        destbox.getgenvar(jitstate),
        indexbox.getgenvar(jitstate),
        valuebox.getgenvar(jitstate)
        )

def gengetarraysize(jitstate, fielddesc, argbox):
    if argbox.is_constant():
        try:
            resgv = fielddesc.perform_getarraysize(
                jitstate.curbuilder.rgenop, argbox.getgenvar(jitstate))
        except rcontainer.SegfaultException:
            pass
        else:
            return rvalue.redboxbuilder_int(resgv)
    genvar = jitstate.curbuilder.genop_getarraysize(
        fielddesc.arraytoken,
        argbox.getgenvar(jitstate))
    return rvalue.IntRedBox(genvar)

def genptrnonzero(jitstate, argbox, reverse):
    assert isinstance(argbox, rvalue.AbstractPtrRedBox)
    if argbox.is_constant():
        addr = rvalue.ll_getvalue(argbox, jitstate.ts.ROOT_TYPE)
        return rvalue.ll_fromvalue(jitstate, bool(addr) ^ reverse)
    builder = jitstate.curbuilder
    if argbox.known_nonzero:
        gv_res = builder.rgenop.genconst(True ^ reverse)
    else:
        gv_addr = argbox.getgenvar(jitstate)
        if reverse:
            gv_res = jitstate.ts.genop_ptr_iszero(builder, argbox, gv_addr)
        else:
            gv_res = jitstate.ts.genop_ptr_nonzero(builder, argbox, gv_addr)
    return rvalue.IntRedBox(gv_res)

def genptreq(jitstate, argbox0, argbox1, reverse):
    assert isinstance(argbox0, rvalue.PtrRedBox)
    assert isinstance(argbox1, rvalue.PtrRedBox)
    builder = jitstate.curbuilder
    if argbox0.is_constant() and argbox1.is_constant():
        addr0 = rvalue.ll_getvalue(argbox0, llmemory.Address)
        addr1 = rvalue.ll_getvalue(argbox1, llmemory.Address)
        return rvalue.ll_fromvalue(jitstate, (addr0 == addr1) ^ reverse)
    if argbox0.content is not None:
        resultbox = argbox0.content.op_ptreq(jitstate, argbox1, reverse)
        if resultbox is not None:
            return resultbox
    if argbox1.content is not None:
        resultbox = argbox1.content.op_ptreq(jitstate, argbox0, reverse)
        if resultbox is not None:
            return resultbox
    gv_addr0 = argbox0.getgenvar(jitstate)
    gv_addr1 = argbox1.getgenvar(jitstate)
    if reverse:
        gv_res = builder.genop_ptr_ne(gv_addr0, gv_addr1)
    else:
        gv_res = builder.genop_ptr_eq(gv_addr0, gv_addr1)
    return rvalue.IntRedBox(gv_res)

# ____________________________________________________________
# other jitstate/graph level operations

def enter_next_block(jitstate, incoming):
    linkargs = []
    for redbox in incoming:
        assert not redbox.genvar.is_const
        linkargs.append(redbox.genvar)
    newblock = jitstate.curbuilder.enter_next_block(linkargs)
    for i in range(len(incoming)):
        incoming[i].genvar = linkargs[i]
    return newblock

class Resumer(object):
    def resume(self, jitstate, resumepoint):
        raise NotImplementedError("abstract base class")

return_marker = Resumer()

def start_new_block(states_dic, jitstate, key, global_resumer, index=-1):
    memo = rvalue.freeze_memo()
    frozen = jitstate.freeze(memo)
    memo = rvalue.exactmatch_memo()
    outgoingvarboxes = []
    res = frozen.exactmatch(jitstate, outgoingvarboxes, memo)
    assert res, "exactmatch() failed"
    cleanup_partial_data(memo.partialdatamatch)
    newblock = enter_next_block(jitstate, outgoingvarboxes)
    if index < 0:
        states_dic[key].append((frozen, newblock))
    else:
        states_dic[key][index] = (frozen, newblock)
        
    if global_resumer is not None and global_resumer is not return_marker:
        assert jitstate.get_resuming() is None
        jitstate.curbuilder.log('start_new_block %s' % (key,))
        greens_gv = jitstate.greens
        rgenop = jitstate.curbuilder.rgenop
        node = PromotionPathRoot(greens_gv, rgenop,
                                 frozen, newblock,
                                 global_resumer)
        dispatchqueue = jitstate.frame.dispatchqueue
        assert dispatchqueue.split_chain is None
        dispatchqueue.clearlocalcaches()
        jitstate.promotion_path = PromotionPathMergesToSee(node, 0)
        #debug_print(lltype.Void, "PROMOTION ROOT")

def retrieve_jitstate_for_merge(states_dic, jitstate, key, global_resumer,
                                force_merge=False):
    # global_resumer is always None, just not for global merge points
    if jitstate.virtualizables:
        jitstate.enter_block_sweep_virtualizables()
    if key not in states_dic:
        states_dic[key] = []
        start_new_block(states_dic, jitstate, key, global_resumer)
        return False   # continue

    states = states_dic[key]
    for i in range(len(states) -1, -1, -1):
        frozen, oldblock =  states[i]
        memo = rvalue.exactmatch_memo(force_merge)
        outgoingvarboxes = []
        
        try:
            match = frozen.exactmatch(jitstate, outgoingvarboxes, memo)
        except rvalue.DontMerge:
            continue
        if match:
            linkargs = []
            for box in outgoingvarboxes:
                linkargs.append(box.getgenvar(jitstate))
            jitstate.curbuilder.finish_and_goto(linkargs, oldblock)
            return True    # finished
        # A mergable blook found
        # We need a more general block.  Do it by generalizing all the
        # redboxes from outgoingvarboxes, by making them variables.
        # Then we make a new block based on this new state.
        cleanup_partial_data(memo.partialdatamatch)
        forget_nonzeroness = memo.forget_nonzeroness
        replace_memo = rvalue.copy_memo()
        for box in outgoingvarboxes:
            box.forcevar(jitstate, replace_memo, box in forget_nonzeroness)
        if replace_memo.boxes:
            jitstate.replace(replace_memo)
        start_new_block(states_dic, jitstate, key, global_resumer, index=i)
        if global_resumer is None:
            merge_generalized(jitstate)
        return False       # continue

    # No mergable states found, make a new.
    start_new_block(states_dic, jitstate, key, global_resumer)
    return False   

def cleanup_partial_data(partialdatamatch):
    # remove entries from PartialDataStruct unless they matched
    # their frozen equivalent
    for box, keep in partialdatamatch.iteritems():
        content = box.content
        if isinstance(content, rcontainer.PartialDataStruct):
            box.content = content.cleanup_partial_data(keep)

def merge_generalized(jitstate):
    resuming = jitstate.get_resuming()
    if resuming is None:
        node = jitstate.promotion_path
        if node is None:
            return    # not recording paths at all
        while not node.cut_limit:
            node = node.next
        dispatchqueue = jitstate.frame.dispatchqueue
        count = dispatchqueue.mergecounter + 1
        dispatchqueue.mergecounter = count
        node = PromotionPathMergesToSee(node, count)
        #debug_print(lltype.Void, "MERGE", count)
        jitstate.promotion_path = node
    else:
        if resuming.mergesleft != MC_IGNORE_UNTIL_RETURN:
            assert resuming.mergesleft > 0
            resuming.mergesleft -= 1

def guard_global_merge(jitstate, resumepoint):
    jitstate.pause()
    dispatchqueue = jitstate.frame.dispatchqueue
    jitstate.next = dispatchqueue.global_merge_chain
    dispatchqueue.global_merge_chain = jitstate
    jitstate.resumepoint = resumepoint

def split(jitstate, switchredbox, resumepoint, *greens_gv):
    exitgvar = switchredbox.getgenvar(jitstate)
    if exitgvar.is_const:
        return exitgvar.revealconst(lltype.Bool)
    else:
        return split_nonconstantcase(jitstate, exitgvar, resumepoint,
                                     switchredbox, False, list(greens_gv))

def split_nonconstantcase(jitstate, exitgvar, resumepoint,
                          condbox, reverse, greens_gv, ll_evalue=NULL_OBJECT):
    resuming = jitstate.get_resuming()
    if resuming is not None and resuming.mergesleft == 0:
        node = resuming.path.pop()
        assert isinstance(node, PromotionPathSplit)
        if condbox is not None:
            ok = condbox.learn_boolvalue(jitstate, node.answer ^ reverse)
            assert ok
        return node.answer
    later_gv = jitstate.get_locals_gv() # alive gvs on the later path
    if ll_evalue:    # special case - we want jump_if_true in split_raisingop
        later_builder = jitstate.curbuilder.jump_if_true(exitgvar, later_gv)
    else:
        later_builder = jitstate.curbuilder.jump_if_false(exitgvar, later_gv)
    memo = rvalue.copy_memo()
    jitstate2 = jitstate.split(later_builder, resumepoint, greens_gv, memo)
    if condbox is not None:
        ok = condbox.learn_boolvalue(jitstate, True ^ reverse)
        assert ok
        try:
            copybox = memo.boxes[condbox]
        except KeyError:
            pass
        else:
            ok = copybox.learn_boolvalue(jitstate2, reverse)
            assert ok
    if ll_evalue:
        jitstate2.residual_ll_exception(ll_evalue)
    if resuming is None:
        node = jitstate.promotion_path
        jitstate2.promotion_path = PromotionPathNo(node)
        jitstate .promotion_path = PromotionPathYes(node)
    return True

def split_raisingop(jitstate, resumepoint, ll_evalue, *greens_gv):
    exitgvar = jitstate.get_gv_op_raised()
    if exitgvar.is_const:
        gotexc = exitgvar.revealconst(lltype.Bool)
    else:
        gotexc = not split_nonconstantcase(jitstate, exitgvar, resumepoint,
                                           None, False, list(greens_gv),
                                           ll_evalue)
    if gotexc:
        jitstate.residual_ll_exception(ll_evalue)

def collect_split(jitstate_chain, resumepoint, greens_gv):
    # YYY split to avoid over-specialization
    # assumes that the head of the jitstate_chain is ready for writing,
    # and all the other jitstates in the chain are paused
    pending = jitstate_chain
    resuming = jitstate_chain.get_resuming()
    if resuming is not None and resuming.mergesleft == 0:
        node = resuming.path.pop()
        assert isinstance(node, PromotionPathCollectSplit)
        for i in range(node.n):
            pending = pending.next
        pending.greens.extend(greens_gv)
        if pending.returnbox is not None:
            pending.frame.local_boxes.append(getreturnbox(pending))
        pending.next = None
        start_writing(pending, jitstate_chain)
        return pending

    n = 0
    while True:
        jitstate = pending
        pending = pending.next
        jitstate.greens.extend(greens_gv)   # item 0 is the return value
        if jitstate.returnbox is not None:
            jitstate.frame.local_boxes.append(getreturnbox(jitstate))
        jitstate.resumepoint = resumepoint
        if resuming is None:
            node = jitstate.promotion_path
            jitstate.promotion_path = PromotionPathCollectSplit(node, n)
            n += 1
        if pending is None:
            break

    dispatchqueue = jitstate_chain.frame.dispatchqueue
    jitstate.next = dispatchqueue.split_chain
    dispatchqueue.split_chain = jitstate_chain.next
    jitstate_chain.next = None
    return jitstate_chain
    # XXX obscurity++ above

def reverse_split_queue(dispatchqueue):
    newchain = None
    while dispatchqueue.split_chain:
        jitstate = dispatchqueue.split_chain
        dispatchqueue.split_chain = jitstate.next
        jitstate.next = newchain
        newchain = jitstate
    dispatchqueue.split_chain = newchain

def dispatch_next(dispatchqueue):
    if dispatchqueue.split_chain is not None:
        jitstate = dispatchqueue.split_chain
        dispatchqueue.split_chain = jitstate.next
        jitstate.curbuilder.start_writing()
        return jitstate
    elif dispatchqueue.global_merge_chain is not None:
        jitstate = dispatchqueue.global_merge_chain
        dispatchqueue.global_merge_chain = jitstate.next
        jitstate.curbuilder.start_writing()
        return jitstate
    else:
        return None

def getresumepoint(jitstate):
    if jitstate is None:
        return -1    # done
    else:
        return jitstate.resumepoint

def save_locals(jitstate, *redboxes):
    redboxes = list(redboxes)
    assert None not in redboxes
    jitstate.frame.local_boxes = redboxes

def save_greens(jitstate, greens_gv):
    jitstate.greens = list(greens_gv)

def getlocalbox(jitstate, i):
    return jitstate.frame.local_boxes[i]

def ll_getgreenbox(jitstate, i, T):
    return jitstate.greens[i].revealconst(T)

def getreturnbox(jitstate):
    retbox = jitstate.returnbox
    jitstate.returnbox = None
    return retbox

def getexctypebox(jitstate):
    return jitstate.exc_type_box

def getexcvaluebox(jitstate):
    return jitstate.exc_value_box

def setexctypebox(jitstate, box):
    jitstate.exc_type_box = box

def setexcvaluebox(jitstate, box):
    jitstate.exc_value_box = box

def setexception(jitstate, typebox, valuebox):
    assert isinstance(typebox, rvalue.PtrRedBox)
    assert isinstance(valuebox, rvalue.PtrRedBox)
    ok1 = typebox .learn_nonzeroness(jitstate, True)
    ok2 = valuebox.learn_nonzeroness(jitstate, True)
    assert ok1 & ok2       # probably... maybe it's false but it would be
                           # nice to see what kind of contrieved code can
                           # make this fail :-)
    jitstate.exc_type_box = typebox
    jitstate.exc_value_box = valuebox

def save_return(jitstate):
    # add 'jitstate' to the chain of return-jitstates
    jitstate.pause()
    dispatchqueue = jitstate.frame.dispatchqueue
    jitstate.next = dispatchqueue.return_chain
    dispatchqueue.return_chain = jitstate

def learn_nonzeroness(jitstate, ptrbox, nonzeroness):
    assert isinstance(ptrbox, rvalue.PtrRedBox)
    ptrbox.learn_nonzeroness(jitstate, nonzeroness)

##def ll_gvar_from_redbox(jitstate, redbox):
##    return redbox.getgenvar(jitstate)

##def ll_gvar_from_constant(jitstate, ll_value):
##    return jitstate.curbuilder.rgenop.genconst(ll_value)


def gen_residual_call(jitstate, calldesc, funcbox, argboxes):
    builder = jitstate.curbuilder
    gv_funcbox = funcbox.getgenvar(jitstate)
    args_gv = [argbox.getgenvar(jitstate) for argbox in argboxes]
    jitstate.prepare_for_residual_call()
    gv_result = builder.genop_call(calldesc.sigtoken, gv_funcbox, args_gv)
    return calldesc.redboxbuilder(gv_result)

def gvflags_after_residual_call(jitstate, exceptiondesc, check_forced):
    builder = jitstate.curbuilder
    if check_forced:
        gv_flags = jitstate.check_forced_after_residual_call()
    else:
        gv_flags = None
    if exceptiondesc:
        if exceptiondesc.lazy_exception_path:
            gv_occurred = exceptiondesc.gen_exc_occurred(builder)
            gv_flag = builder.genop1("cast_bool_to_int", gv_occurred)
            if gv_flags is None:
                gv_flags = gv_flag
            else:
                gv_flags = builder.genop2("int_or", gv_flags, gv_flag)
        else:
            assert gv_flags is None
            exceptiondesc.fetch_global_excdata(jitstate)
    return gv_flags

def after_residual_call(jitstate, exceptiondesc, check_forced):
    gv_flags = gvflags_after_residual_call(jitstate, exceptiondesc,
                                           check_forced)
    builder = jitstate.curbuilder
    if gv_flags is None:
        gv_flags = builder.rgenop.constPrebuiltGlobal(0)
    return rvalue.IntRedBox(gv_flags)

def residual_fetch(jitstate, exceptiondesc, check_forced, flagsbox):
    flags = rvalue.ll_getvalue(flagsbox, lltype.Signed)
    if flags & 1:   # an exception occurred
        exceptiondesc.fetch_global_excdata(jitstate, known_occurred=True)
    if check_forced:
        shapemask = flags & ~ 1
        jitstate.reshape(shapemask)

def oopspec_was_residual(jitstate):
    res = jitstate.generated_oop_residual_can_raise
    jitstate.generated_oop_residual_can_raise = False
    return res


class ResumingInfo(object):
    def __init__(self, promotion_point, gv_value, path):
        node = PromotionPathPromote(promotion_point.promotion_path,
                                    promotion_point, gv_value)
        path[0] = node
        self.promotion_point = promotion_point
        self.path = path
        self.mergesleft = 0

    def merges_to_see(self):
        node = self.path[-1]
        if isinstance(node, PromotionPathMergesToSee):
            self.mergesleft = node.count
            del self.path[-1]
        else:
            self.mergesleft = MC_IGNORE_UNTIL_RETURN

    def leave_call(self, dispatchqueue):
        parent_mergesleft = dispatchqueue.mergecounter
        if parent_mergesleft == 0:
            node = self.path.pop()
            assert isinstance(node, PromotionPathBackFromReturn)
            self.merges_to_see()
        elif parent_mergesleft == MC_CALL_NOT_TAKEN:
            self.mergesleft = 0
        else:
            self.mergesleft = parent_mergesleft


class PromotionPoint(object):
    def __init__(self, flexswitch, incoming_gv, promotion_path):
        assert promotion_path is not None
        self.flexswitch = flexswitch
        self.incoming_gv = incoming_gv
        self.promotion_path = promotion_path

    # hack for testing: make the llinterpreter believe this is a Ptr to base
    # instance
    _TYPE = base_ptr_lltype()

class AbstractPromotionPath(object):
    cut_limit = False

class PromotionPathRoot(AbstractPromotionPath):
    cut_limit = True

    def __init__(self, greens_gv, rgenop, frozen, replayableblock, global_resumer):
        self.greens_gv = greens_gv
        self.rgenop = rgenop
        self.frozen = frozen
        self.replayableblock = replayableblock
        self.global_resumer = global_resumer

    def follow_path(self, path):
        return self

    def continue_compilation(self, resuminginfo):
        incoming = []
        memo = rvalue.unfreeze_memo()
        jitstate = self.frozen.unfreeze(incoming, memo)
        builder, vars_gv = self.rgenop.replay(self.replayableblock)
        for i in range(len(incoming)):
            assert incoming[i].genvar is None
            incoming[i].genvar = vars_gv[i]
        jitstate.curbuilder = builder
        jitstate.greens = self.greens_gv
        assert jitstate.frame.backframe is None
        resuminginfo.merges_to_see()
        self.global_resumer.resume(jitstate, resuminginfo)
        builder.show_incremental_progress()

class PromotionPathNode(AbstractPromotionPath):
    def __init__(self, next):
        self.next = next
    def follow_path(self, path):
        path.append(self)
        return self.next.follow_path(path)

class PromotionPathSplit(PromotionPathNode):
    pass

class PromotionPathYes(PromotionPathSplit):
    answer = True

class PromotionPathNo(PromotionPathSplit):
    answer = False

class PromotionPathCollectSplit(PromotionPathNode):

    def __init__(self, next, n):
        self.next = next
        self.n = n

class PromotionPathCallNotTaken(PromotionPathNode):
    pass

class PromotionPathPromote(PromotionPathNode):
    cut_limit = True

    def __init__(self, next, promotion_point, gv_value):
        self.next = next
        self.promotion_point = promotion_point
        self.gv_value = gv_value

class PromotionPathCall(PromotionPathNode):
    cut_limit = True

class PromotionPathBackFromReturn(PromotionPathNode):
    cut_limit = True

class PromotionPathMergesToSee(PromotionPathNode):
    def __init__(self, next, count):
        self.next = next
        self.count = count

MC_IGNORE_UNTIL_RETURN = -1
MC_CALL_NOT_TAKEN      = -2

# for testing purposes
def _cast_base_ptr_to_promotion_point(ptr):
    if we_are_translated():
        return cast_base_ptr_to_instance(PromotionPoint, ptr)
    else:
        return ptr

def _cast_promotion_point_to_base_ptr(instance):
    assert isinstance(instance, PromotionPoint)
    if we_are_translated():
        return cast_instance_to_base_ptr(instance)
    else:
        return instance


class PromotionDesc:
    __metaclass__ = cachedtype

    def __init__(self, ERASED, interpreter):
        self.exceptiondesc = interpreter.exceptiondesc

        def ll_continue_compilation(promotion_point_ptr, value):
            try:
                promotion_point = _cast_base_ptr_to_promotion_point(
                    promotion_point_ptr)
                path = [None]
                root = promotion_point.promotion_path.follow_path(path)
                gv_value = root.rgenop.genconst(value)
                resuminginfo = ResumingInfo(promotion_point, gv_value, path)
                root.continue_compilation(resuminginfo)
                interpreter.portalstate.compile_more_functions()
            except Exception, e:
                if not we_are_translated():
                    import sys, pdb
                    print >> sys.stderr, "\n*** Error in ll_continue_compilation ***"
                    print >> sys.stderr, e
                    pdb.post_mortem(sys.exc_info()[2])
                lloperation.llop.debug_fatalerror(
                    lltype.Void, "compilation-time error %s" % e)
        self.ll_continue_compilation = ll_continue_compilation
        ll_continue_compilation._debugexc = True

        ts = interpreter.ts
        FUNCTYPE, FUNCPTRTYPE = ts.get_FuncType([base_ptr_lltype(), ERASED], lltype.Void)
        self.FUNCPTRTYPE = FUNCPTRTYPE
        self.sigtoken = interpreter.rgenop.sigToken(FUNCTYPE)

        def get_gv_continue_compilation(builder):
            fnptr = llhelper(FUNCPTRTYPE, ll_continue_compilation)
            # ^^^ the llhelper cannot be attached on 'self' directly, because
            # the translator needs to see its construction done by RPython code
            return builder.rgenop.genconst(fnptr)
        self.get_gv_continue_compilation = get_gv_continue_compilation

    def _freeze_(self):
        return True

def promote(jitstate, promotebox, promotiondesc):
    builder = jitstate.curbuilder
    gv_switchvar = promotebox.getgenvar(jitstate)
    if gv_switchvar.is_const:
        return False
    else:
        incoming = jitstate.enter_block_sweep_virtualizables()
        switchblock = enter_next_block(jitstate, incoming)
        gv_switchvar = promotebox.genvar
        incoming_gv = [box.genvar for box in incoming]
        flexswitch, default_builder = builder.flexswitch(gv_switchvar,
                                                         incoming_gv)
        resuming = jitstate.get_resuming()
        if resuming is None:
            jitstate.curbuilder = default_builder
            # default case of the switch:
            pm = PromotionPoint(flexswitch, incoming_gv,
                                jitstate.promotion_path)
            #debug_print(lltype.Void, "PROMOTE")
            ll_pm = _cast_promotion_point_to_base_ptr(pm)
            gv_pm = default_builder.rgenop.genconst(ll_pm)
            gv_switchvar = promotebox.genvar
            exceptiondesc = promotiondesc.exceptiondesc
            gv_exc_type  = exceptiondesc.genop_get_exc_type (default_builder)
            gv_exc_value = exceptiondesc.genop_get_exc_value(default_builder)
            exceptiondesc.genop_set_exc_type (default_builder,
                                              exceptiondesc.gv_null_exc_type )
            exceptiondesc.genop_set_exc_value(default_builder,
                                              exceptiondesc.gv_null_exc_value)
            gv_cc = promotiondesc.get_gv_continue_compilation(default_builder)
            default_builder.genop_call(promotiondesc.sigtoken,
                                       gv_cc,
                                       [gv_pm, gv_switchvar])
            exceptiondesc.genop_set_exc_type (default_builder, gv_exc_type )
            exceptiondesc.genop_set_exc_value(default_builder, gv_exc_value)
            linkargs = []
            for box in incoming:
                linkargs.append(box.getgenvar(jitstate))
            default_builder.finish_and_goto(linkargs, switchblock)
            return True
        else:
            assert jitstate.promotion_path is None
            if resuming.mergesleft != 0:
                default_builder.pause_writing([])
                return True

            promotenode = resuming.path.pop()
            assert isinstance(promotenode, PromotionPathPromote)
            #debug_view(lltype.Void, promotenode, resuming, incoming)
            pm = promotenode.promotion_point
            assert pm.promotion_path is promotenode.next

            # clear the complete state of dispatch queues
            f = jitstate.frame
            while f is not None:
                f.dispatchqueue.clear()
                f = f.backframe

            if len(resuming.path) == 0:
                incoming_gv = pm.incoming_gv
                for i in range(len(incoming)):
                    assert not incoming[i].genvar.is_const
                    incoming[i].genvar = incoming_gv[i]
                flexswitch = pm.flexswitch
                promotebox.setgenvar(promotenode.gv_value)
                jitstate.clear_resuming()
                node = PromotionPathMergesToSee(promotenode, 0)
                jitstate.promotion_path = node
            else:
                resuming.merges_to_see()
                promotebox.setgenvar(promotenode.gv_value)
                
            newbuilder = flexswitch.add_case(promotenode.gv_value)
            jitstate.curbuilder = newbuilder
            return False

# ____________________________________________________________

class DispatchQueue(object):
    resuming = None

    def __init__(self, num_local_caches=0):
        self.split_chain = None
        self.global_merge_chain = None
        self.return_chain = None
        self.num_local_caches = num_local_caches
        self.clearlocalcaches()

    def clearlocalcaches(self):
        self.mergecounter = 0
        self.local_caches = [newgreendict()
                                 for i in range(self.num_local_caches)]

    def clear(self):
        self.__init__(self.num_local_caches)

def build_dispatch_subclass(attrnames):
    py.test.skip("no longer exists")


class FrozenVirtualFrame(object):
    fz_backframe = None
    #fz_local_boxes = ... set by freeze()

    def exactmatch(self, vframe, outgoingvarboxes, memo):
        self_boxes = self.fz_local_boxes
        live_boxes = vframe.local_boxes
        fullmatch = True
        for i in range(len(self_boxes)):
            if not self_boxes[i].exactmatch(live_boxes[i],
                                            outgoingvarboxes,
                                            memo):
                fullmatch = False
        if self.fz_backframe is not None:
            assert vframe.backframe is not None
            if not self.fz_backframe.exactmatch(vframe.backframe,
                                                outgoingvarboxes,
                                                memo):
                fullmatch = False
        else:
            assert vframe.backframe is None
        return fullmatch

    def unfreeze(self, incomingvarboxes, memo):
        local_boxes = []
        for fzbox in self.fz_local_boxes:
            local_boxes.append(fzbox.unfreeze(incomingvarboxes, memo))
        if self.fz_backframe is not None:
            backframe = self.fz_backframe.unfreeze(incomingvarboxes, memo)
        else:
            backframe = None
        vframe = VirtualFrame(backframe, None) # dispatch queue to be patched
        vframe.local_boxes = local_boxes
        return vframe


class FrozenJITState(object):
    #fz_frame = ...           set by freeze()
    #fz_exc_type_box = ...    set by freeze()
    #fz_exc_value_box = ...   set by freeze()
    #fz_virtualizables = ...  set by freeze()

    def exactmatch(self, jitstate, outgoingvarboxes, memo):
        if not memo.force_merge:
            null1 = self.fz_exc_type_box.is_constant_nullptr()
            box = jitstate.exc_type_box
            null2 = (box.is_constant() and
                     not rvalue.ll_getvalue(box, jitstate.ts.ROOT_TYPE))
            if null1 != null2:
                raise rvalue.DontMerge # a jit-with-exc. and a jit-without-exc.

        fullmatch = True
        if not self.fz_frame.exactmatch(jitstate.frame,
                                        outgoingvarboxes,
                                        memo):
            fullmatch = False
        if not self.fz_exc_type_box.exactmatch(jitstate.exc_type_box,
                                               outgoingvarboxes,
                                               memo):
            fullmatch = False
        if not self.fz_exc_value_box.exactmatch(jitstate.exc_value_box,
                                                outgoingvarboxes,
                                                memo):
            fullmatch = False
        return fullmatch

    def unfreeze(self, incomingvarboxes, memo):
        frame         = self.fz_frame        .unfreeze(incomingvarboxes, memo)
        exc_type_box  = self.fz_exc_type_box .unfreeze(incomingvarboxes, memo)
        exc_value_box = self.fz_exc_value_box.unfreeze(incomingvarboxes, memo)
        virtualizables = []
        for fz_virtualizable_box in self.fz_virtualizables:
            virtualizable_box = fz_virtualizable_box.unfreeze(incomingvarboxes,
                                                              memo)
            assert isinstance(virtualizable_box, rvalue.PtrRedBox)
            virtualizables.append(virtualizable_box)
        return JITState(None, frame, exc_type_box, exc_value_box, self.ts,
                        virtualizables=virtualizables)


class VirtualFrame(object):

    def __init__(self, backframe, dispatchqueue):
        self.backframe = backframe
        self.dispatchqueue = dispatchqueue
        #self.local_boxes = ... set by callers
        #self.local_green = ... set by callers
        #self.pc = ...          set by callers
        #self.bytecode = ...    set by callers

    def enter_block(self, incoming, memo):
        for box in self.local_boxes:
            box.enter_block(incoming, memo)
        if self.backframe is not None:
            self.backframe.enter_block(incoming, memo)

    def freeze(self, memo):
        result = FrozenVirtualFrame()
        frozens = [box.freeze(memo) for box in self.local_boxes]
        result.fz_local_boxes = frozens
        if self.backframe is not None:
            result.fz_backframe = self.backframe.freeze(memo)
        return result

    def copy(self, memo):
        if self.backframe is None:
            newbackframe = None
        else:
            newbackframe = self.backframe.copy(memo)
        result = VirtualFrame(newbackframe, self.dispatchqueue)
        result.local_boxes = [box.copy(memo) for box in self.local_boxes]
        result.pc = self.pc
        result.bytecode = self.bytecode
        result.local_green = self.local_green[:]
        return result

    def replace(self, memo):
        local_boxes = self.local_boxes
        for i in range(len(local_boxes)):
            local_boxes[i] = local_boxes[i].replace(memo)
        if self.backframe is not None:
            self.backframe.replace(memo)


class JITState(object):
    _attrs_ = """curbuilder frame
                 exc_type_box exc_value_box
                 greens
                 gv_op_raised
                 returnbox
                 promotion_path
                 resumepoint resuming
                 next
                 virtualizables
                 shape_place
                 forced_boxes
                 generated_oop_residual_can_raise
                 ts
              """.split()

    returnbox = None
    next      = None   # for linked lists
    promotion_path = None
    generated_oop_residual_can_raise = False

    def __init__(self, builder, frame, exc_type_box, exc_value_box, ts,
                 resumepoint=-1, newgreens=None, virtualizables=None):
        self.curbuilder = builder
        self.frame = frame
        self.exc_type_box = exc_type_box
        self.exc_value_box = exc_value_box
        self.ts = ts
        self.resumepoint = resumepoint
        if newgreens is None:
            newgreens = []
        self.greens = newgreens
        self.gv_op_raised = None

        # XXX can not be a dictionary
        # it needs to be iterated in a deterministic order.
        if virtualizables is None:
            virtualizables = []
        self.virtualizables = virtualizables

    def add_virtualizable(self, virtualizable_box):
        assert isinstance(virtualizable_box, rvalue.PtrRedBox)
        if virtualizable_box not in self.virtualizables:
            self.virtualizables.append(virtualizable_box)

    def clone(self, memo):
        virtualizables = []
        for virtualizable_box in self.virtualizables:
            new_virtualizable_box = virtualizable_box.copy(memo)
            assert isinstance(new_virtualizable_box, rvalue.PtrRedBox)
            virtualizables.append(new_virtualizable_box)
        return JITState(self.curbuilder,
                        self.frame.copy(memo),
                        self.exc_type_box .copy(memo),
                        self.exc_value_box.copy(memo),
                        self.ts,
                        self.resumepoint,
                        self.greens[:],
                        virtualizables)

    def split(self, newbuilder, newresumepoint, newgreens, memo):
        virtualizables = []
        for virtualizable_box in self.virtualizables:
            new_virtualizable_box = virtualizable_box.copy(memo)
            assert isinstance(new_virtualizable_box, rvalue.PtrRedBox)
            virtualizables.append(new_virtualizable_box)
        later_jitstate = JITState(newbuilder,
                                  self.frame.copy(memo),
                                  self.exc_type_box .copy(memo),
                                  self.exc_value_box.copy(memo),
                                  self.ts,
                                  newresumepoint,
                                  newgreens,
                                  virtualizables)
        # add the later_jitstate to the chain of pending-for-dispatch_next()
        dispatchqueue = self.frame.dispatchqueue
        later_jitstate.next = dispatchqueue.split_chain
        dispatchqueue.split_chain = later_jitstate
        return later_jitstate

    def _enter_block(self, incoming, memo):
        self.frame.enter_block(incoming, memo)
        self.exc_type_box .enter_block(incoming, memo)
        self.exc_value_box.enter_block(incoming, memo)

    def enter_block_sweep_virtualizables(self):
        incoming = []
        memo = rvalue.enter_block_memo()
        self._enter_block(incoming, memo)
        virtualizables = self.virtualizables
        builder = self.curbuilder
        self.virtualizables = []
        for virtualizable_box in virtualizables:
            if virtualizable_box.content in memo.containers:
                self.virtualizables.append(virtualizable_box)
            else:
                content = virtualizable_box.content
                assert isinstance(content, rcontainer.VirtualizableStruct)
                content.store_back(self)
        return incoming

    def store_back_virtualizables_at_return(self):
        for virtualizable_box in self.virtualizables:
            assert isinstance(virtualizable_box, rvalue.PtrRedBox)
            content = virtualizable_box.content
            assert isinstance(content, rcontainer.VirtualizableStruct)
            content.store_back(self)

    def prepare_for_residual_call(self):
        virtualizables = self.virtualizables
        if virtualizables:
            builder = self.curbuilder
            memo = rvalue.make_vrti_memo()
            memo.bitcount = 1
            memo.frameindex = 0
            memo.framevars_gv = []
            memo.forced_boxes = forced_boxes = []
            
            shape_kind = builder.rgenop.kindToken(lltype.Signed)
            gv_zero = builder.rgenop.genconst(0)
            self.shape_place = builder.alloc_frame_place(shape_kind, gv_zero)
            self.forced_boxes = forced_boxes
            
            vable_rtis = []
            for virtualizable_box in virtualizables:
                content = virtualizable_box.content
                assert isinstance(content, rcontainer.VirtualizableStruct)
                vable_rtis.append(content.make_rti(self, memo))
            assert memo.bitcount < 32
            gv_base = builder.genop_get_frame_base()
            frameinfo = builder.get_frame_info(memo.framevars_gv)
            for i in range(len(virtualizables)):
                vable_rti = vable_rtis[i]
                if vable_rti is None:
                    continue
                assert isinstance(vable_rti, rvirtualizable.VirtualizableRTI)
                vable_rti.frameinfo = frameinfo
                virtualizable_box = virtualizables[i]
                content = virtualizable_box.content
                assert isinstance(content, rcontainer.VirtualizableStruct)
                content.prepare_for_residual_call(self, gv_base, vable_rti)
                
    def check_forced_after_residual_call(self):
        virtualizables = self.virtualizables
        builder = self.curbuilder
        if virtualizables:
            for virtualizable_box in virtualizables:
                content = virtualizable_box.content
                assert isinstance(content, rcontainer.VirtualizableStruct)
                content.check_forced_after_residual_call(self)
            shape_kind = builder.rgenop.kindToken(lltype.Signed)

            for forced_box, forced_place in self.forced_boxes:
                gv_forced = builder.genop_absorb_place(forced_place)
                forced_box.setgenvar(gv_forced)
            self.forced_boxes = None

            gv_shape = builder.genop_absorb_place(shape_kind,
                                                  self.shape_place)
            self.shape_place = None
            
            return gv_shape
        else:
            return None

    def reshape(self, shapemask):
        virtualizables = self.virtualizables
        builder = self.curbuilder
        if virtualizables:
            memo = rvalue.make_vrti_memo()
            memo.bitcount = 1
            if shapemask:
                memo.forced = []
            else:
                memo.forced = None

            for virtualizable_box in virtualizables:
                content = virtualizable_box.content
                assert isinstance(content, rcontainer.VirtualizableStruct)
                content.reshape(self, shapemask, memo)

            if shapemask:
                for vcontainer, gv_ptr in memo.forced:
                    vcontainer.setforced(gv_ptr)
                
    def freeze(self, memo):
        result = FrozenJITState()
        result.fz_frame = self.frame.freeze(memo)
        result.fz_exc_type_box  = self.exc_type_box .freeze(memo)
        result.fz_exc_value_box = self.exc_value_box.freeze(memo)
        assert self.gv_op_raised is None
        result.ts = self.ts
        fz_virtualizables = result.fz_virtualizables = []
        for virtualizable_box in self.virtualizables:
            assert virtualizable_box in memo.boxes
            fz_virtualizables.append(virtualizable_box.freeze(memo))
        return result

    def replace(self, memo):
        self.frame.replace(memo)
        self.exc_type_box  = self.exc_type_box .replace(memo)
        self.exc_value_box = self.exc_value_box.replace(memo)
        virtualizables = []
        for i in range(len(self.virtualizables)):
            virtualizable_box = self.virtualizables[i]
            new_virtualizable_box = virtualizable_box.replace(memo)
            assert isinstance(new_virtualizable_box, rvalue.PtrRedBox)
            self.virtualizables[i] = new_virtualizable_box
            
    def get_locals_gv(self):
        # get all the genvars that are "alive", i.e. stored in the JITState
        # or the VirtualFrames
        incoming = []
        memo = rvalue.enter_block_memo()
        self._enter_block(incoming, memo)
        for virtualizable_box in self.virtualizables:
            virtualizable_box.enter_block(incoming, memo)
        locals_gv = [redbox.genvar for redbox in incoming]
        return locals_gv

    def pause(self):
        locals_gv = self.get_locals_gv()
        self.curbuilder = self.curbuilder.pause_writing(locals_gv)


    def residual_ll_exception(self, ll_evalue):
        ll_etype  = self.ts.get_typeptr(ll_evalue)
        etypebox  = rvalue.ll_fromvalue(self, ll_etype)
        evaluebox = rvalue.ll_fromvalue(self, ll_evalue)
        setexctypebox (self, etypebox )
        setexcvaluebox(self, evaluebox)

    def residual_exception(self, e):
        self.residual_ll_exception(cast_instance_to_base_ptr(e))

    def get_resuming(self):
        if self.frame.dispatchqueue is None:
            return None
        return self.frame.dispatchqueue.resuming

    def clear_resuming(self):
        f = self.frame
        while f is not None:
            f.dispatchqueue.resuming = None
            f = f.backframe

    def get_gv_op_raised(self):
        result = self.gv_op_raised
        self.gv_op_raised = None
        return result


def start_writing(jitstate=None, prevopen=None):
    if jitstate is not prevopen:
        if prevopen is not None:
            prevopen.pause()
        jitstate.curbuilder.start_writing()
    return jitstate


def enter_frame(jitstate, dispatchqueue):
    if jitstate.frame:
        resuming = jitstate.get_resuming()
        dispatchqueue.resuming = resuming
    else:
        resuming = None
    jitstate.frame = VirtualFrame(jitstate.frame, dispatchqueue)
    if resuming is None:
        node = PromotionPathCall(jitstate.promotion_path)
        node = PromotionPathMergesToSee(node, 0)
        jitstate.promotion_path = node
    else:
        parent_mergesleft = resuming.mergesleft
        resuming.mergesleft = MC_IGNORE_UNTIL_RETURN
        if parent_mergesleft == 0:
            node = resuming.path.pop()
            if isinstance(node, PromotionPathCall):
                resuming.merges_to_see()
            else:
                assert isinstance(node, PromotionPathCallNotTaken)
                parent_mergesleft = MC_CALL_NOT_TAKEN
        dispatchqueue.mergecounter = parent_mergesleft

def merge_returning_jitstates(dispatchqueue, force_merge=False):
    return_chain = dispatchqueue.return_chain
    return_cache = newgreendict()
    still_pending = None
    opened = None
    while return_chain is not None:
        jitstate = return_chain
        return_chain = return_chain.next
        opened = start_writing(jitstate, opened)
        res = retrieve_jitstate_for_merge(return_cache, jitstate, empty_key,
                                          return_marker,
                                          force_merge=force_merge)
        if res is False:    # not finished
            jitstate.next = still_pending
            still_pending = jitstate
        else:
            opened = None
    
    # Of the jitstates we have left some may be mergable to a later
    # more general one.
    return_chain = still_pending
    if return_chain is not None:
        return_cache = newgreendict()
        still_pending = None
        while return_chain is not None:
            jitstate = return_chain
            return_chain = return_chain.next
            opened = start_writing(jitstate, opened)
            res = retrieve_jitstate_for_merge(return_cache, jitstate, empty_key,
                                              return_marker,
                                              force_merge=force_merge)
            if res is False:    # not finished
                jitstate.next = still_pending
                still_pending = jitstate
            else:
                opened = None
    start_writing(still_pending, opened)
    return still_pending

def leave_graph_red(dispatchqueue, is_portal):
    resuming = dispatchqueue.resuming
    return_chain = merge_returning_jitstates(dispatchqueue,
                                             force_merge=is_portal)
    if is_portal:
        assert return_chain is None or return_chain.next is None
    if resuming is not None:
        resuming.leave_call(dispatchqueue)
    jitstate = return_chain
    while jitstate is not None:
        myframe = jitstate.frame
        leave_frame(jitstate)
        jitstate.greens = []
        assert len(myframe.local_boxes) == 1
        jitstate.returnbox = myframe.local_boxes[0]
        jitstate = jitstate.next
    return return_chain

def leave_graph_gray(dispatchqueue):
    resuming = dispatchqueue.resuming
    return_chain = merge_returning_jitstates(dispatchqueue)
    if resuming is not None:
        resuming.leave_call(dispatchqueue)
    jitstate = return_chain
    while jitstate is not None:
        leave_frame(jitstate)
        jitstate.greens = []
        jitstate.returnbox = None
        jitstate = jitstate.next
    return return_chain

def leave_frame(jitstate):
    resuming = jitstate.get_resuming()
    myframe = jitstate.frame
    backframe = myframe.backframe
    jitstate.frame = backframe    
    if resuming is None:
        #debug_view(jitstate)
        node = jitstate.promotion_path
        while not node.cut_limit:
            node = node.next
        if isinstance(node, PromotionPathCall):
            node = PromotionPathCallNotTaken(node.next)
        else:
            node = PromotionPathBackFromReturn(node)
            node = PromotionPathMergesToSee(node, 0)
        jitstate.promotion_path = node


def leave_graph_yellow(mydispatchqueue):
    resuming = mydispatchqueue.resuming
    if resuming is not None:
        resuming.leave_call(mydispatchqueue)
    return_chain = mydispatchqueue.return_chain
    if return_chain is not None:
        jitstate = return_chain
        while jitstate is not None:
            leave_frame(jitstate)
            jitstate = jitstate.next
        # return the jitstate which is the head of the chain,
        # ready for further writing
        return_chain.curbuilder.start_writing()
    return return_chain
