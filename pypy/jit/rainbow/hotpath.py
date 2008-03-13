from pypy.objspace.flow.model import Constant, Variable, SpaceOperation
from pypy.objspace.flow.model import Link, checkgraph
from pypy.rpython.annlowlevel import llhelper
from pypy.rpython.lltypesystem import lltype, lloperation
from pypy.rpython.llinterp import LLInterpreter
from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.objectmodel import we_are_translated
from pypy.jit.hintannotator.model import originalconcretetype
from pypy.jit.timeshifter import rvalue
from pypy.jit.timeshifter.greenkey import KeyDesc, empty_key
from pypy.jit.timeshifter.greenkey import GreenKey, newgreendict
from pypy.jit.rainbow import rhotpath
from pypy.jit.rainbow.fallback import FallbackInterpreter
from pypy.jit.rainbow.codewriter import maybe_on_top_of_llinterp


class EntryPointsRewriter:

    def __init__(self, hintannotator, rtyper, entryjitcode, RGenOp,
                 codewriter, threshold, translate_support_code = True):
        self.hintannotator = hintannotator
        self.entryjitcode = entryjitcode
        self.rtyper = rtyper
        self.RGenOp = RGenOp
        self.interpreter = codewriter.interpreter
        self.codewriter = codewriter
        self.threshold = threshold
        self.translate_support_code = translate_support_code

    def _freeze_(self):
        return True

    def rewrite_all(self):
        self.make_args_specification()
        self.make_enter_function()
        self.rewrite_graphs()
        self.update_interp()

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
                RESARGS.append(TYPE)
                kind = self.RGenOp.kindToken(TYPE)
                boxcls = rvalue.ll_redboxcls(TYPE)
                self.red_args_spec.append((kind, boxcls))

        self.JIT_ENTER_FUNCTYPE = lltype.FuncType(ALLARGS, lltype.Void)
        self.RESIDUAL_FUNCTYPE = lltype.FuncType(RESARGS, lltype.Void)
        self.sigtoken = self.RGenOp.sigToken(self.RESIDUAL_FUNCTYPE)

    def make_enter_function(self):
        HotEnterState = make_state_class(self)
        state = HotEnterState()
        exceptiondesc = self.codewriter.exceptiondesc
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
                interpreter.debug_trace("jit_compile", *args)
                if not state.compile(key):
                    return
            interpreter.debug_trace("run_machine_code", *args)
            mc = state.machine_codes[key]
            run = maybe_on_top_of_llinterp(exceptiondesc, mc)
            run(*args[num_green_args:])

        HotEnterState.compile.im_func._dont_inline_ = True
        maybe_enter_jit._always_inline_ = True
        self.maybe_enter_jit_fn = maybe_enter_jit

    def update_interp(self):
        self.fallbackinterp = FallbackInterpreter(
            self.interpreter,
            self.codewriter.exceptiondesc,
            self.DoneWithThisFrame,
            self.ContinueRunningNormally)
        ERASED = self.RGenOp.erasedType(lltype.Bool)
        self.interpreter.bool_hotpromotiondesc = rhotpath.HotPromotionDesc(
            ERASED, self.interpreter, self.threshold, self.fallbackinterp)

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
        if not self.translate_support_code:
            # this case is used for most tests: the jit stuff should be run
            # directly to make these tests faster
            op = block.operations[index]
            numgreens = op.args[0].value
            numreds = op.args[1].value
            args_v = op.args[2:2+numgreens+numreds]

            FUNCPTR = lltype.Ptr(self.JIT_ENTER_FUNCTYPE)
            jit_enter_graph_ptr = llhelper(FUNCPTR, self.maybe_enter_jit_fn)
            vlist = [Constant(jit_enter_graph_ptr, FUNCPTR)] + args_v

            v_result = Variable()
            v_result.concretetype = lltype.Void
            newop = SpaceOperation('direct_call', vlist, v_result)
            block.operations[index] = newop
        else:
            xxx
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
        if origportalgraph is portalgraph:
            return False      # only mutate the original portal graph,
                              # not its copy

        ARGS = [v.concretetype for v in portalgraph.getargs()]
        RES = portalgraph.getreturnvar().concretetype
        PORTALFUNC = lltype.FuncType(ARGS, RES)

        if not self.translate_support_code:
            # ____________________________________________________________
            # Prepare the portal_runner() helper, in a version that
            # doesn't need to be translated
            #
            exc_data_ptr = self.codewriter.exceptiondesc.exc_data_ptr
            llinterp = LLInterpreter(self.rtyper, exc_data_ptr=exc_data_ptr)
            maybe_enter_jit = self.maybe_enter_jit_fn

            class DoneWithThisFrame(Exception):
                _go_through_llinterp_uncaught_ = True     # ugh
                def __init__(self, gv_result):
                    if RES is lltype.Void:
                        assert gv_result is None
                        self.result = None
                    else:
                        self.result = gv_result.revealconst(RES)
                def __str__(self):
                    return 'DoneWithThisFrame(%s)' % (self.result,)

            class ContinueRunningNormally(Exception):
                _go_through_llinterp_uncaught_ = True     # ugh
                def __init__(self, args_gv, seen_can_enter_jit):
                    assert len(args_gv) == len(ARGS)
                    self.args = [gv_arg.revealconst(ARG)
                                 for gv_arg, ARG in zip(args_gv, ARGS)]
                    self.seen_can_enter_jit = seen_can_enter_jit
                def __str__(self):
                    return 'ContinueRunningNormally(%s)' % (
                        ', '.join(map(str, self.args)),)

            self.DoneWithThisFrame = DoneWithThisFrame
            self.ContinueRunningNormally = ContinueRunningNormally

            def portal_runner(*args):
                check_for_immediate_reentry = False
                while 1:
                    try:
                        if check_for_immediate_reentry:
                            maybe_enter_jit(*args)
                        return llinterp.eval_graph(portalgraph, list(args))
                    except DoneWithThisFrame, e:
                        return e.result
                    except ContinueRunningNormally, e:
                        args = e.args
                        self.interpreter.debug_trace("fb_leave", *args)
                        check_for_immediate_reentry = e.seen_can_enter_jit
                        # ^^^ but should depend on whether the fallback
                        # interpreter reached a can_enter_jit() or just
                        # the jit_merge_point()

            portal_runner_ptr = lltype.functionptr(PORTALFUNC, 'portal_runner',
                                                   _callable = portal_runner)
        else:
            xxx
        # ____________________________________________________________
        # Now mutate origportalgraph to end with a call to portal_runner_ptr
        #
        op = origblock.operations[origindex]
        assert op.opname == 'jit_merge_point'
        numgreens = op.args[0].value
        numreds = op.args[1].value
        greens_v = op.args[2:2+numgreens]
        reds_v = op.args[2+numgreens:2+numgreens+numreds]
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


def make_state_class(rewriter):
    # very minimal, just to make the first test pass
    green_args_spec = unrolling_iterable(rewriter.green_args_spec)
    red_args_spec = unrolling_iterable(rewriter.red_args_spec)
    if rewriter.green_args_spec:
        keydesc = KeyDesc(rewriter.RGenOp, *rewriter.green_args_spec)
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
            rgenop = rewriter.interpreter.rgenop
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
                rhotpath.report_compile_time_exception(rewriter.interpreter, e)
                return False

        def _compile(self, greenkey):
            interp = rewriter.interpreter
            rgenop = interp.rgenop
            builder, gv_generated, inputargs_gv = rgenop.newgraph(
                rewriter.sigtoken, "residual")

            greenargs = list(greenkey.values)
            redargs = ()
            red_i = 0
            for kind, boxcls in red_args_spec:
                gv_arg = inputargs_gv[red_i]
                red_i += 1
                box = boxcls(kind, gv_arg)
                redargs += (box,)
            redargs = list(redargs)

            jitstate = interp.fresh_jitstate(builder)
            rhotpath.setup_jitstate(interp, jitstate, greenargs, redargs,
                                    rewriter.entryjitcode, rewriter.sigtoken)
            builder = jitstate.curbuilder
            builder.start_writing()
            rhotpath.compile(interp)
            builder.end()

            FUNCPTR = lltype.Ptr(rewriter.RESIDUAL_FUNCTYPE)
            self.machine_codes[greenkey] = gv_generated.revealconst(FUNCPTR)
            self.counters[greenkey] = -1     # compiled

    return HotEnterState
