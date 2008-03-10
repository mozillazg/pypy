from pypy.objspace.flow.model import Constant, Variable, SpaceOperation
from pypy.rpython.annlowlevel import llhelper
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.llinterp import LLInterpreter
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.objectmodel import we_are_translated
from pypy.jit.hintannotator.model import originalconcretetype
from pypy.jit.timeshifter import rvalue


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
        for graph in self.hintannotator.base_translator.graphs:
            for block in graph.iterblocks():
                for op in block.operations:
                    if op.opname == 'can_enter_jit':
                        index = block.operations.index(op)
                        self.rewrite_can_enter_jit(graph, block, index)

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

        def jit_may_enter(*args):
            if not state.machine_code:
                state.counter += 1
                if state.counter < self.threshold:
                    return
                state.compile()
            maybe_on_top_of_llinterp(self, state.machine_code)(*args)

        HotEnterState.compile.im_func._dont_inline_ = True
        jit_may_enter._always_inline = True
        self.jit_enter_fn = jit_may_enter

    def rewrite_can_enter_jit(self, graph, block, index):
        if not self.translate_support_code:
            # this case is used for most tests: the jit stuff should be run
            # directly to make these tests faster
            op = block.operations[index]
            numgreens = op.args[0].value
            numreds = op.args[1].value
            assert numgreens == 0    # XXX for the first test
            reds_v = op.args[2+numgreens:2+numgreens+numreds]

            FUNCPTR = lltype.Ptr(self.JIT_ENTER_FUNCTYPE)
            jit_enter_graph_ptr = llhelper(FUNCPTR, self.jit_enter_fn)
            vlist = [Constant(jit_enter_graph_ptr, FUNCPTR)] + reds_v

            v_result = Variable()
            v_result.concretetype = lltype.Void
            newop = SpaceOperation('direct_call', vlist, v_result)
            block.operations[index] = newop
        else:
            xxx


def make_state_class(rewriter):
    # very minimal, just to make the first test pass
    args_specification = unrolling_iterable(rewriter.args_specification)

    class HotEnterState:
        def __init__(self):
            self.graph_compilation_queue = []
            self.machine_code = lltype.nullptr(rewriter.RESIDUAL_FUNCTYPE)
            self.counter = 0

        def compile_more_functions(self):
            while self.graph_compilation_queue:
                top_jitstate, greenargs, redargs = self.graph_compilation_queue.pop()
                builder = top_jitstate.curbuilder
                builder.start_writing()
                top_jitstate = rewriter.interpreter.run(top_jitstate,
                                                        rewriter.entryjitcode,
                                                        greenargs, redargs)
                if top_jitstate is not None:
                    rewriter.interpreter.finish_jitstate_gray(
                        rewriter.sigtoken)
                builder.end()
                builder.show_incremental_progress()

        def compile(self):
            rgenop = rewriter.interpreter.rgenop
            builder, gv_generated, inputargs_gv = rgenop.newgraph(
                rewriter.sigtoken, "residual")
            top_jitstate = rewriter.interpreter.fresh_jitstate(builder)

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

            self.graph_compilation_queue.append((top_jitstate,
                                                 greenargs, redargs))
            self.compile_more_functions()

            FUNCPTR = lltype.Ptr(rewriter.RESIDUAL_FUNCTYPE)
            self.machine_code = gv_generated.revealconst(FUNCPTR)

    return HotEnterState


def maybe_on_top_of_llinterp(rewriter, fnptr):
    # Run a generated graph on top of the llinterp for testing.
    # When translated, this just returns the fnptr.
    exc_data_ptr = rewriter.codewriter.exceptiondesc.exc_data_ptr
    llinterp = LLInterpreter(rewriter.rtyper, exc_data_ptr=exc_data_ptr)
    def on_top_of_llinterp(*args):
        return llinterp.eval_graph(fnptr._obj.graph, list(args))
    return on_top_of_llinterp

class Entry(ExtRegistryEntry):
    _about_ = maybe_on_top_of_llinterp

    def compute_result_annotation(self, s_rewriter, s_fnptr):
        return s_fnptr

    def specialize_call(self, hop):
        return hop.inputarg(hop.args_r[1], arg=1)
