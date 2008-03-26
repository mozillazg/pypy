from pypy.objspace.flow.model import Constant, Variable, SpaceOperation
from pypy.objspace.flow.model import Link, checkgraph
from pypy.annotation import model as annmodel
from pypy.rpython import annlowlevel
from pypy.rpython.annlowlevel import llhelper
from pypy.rpython.lltypesystem import lltype, lloperation
from pypy.rpython.llinterp import LLInterpreter
from pypy.rlib.objectmodel import we_are_translated, UnboxedValue
from pypy.rlib.rarithmetic import r_uint
from pypy.rlib.unroll import unrolling_iterable
from pypy.jit.codegen.i386.rgenop import cast_whatever_to_int
from pypy.jit.hintannotator.model import originalconcretetype
from pypy.jit.timeshifter import rvalue
from pypy.jit.timeshifter.oop import maybe_on_top_of_llinterp
from pypy.jit.rainbow import rhotpath, fallback
from pypy.jit.rainbow.portal import getjitenterargdesc


class HotRunnerDesc:

    def __init__(self, hintannotator, rtyper, entryjitcode, RGenOp,
                 codewriter, jitdrivercls, translate_support_code = True,
                 verbose_level=3):
        self.hintannotator = hintannotator
        self.entryjitcode = entryjitcode
        self.rtyper = rtyper
        self.RGenOp = RGenOp
        self.exceptiondesc = codewriter.exceptiondesc
        self.interpreter = codewriter.interpreter
        self.ts = self.interpreter.ts
        self.codewriter = codewriter
        self.jitdrivercls = jitdrivercls
        self.translate_support_code = translate_support_code
        self.verbose_level = verbose_level

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
        self.fbrunnerdesc = fallback.FallbackRunnerDesc(self)
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
            greenargs = args[:num_green_args]
            mc = state.maybe_compile(*greenargs)
            if not mc:
                return
            if self.verbose_level >= 2:
                interpreter.debug_trace("run_machine_code", *args)
            run = maybe_on_top_of_llinterp(exceptiondesc, mc)
            residualargs = state.make_residualargs(*args[num_green_args:])
            run(*residualargs)
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
    green_args_names = unrolling_iterable(
        ['g%d' % i for i in range(len(hotrunnerdesc.green_args_spec))])
    green_args_range = unrolling_iterable(
        range(len(hotrunnerdesc.green_args_spec)))
    if hotrunnerdesc.green_args_spec:
        HASH_TABLE_SIZE = 2 ** 14
    else:
        HASH_TABLE_SIZE = 1

    class StateCell(object):
        __slots__ = []

    class Counter(StateCell, UnboxedValue):
        __slots__ = 'counter'

    class MachineCodeEntryPoint(StateCell):
        def __init__(self, mc, *greenargs):
            self.mc = mc
            self.next = Counter(0)
            i = 0
            for name in green_args_names:
                setattr(self, name, greenargs[i])
                i += 1
        def equalkey(self, *greenargs):
            i = 0
            for name in green_args_names:
                if getattr(self, name) != greenargs[i]:
                    return False
                i += 1
            return True

    class HotEnterState:
        NULL_MC = lltype.nullptr(hotrunnerdesc.RESIDUAL_FUNCTYPE)

        def __init__(self):
            self.cells = [Counter(0)] * HASH_TABLE_SIZE

            # Only use the hash of the arguments as the profiling key.
            # Indeed, this is all a heuristic, so if things are designed
            # correctly, the occasional mistake due to hash collision is
            # not too bad.

        def maybe_compile(self, *greenargs):
            argshash = self.getkeyhash(*greenargs)
            argshash &= (HASH_TABLE_SIZE - 1)
            cell = self.cells[argshash]
            if isinstance(cell, Counter):
                # update the profiling counter
                interp = hotrunnerdesc.interpreter
                n = cell.counter + 1
                if n < hotrunnerdesc.jitdrivercls.getcurrentthreshold():
                    if hotrunnerdesc.verbose_level >= 3:
                        interp.debug_trace("jit_not_entered", *greenargs)
                    self.cells[argshash] = Counter(n)
                    return self.NULL_MC
                interp.debug_trace("jit_compile", *greenargs)
                return self.compile(argshash, *greenargs)
            else:
                # machine code was already compiled for these greenargs
                # (or we have a hash collision)
                assert isinstance(cell, MachineCodeEntryPoint)
                if cell.equalkey(*greenargs):
                    return cell.mc
                else:
                    return self.handle_hash_collision(cell, argshash,
                                                      *greenargs)
        maybe_compile._dont_inline_ = True

        def handle_hash_collision(self, cell, argshash, *greenargs):
            next = cell.next
            while not isinstance(next, Counter):
                assert isinstance(next, MachineCodeEntryPoint)
                if next.equalkey(*greenargs):
                    # found, move to the front of the linked list
                    cell.next = next.next
                    next.next = self.cells[argshash]
                    self.cells[argshash] = next
                    return next.mc
                cell = next
                next = cell.next
            # not found at all, do profiling
            interp = hotrunnerdesc.interpreter
            n = next.counter + 1
            if n < hotrunnerdesc.jitdrivercls.getcurrentthreshold():
                if hotrunnerdesc.verbose_level >= 3:
                    interp.debug_trace("jit_not_entered", *greenargs)
                cell.next = Counter(n)
                return self.NULL_MC
            interp.debug_trace("jit_compile", *greenargs)
            return self.compile(argshash, *greenargs)
        handle_hash_collision._dont_inline_ = True

        def getkeyhash(self, *greenargs):
            result = r_uint(0x345678)
            i = 0
            mult = r_uint(1000003)
            for TYPE in green_args_spec:
                if i > 0:
                    result = result * mult
                    mult = mult + 82520 + 2*len(greenargs)
                item = greenargs[i]
                result = result ^ cast_whatever_to_int(TYPE, item)
                i += 1
            return result
        getkeyhash._always_inline_ = True

        def compile(self, argshash, *greenargs):
            try:
                return self._compile(argshash, *greenargs)
            except Exception, e:
                rhotpath.report_compile_time_exception(
                    hotrunnerdesc.interpreter, e)
                return self.NULL_MC

        def _compile(self, argshash, *greenargs):
            interp = hotrunnerdesc.interpreter
            rgenop = interp.rgenop
            builder, gv_generated, inputargs_gv = rgenop.newgraph(
                hotrunnerdesc.sigtoken, "residual")

            jitstate = interp.fresh_jitstate(builder)
            redargs = ()
            red_i = 0
            for _, make_arg_redbox, _ in red_args_spec:
                gv_arg = inputargs_gv[red_i]
                box = make_arg_redbox(jitstate, inputargs_gv, red_i)
                redargs += (box,)
                red_i += make_arg_redbox.consumes
            redargs = list(redargs)

            greenargs_gv = [rgenop.genconst(greenargs[i])
                            for i in green_args_range]
            rhotpath.setup_jitstate(interp, jitstate, greenargs_gv, redargs,
                                    hotrunnerdesc.entryjitcode,
                                    hotrunnerdesc.sigtoken)
            builder.start_writing()
            rhotpath.compile(interp)
            builder.end()

            FUNCPTR = lltype.Ptr(hotrunnerdesc.RESIDUAL_FUNCTYPE)
            generated = gv_generated.revealconst(FUNCPTR)

            newcell = MachineCodeEntryPoint(generated, *greenargs)
            cell = self.cells[argshash]
            if not isinstance(cell, Counter):
                while True:
                    assert isinstance(cell, MachineCodeEntryPoint)
                    next = cell.next
                    if isinstance(next, Counter):
                        cell.next = Counter(0)
                        break
                    cell = next
                newcell.next = self.cells[argshash]
            self.cells[argshash] = newcell

            if not we_are_translated():
                hotrunnerdesc.residual_graph = generated._obj.graph  #for tests
            return generated

        def make_residualargs(self, *redargs):
            residualargs = ()
            i = 0
            for collect_residual_args, _, _ in red_args_spec:
                residualargs = residualargs + collect_residual_args(redargs[i])
                i += 1
            return residualargs
        make_residualargs._always_inline_ = True

    return HotEnterState
