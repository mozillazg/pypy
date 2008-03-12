from pypy.objspace.flow.model import Constant, Variable, SpaceOperation
from pypy.objspace.flow.model import Link, checkgraph
from pypy.rpython.annlowlevel import llhelper
from pypy.rpython.lltypesystem import lltype, lloperation
from pypy.rpython.llinterp import LLInterpreter
from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.objectmodel import we_are_translated
from pypy.jit.hintannotator.model import originalconcretetype
from pypy.jit.timeshifter import rvalue
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
        for block in origportalgraph.iterblocks():
            if block is origportalgraph.returnblock:
                raise Exception("XXX doesn't support portal functions with"
                                " a 'return' yet - leave it with 'raise' :-)")
        newportalgraph = self.hintannotator.translator.graphs[0]
        ALLARGS = []
        RESARGS = []
        self.args_specification = []
        for v in newportalgraph.getargs():
            TYPE = v.concretetype
            ALLARGS.append(TYPE)
            if self.hintannotator.binding(v).is_green():
                xxx
            else:
                RESARGS.append(TYPE)
                kind = self.RGenOp.kindToken(TYPE)
                boxcls = rvalue.ll_redboxcls(TYPE)
                self.args_specification.append((kind, boxcls))

        self.JIT_ENTER_FUNCTYPE = lltype.FuncType(ALLARGS, lltype.Void)
        self.RESIDUAL_FUNCTYPE = lltype.FuncType(RESARGS, lltype.Void)
        self.sigtoken = self.RGenOp.sigToken(self.RESIDUAL_FUNCTYPE)

    def make_enter_function(self):
        HotEnterState = make_state_class(self)
        state = HotEnterState()
        exceptiondesc = self.codewriter.exceptiondesc
        interpreter = self.interpreter

        def jit_may_enter(*args):
            counter = state.counter
            if counter >= 0:
                counter += 1
                if counter < self.threshold:
                    interpreter.debug_trace("jit_not_entered", *args)
                    state.counter = counter
                    return
                interpreter.debug_trace("jit_compile", *args)
                if not state.compile():
                    return
            interpreter.debug_trace("run_machine_code", *args)
            maybe_on_top_of_llinterp(exceptiondesc, state.machine_code)(*args)

        HotEnterState.compile.im_func._dont_inline_ = True
        jit_may_enter._always_inline = True
        self.jit_may_enter_fn = jit_may_enter

    def update_interp(self):
        self.fallbackinterp = FallbackInterpreter(
            self.interpreter,
            self.ContinueRunningNormally,
            self.codewriter.exceptiondesc)
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
        # In the original graphs, replace the 'jit_can_enter' operations
        # with a call to the jit_may_enter() helper.
        #
        assert graph is not self.hintannotator.origportalgraph, (
            "XXX can_enter_jit() cannot appear before jit_merge_point() "
            "in the portal graph")
        if not self.translate_support_code:
            # this case is used for most tests: the jit stuff should be run
            # directly to make these tests faster
            op = block.operations[index]
            numgreens = op.args[0].value
            numreds = op.args[1].value
            assert numgreens == 0    # XXX for the first test
            reds_v = op.args[2+numgreens:2+numgreens+numreds]

            FUNCPTR = lltype.Ptr(self.JIT_ENTER_FUNCTYPE)
            jit_enter_graph_ptr = llhelper(FUNCPTR, self.jit_may_enter_fn)
            vlist = [Constant(jit_enter_graph_ptr, FUNCPTR)] + reds_v

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
        assert portalgraph.getreturnvar().concretetype is lltype.Void
        PORTALFUNC = lltype.FuncType(ARGS, lltype.Void)

        if not self.translate_support_code:
            # ____________________________________________________________
            # Prepare the portal_runner() helper, in a version that
            # doesn't need to be translated
            #
            exc_data_ptr = self.codewriter.exceptiondesc.exc_data_ptr
            llinterp = LLInterpreter(self.rtyper, exc_data_ptr=exc_data_ptr)
            jit_may_enter = self.jit_may_enter_fn

            class ContinueRunningNormally(Exception):
                _go_through_llinterp_uncaught_ = True     # ugh
                def __init__(self, args_gv):
                    assert len(args_gv) == len(ARGS)
                    self.args = [gv_arg.revealconst(ARG)
                                 for gv_arg, ARG in zip(args_gv, ARGS)]
                def __str__(self):
                    return 'ContinueRunningNormally(%s)' % (
                        ', '.join(map(str, self.args)),)
            self.ContinueRunningNormally = ContinueRunningNormally

            def portal_runner(*args):
                check_for_immediate_reentry = False
                while 1:
                    try:
                        if check_for_immediate_reentry:
                            jit_may_enter(*args)
                        llinterp.eval_graph(portalgraph, list(args))
                        assert 0, "unreachable"
                    except ContinueRunningNormally, e:
                        args = e.args
                        self.interpreter.debug_trace("fb_leave", *args)
                        check_for_immediate_reentry = True
                        # ^^^ but should depend on whether the fallback
                        # interpreter reached a jit_can_enter() or just
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
        v_result.concretetype = lltype.Void
        newop = SpaceOperation('direct_call', vlist, v_result)
        del origblock.operations[origindex:]
        origblock.operations.append(newop)
        origblock.exitswitch = None
        origblock.recloseblock(Link([Constant(None, lltype.Void)],
                                    origportalgraph.returnblock))
        checkgraph(origportalgraph)
        return True


def make_state_class(rewriter):
    # very minimal, just to make the first test pass
    args_specification = unrolling_iterable(rewriter.args_specification)

    class HotEnterState:
        def __init__(self):
            self.machine_code = lltype.nullptr(rewriter.RESIDUAL_FUNCTYPE)
            self.counter = 0     # -1 means "compiled"

        def compile(self):
            try:
                self._compile()
                return True
            except Exception, e:
                rhotpath.report_compile_time_exception(rewriter.interpreter, e)
                return False

        def _compile(self):
            interp = rewriter.interpreter
            rgenop = interp.rgenop
            builder, gv_generated, inputargs_gv = rgenop.newgraph(
                rewriter.sigtoken, "residual")

            greenargs = ()
            redargs = ()
            red_i = 0
            for kind, boxcls in args_specification:
                gv_arg = inputargs_gv[red_i]
                red_i += 1
                box = boxcls(kind, gv_arg)
                redargs += (box,)
            greenargs = list(greenargs)
            redargs = list(redargs)

            jitstate = interp.fresh_jitstate(builder)
            rhotpath.setup_jitstate(interp, jitstate, greenargs, redargs,
                                    rewriter.entryjitcode, rewriter.sigtoken)
            builder = jitstate.curbuilder
            builder.start_writing()
            rhotpath.compile(interp)
            builder.end()

            FUNCPTR = lltype.Ptr(rewriter.RESIDUAL_FUNCTYPE)
            self.machine_code = gv_generated.revealconst(FUNCPTR)
            self.counter = -1     # compiled

    return HotEnterState

