from pypy.objspace.flow.model import Constant, Variable, SpaceOperation
from pypy.objspace.flow.model import Link, checkgraph
from pypy.annotation import model as annmodel
from pypy.rpython import annlowlevel
from pypy.rpython.annlowlevel import llhelper
from pypy.rpython.lltypesystem import lltype, lloperation
from pypy.rpython.llinterp import LLInterpreter
from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.objectmodel import we_are_translated
from pypy.jit.hintannotator.model import originalconcretetype
from pypy.jit.timeshifter import rvalue
from pypy.jit.timeshifter.oop import maybe_on_top_of_llinterp
from pypy.jit.timeshifter.greenkey import KeyDesc, empty_key
from pypy.jit.timeshifter.greenkey import GreenKey, newgreendict
from pypy.jit.rainbow import rhotpath
from pypy.jit.rainbow.fallback import FallbackInterpreter
from pypy.jit.rainbow.portal import getjitenterargdesc


class HotRunnerDesc:

    def __init__(self, hintannotator, rtyper, entryjitcode, RGenOp,
                 codewriter, threshold, translate_support_code = True):
        self.hintannotator = hintannotator
        self.entryjitcode = entryjitcode
        self.rtyper = rtyper
        self.RGenOp = RGenOp
        self.exceptiondesc = codewriter.exceptiondesc
        self.interpreter = codewriter.interpreter
        self.ts = self.interpreter.ts
        self.codewriter = codewriter
        self.threshold = threshold
        self.translate_support_code = translate_support_code

    def _freeze_(self):
        return True

    def rewrite_all(self):
        if self.translate_support_code:
            self.annhelper = annlowlevel.MixLevelHelperAnnotator(self.rtyper)
        self.interpreter.set_hotrunnerdesc(self)
        self.make_args_specification()
        self.make_enter_function()
        self.rewrite_graphs()
        self.make_descs()
        self.fallbackinterp = FallbackInterpreter(self)
        if self.translate_support_code:
            self.annhelper.finish()

    def make_args_specification(self):
        origportalgraph = self.hintannotator.portalgraph
        newportalgraph = self.hintannotator.translator.graphs[0]
        ALLARGS = []
        RESARGS = []
        self.red_args_spec = []
        self.green_args_spec = []
        for v in newportalgraph.getargs():
            TYPE = v.concretetype
            ALLARGS.append(TYPE)
            if self.hintannotator.binding(v).is_green():
                self.green_args_spec.append(TYPE)
                assert len(self.red_args_spec) == 0, "bogus order of colors"
            else:
                argdesc = getjitenterargdesc(TYPE, self.RGenOp)
                arg_spec = (argdesc.residual_args_collector(),
                            argdesc.arg_redbox_maker(), TYPE)
                self.red_args_spec.append(arg_spec)
                RESARGS.extend(argdesc.residual_argtypes())

        self.JIT_ENTER_FUNCTYPE = lltype.FuncType(ALLARGS, lltype.Void)
        self.RESIDUAL_FUNCTYPE = lltype.FuncType(RESARGS, lltype.Void)
        self.sigtoken = self.RGenOp.sigToken(self.RESIDUAL_FUNCTYPE)

    def make_enter_function(self):
        HotEnterState = make_state_class(self)
        state = HotEnterState()
        exceptiondesc = self.exceptiondesc
        interpreter = self.interpreter
        num_green_args = len(self.green_args_spec)

        def maybe_enter_jit(*args):
            key = state.getkey(*args[:num_green_args])
            counter = state.counters.get(key, 0)
            if counter >= 0:
                counter += 1
                if counter < self.threshold:
                    interpreter.debug_trace("jit_not_entered", *args)
                    state.counters[key] = counter
                    return
                interpreter.debug_trace("jit_compile", *args[:num_green_args])
                if not state.compile(key):
                    return
            interpreter.debug_trace("run_machine_code", *args)
            mc = state.machine_codes[key]
            run = maybe_on_top_of_llinterp(exceptiondesc, mc)
            residualargs = state.make_residualargs(*args[num_green_args:])
            run(*residualargs)

        HotEnterState.compile.im_func._dont_inline_ = True
        maybe_enter_jit._always_inline_ = True
        self.maybe_enter_jit_fn = maybe_enter_jit

    def make_descs(self):
        HotPromotionDesc = rhotpath.HotPromotionDesc
        RGenOp = self.RGenOp
        EBOOL   = RGenOp.erasedType(lltype.Bool)
        ESIGNED = RGenOp.erasedType(lltype.Signed)
        self.bool_hotpromotiondesc   = HotPromotionDesc(EBOOL,   RGenOp)
        self.signed_hotpromotiondesc = HotPromotionDesc(ESIGNED, RGenOp)

    def rewrite_graphs(self):
        for graph in self.hintannotator.base_translator.graphs:
            while self.rewrite_graph(graph):
                pass

    def rewrite_graph(self, graph):
        for block in graph.iterblocks():
            for op in block.operations:
                if op.opname == 'can_enter_jit':
                    index = block.operations.index(op)
                    if self.rewrite_can_enter_jit(graph, block, index):
                        return True      # graph mutated, start over again
                elif op.opname == 'jit_merge_point':
                    index = block.operations.index(op)
                    if self.rewrite_jit_merge_point(graph, block, index):
                        return True      # graph mutated, start over again
        return False  # done

    def rewrite_can_enter_jit(self, graph, block, index):
        #
        # In the original graphs, replace the 'can_enter_jit' operations
        # with a call to the maybe_enter_jit() helper.
        #
        assert graph is not self.hintannotator.origportalgraph, (
            "XXX can_enter_jit() cannot appear before jit_merge_point() "
            "in the graph of the main loop")
        FUNC = self.JIT_ENTER_FUNCTYPE
        FUNCPTR = lltype.Ptr(FUNC)

        if not self.translate_support_code:
            # this case is used for most tests: the jit stuff should be run
            # directly to make these tests faster
            jit_enter_fnptr = llhelper(FUNCPTR, self.maybe_enter_jit_fn)
        else:
            args_s = [annmodel.lltype_to_annotation(ARG) for ARG in FUNC.ARGS]
            s_result = annmodel.lltype_to_annotation(FUNC.RESULT)
            jit_enter_fnptr = self.annhelper.delayedfunction(
                self.maybe_enter_jit_fn, args_s, s_result)

        op = block.operations[index]
        greens_v, reds_v = self.codewriter.decode_hp_hint_args(op)
        args_v = greens_v + reds_v

        vlist = [Constant(jit_enter_fnptr, FUNCPTR)] + args_v

        v_result = Variable()
        v_result.concretetype = lltype.Void
        newop = SpaceOperation('direct_call', vlist, v_result)
        block.operations[index] = newop
        return True

    def rewrite_jit_merge_point(self, origportalgraph, origblock, origindex):
        #
        # Mutate the original portal graph from this:
        #
        #       def original_portal(..):
        #           stuff
        #           jit_merge_point(*args)
        #           more stuff
        #
        # to that:
        #
        #       def original_portal(..):
        #           stuff
        #           return portal_runner(*args)
        #
        #       def portal_runner(*args):
        #           while 1:
        #               try:
        #                   return portal(*args)
        #               except ContinueRunningNormally, e:
        #                   *args = *e.new_args
        #
        #       def portal(*args):
        #           more stuff
        #
        portalgraph = self.hintannotator.portalgraph
        # ^^^ as computed by HotPathHintAnnotator.prepare_portal_graphs()
        if origportalgraph is not self.hintannotator.origportalgraph:
            return False      # only mutate the original portal graph,
                              # not its copy

        ARGS = [v.concretetype for v in portalgraph.getargs()]
        RES = portalgraph.getreturnvar().concretetype
        PORTALFUNC = lltype.FuncType(ARGS, RES)

        # ____________________________________________________________
        # Prepare the portal_runner() helper
        #
        exceptiondesc = self.exceptiondesc
        portal_ptr = lltype.functionptr(PORTALFUNC, 'portal',
                                        graph = portalgraph)
        maybe_enter_jit = self.maybe_enter_jit_fn
        unroll_ARGS = unrolling_iterable(ARGS)

        class DoneWithThisFrame(Exception):
            _go_through_llinterp_uncaught_ = True     # ugh
            def __init__(self, result):
                self.result = result
            def __str__(self):
                return 'DoneWithThisFrame(%s)' % (self.result,)

        def raise_done(llvalue=None):
            raise DoneWithThisFrame(llvalue)

        class ContinueRunningNormally(Exception):
            _go_through_llinterp_uncaught_ = True     # ugh
            args_gv = []       # for tests where __init__ is not seen
            seen_can_enter_jit = False

            def __init__(self, args_gv, seen_can_enter_jit):
                self.args_gv = args_gv
                self.seen_can_enter_jit = seen_can_enter_jit

            def __str__(self):
                return 'ContinueRunningNormally(%s)' % (
                    ', '.join(map(str, self.args_gv)),)

            def decode_args(self):
                args_gv = self.args_gv
                assert len(args_gv) == len(ARGS)
                args = ()
                i = 0
                for ARG in unroll_ARGS:
                    gv_arg = args_gv[i]
                    args += (gv_arg.revealconst(ARG), )
                    i += 1
                return args

        self.raise_done = raise_done
        RAISE_DONE_FUNC = lltype.FuncType([RES], lltype.Void)
        self.tok_raise_done = self.RGenOp.sigToken(RAISE_DONE_FUNC)
        self.RAISE_DONE_FUNCPTR = lltype.Ptr(RAISE_DONE_FUNC)
        self.DoneWithThisFrame = DoneWithThisFrame
        self.ContinueRunningNormally = ContinueRunningNormally

        def ll_portal_runner(*args):
            check_for_immediate_reentry = False
            while 1:
                try:
                    if check_for_immediate_reentry:
                        maybe_enter_jit(*args)
                    return maybe_on_top_of_llinterp(exceptiondesc,
                                                    portal_ptr)(*args)
                except DoneWithThisFrame, e:
                    return e.result
                except ContinueRunningNormally, e:
                    args = e.decode_args()
                    self.interpreter.debug_trace("fb_leave", *args)
                    check_for_immediate_reentry = e.seen_can_enter_jit

        if not self.translate_support_code:
            portal_runner_ptr = llhelper(lltype.Ptr(PORTALFUNC),
                                         ll_portal_runner)
        else:
            args_s = [annmodel.lltype_to_annotation(ARG) for ARG in ARGS]
            s_result = annmodel.lltype_to_annotation(RES)
            portal_runner_ptr = self.annhelper.delayedfunction(
                ll_portal_runner, args_s, s_result)

        # ____________________________________________________________
        # Now mutate origportalgraph to end with a call to portal_runner_ptr
        #
        op = origblock.operations[origindex]
        assert op.opname == 'jit_merge_point'
        greens_v, reds_v = self.codewriter.decode_hp_hint_args(op)
        vlist = [Constant(portal_runner_ptr, lltype.Ptr(PORTALFUNC))]
        vlist += greens_v
        vlist += reds_v
        v_result = Variable()
        v_result.concretetype = RES
        newop = SpaceOperation('direct_call', vlist, v_result)
        del origblock.operations[origindex:]
        origblock.operations.append(newop)
        origblock.exitswitch = None
        origblock.recloseblock(Link([v_result], origportalgraph.returnblock))
        checkgraph(origportalgraph)
        return True


def make_state_class(hotrunnerdesc):
    # very minimal, just to make the first test pass
    green_args_spec = unrolling_iterable(hotrunnerdesc.green_args_spec)
    red_args_spec = unrolling_iterable(hotrunnerdesc.red_args_spec)
    if hotrunnerdesc.green_args_spec:
        keydesc = KeyDesc(hotrunnerdesc.RGenOp, *hotrunnerdesc.green_args_spec)
    else:
        keydesc = None

    class HotEnterState:
        def __init__(self):
            self.machine_codes = newgreendict()
            self.counters = newgreendict()     # -1 means "compiled"

            # XXX XXX be more clever and find a way where we don't need
            # to allocate a GreenKey object for each call to
            # maybe_enter_jit().  One way would be to replace the
            # 'counters' with some hand-written fixed-sized hash table.
            # Indeed, this is all a heuristic, so if things are designed
            # correctly, the occasional mistake due to hash collision is
            # not too bad.  The fixed-size-ness would also let old
            # recorded counters gradually disappear as they get replaced
            # by more recent ones.

        def getkey(self, *greenvalues):
            if keydesc is None:
                return empty_key
            rgenop = hotrunnerdesc.interpreter.rgenop
            lst_gv = [None] * len(greenvalues)
            i = 0
            for _ in green_args_spec:
                lst_gv[i] = rgenop.genconst(greenvalues[i])
                i += 1
            return GreenKey(lst_gv, keydesc)

        def compile(self, greenkey):
            try:
                self._compile(greenkey)
                return True
            except Exception, e:
                rhotpath.report_compile_time_exception(
                    hotrunnerdesc.interpreter, e)
                return False

        def _compile(self, greenkey):
            interp = hotrunnerdesc.interpreter
            rgenop = interp.rgenop
            builder, gv_generated, inputargs_gv = rgenop.newgraph(
                hotrunnerdesc.sigtoken, "residual")

            greenargs = list(greenkey.values)

            jitstate = interp.fresh_jitstate(builder)
            redargs = ()
            red_i = 0
            for _, make_arg_redbox, _ in red_args_spec:
                gv_arg = inputargs_gv[red_i]
                box = make_arg_redbox(jitstate, inputargs_gv, red_i)
                redargs += (box,)
                red_i += make_arg_redbox.consumes
            redargs = list(redargs)

            rhotpath.setup_jitstate(interp, jitstate, greenargs, redargs,
                                    hotrunnerdesc.entryjitcode,
                                    hotrunnerdesc.sigtoken)
            builder.start_writing()
            rhotpath.compile(interp)
            builder.end()

            FUNCPTR = lltype.Ptr(hotrunnerdesc.RESIDUAL_FUNCTYPE)
            generated = gv_generated.revealconst(FUNCPTR)
            self.machine_codes[greenkey] = generated
            self.counters[greenkey] = -1     # compiled

            if not we_are_translated():
                hotrunnerdesc.residual_graph = generated._obj.graph  #for tests

        def make_residualargs(self, *redargs):
            residualargs = ()
            i = 0
            for collect_residual_args, _, _ in red_args_spec:
                residualargs = residualargs + collect_residual_args(redargs[i])
                i += 1
            return residualargs

    return HotEnterState
