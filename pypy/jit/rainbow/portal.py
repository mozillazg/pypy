from pypy.jit.hintannotator.model import originalconcretetype
from pypy.jit.timeshifter import rvalue, rcontainer
from pypy.objspace.flow import model as flowmodel
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.unroll import unrolling_iterable
from pypy.rpython.annlowlevel import llhelper, cachedtype
from pypy.rpython.llinterp import LLInterpreter
from pypy.rpython.lltypesystem import lltype, llmemory

# graph transformations for transforming the portal graph(s)
class PortalRewriter(object):
    def __init__(self, hintannotator, rtyper, RGenOp, codewriter,
                 translate_support_code = True):
        self.hintannotator = hintannotator
        self.rtyper = rtyper
        self.interpreter = codewriter.interpreter
        self.codewriter = codewriter
        self.RGenOp = RGenOp
        self.translate_support_code = translate_support_code

    def rewrite(self, origportalgraph, portalgraph, view=False):
        self.origportalgraph = origportalgraph
        self.portalgraph = portalgraph
        self.view = view
        self.readportalgraph = None
        self.make_args_specification()
        self.PortalState = make_state_class(
            self.args_specification, self.RESIDUAL_FUNCTYPE, self.sigtoken,
            self.codewriter.all_graphs[self.portalgraph],
            self.rtyper,
            self.codewriter)
        self.make_state_instance()
        self.mutate_origportalgraph()

    def make_args_specification(self):
        args_specification = []
        RESTYPE = originalconcretetype(
            self.hintannotator.binding(self.portalgraph.getreturnvar()))
        ARGS = []
        ORIGARGS = []
        for v in self.portalgraph.getargs():
            ORIGARGS.append(v.concretetype)
            binding = self.hintannotator.binding(v)
            concretetype = originalconcretetype(binding)
            if binding.is_green():
                arg_spec = "green", None, None, concretetype
            else:
                argdesc = getjitenterargdesc(concretetype, self.RGenOp)
                arg_spec = ("red", argdesc.residual_args_collector(),
                            argdesc.arg_redbox_maker(), concretetype)
                ARGS.extend(argdesc.residual_argtypes())
            args_specification.append(arg_spec)
        self.args_specification = args_specification
        self.RESIDUAL_FUNCTYPE = lltype.FuncType(ARGS, RESTYPE)
        self.PORTAL_FUNCTYPE = lltype.FuncType(ORIGARGS, RESTYPE)
        self.sigtoken = self.RGenOp.sigToken(self.RESIDUAL_FUNCTYPE)

    def make_state_instance(self):
        portalbytecode = self.codewriter.all_graphs[self.portalgraph]
        state = self.PortalState(self.interpreter, portalbytecode)
        def portal_entry(*args):
            return state.portal_entry(*args)
        self.state = state
        self.portal_entry = portal_entry
        self.interpreter.set_portalstate(state)

    def mutate_origportalgraph(self):
        if not self.translate_support_code:
            # this case is used for most tests: the jit stuff should be run
            # directly to make these tests faster
            portal_entry_graph_ptr = llhelper(lltype.Ptr(self.PORTAL_FUNCTYPE),
                                              self.portal_entry)
        else:
            # this translates portal_entry into low-level graphs, recursively
            # dragging the whole jit support code with it.  Depending on which
            # descs are reachable from the portalbytecode, this will create
            # the specialized versions of the support code as needed.
            from pypy.rpython import annlowlevel
            from pypy.annotation import model as annmodel
            annhelper = annlowlevel.MixLevelHelperAnnotator(self.rtyper)
            FUNC = self.PORTAL_FUNCTYPE
            RESFUNC = self.RESIDUAL_FUNCTYPE
            args_s = [annmodel.lltype_to_annotation(ARG) for ARG in FUNC.ARGS]
            s_result = annmodel.lltype_to_annotation(FUNC.RESULT)
            self.portal_entry_graph = annhelper.getgraph(
                self.portal_entry, args_s, s_result)
            portal_entry_graph_ptr = annhelper.graph2delayed(
                self.portal_entry_graph, FUNC)
            # debugging
            state = self.state
            def ll_get_residual_fnptr():
                return state.get_residual_fnptr()
            self.get_residual_fnptr_graph = annhelper.getgraph(
                ll_get_residual_fnptr, [],
                annmodel.lltype_to_annotation(lltype.Ptr(RESFUNC)))
            annhelper.finish()

        # the following gives a pdb prompt when portal_entry raises an exception
        portal_entry_graph_ptr._obj.__dict__['_debugexc'] = True
        # XXX hack hack hack
        args = [flowmodel.Constant(portal_entry_graph_ptr,
                                   lltype.Ptr(self.PORTAL_FUNCTYPE))]
        args += self.origportalgraph.getargs()
        result = flowmodel.Variable()
        result.concretetype = self.origportalgraph.getreturnvar().concretetype
        block = self.origportalgraph.startblock
        block.operations[:] = [
            flowmodel.SpaceOperation("direct_call", args, result)]
        block.exitswitch = None
        block.recloseblock(
            flowmodel.Link([result], self.origportalgraph.returnblock))


    def get_residual_graph(self, llinterp):
        # debugging helper
        portalstate = self.state
        if not self.translate_support_code:
            residual_graph_ptr = portalstate.get_residual_fnptr()
        else:
            residual_graph_ptr = llinterp.eval_graph(
                self.get_residual_fnptr_graph, [])
        residual_graph = residual_graph_ptr._obj.graph
        return residual_graph


def make_state_class(args_specification, RESIDUAL_FUNCTYPE, sigtoken,
                     portal_jitcode, rtyper, codewriter):
    args_specification = unrolling_iterable(args_specification)
    class PortalState(object):
        def __init__(self, interpreter, portalbytecode):
            self.cache = {}
            self.graph_compilation_queue = []
            self.interpreter = interpreter
            self.portalbytecode = portalbytecode
            self.sigtoken = sigtoken

        def compile_more_functions(self):
            while self.graph_compilation_queue:
                top_jitstate, greenargs, redargs = self.graph_compilation_queue.pop()
                builder = top_jitstate.curbuilder
                builder.start_writing()
                top_jitstate = self.interpreter.run(top_jitstate,
                                                    portal_jitcode,
                                                    greenargs, redargs)
                if top_jitstate is not None:
                    self.interpreter.finish_jitstate(sigtoken)
                builder.end()
                builder.show_incremental_progress()

        def make_key(self, *args):
            key = ()
            i = 0
            for color, collect_residual_args, _, _ in args_specification:
                if color == "green":
                    x = args[i]
                    if isinstance(lltype.typeOf(x), lltype.Ptr): 
                        x = llmemory.cast_ptr_to_adr(x)
                    key = key + (x,)
                i = i + 1
            return key

        def make_key_from_genconsts(self, green_gv):
            key = ()
            i = 0
            j = 0
            for color, collect_residual_args, _, TYPE in args_specification:
                if color == "green":
                    genconst = green_gv[j]
                    x = genconst.revealconst(TYPE)
                    if isinstance(TYPE, lltype.Ptr): 
                        x = llmemory.cast_ptr_to_adr(x)
                    key = key + (x,)
                    j += 1
                i = i + 1
            return key


        def make_residualargs(self, *args):
            residualargs = ()
            i = 0
            for color, collect_residual_args, _, _ in args_specification:
                if color != "green":
                    residualargs = residualargs + collect_residual_args(args[i])
                i = i + 1
            return residualargs

        def portal_entry(self, *args):
            i = 0
            cache = self.cache
            key = self.make_key(*args)
            try:
                gv_generated = cache[key]
            except KeyError:
                gv_generated = self.compile(key, *args)
            residualargs = self.make_residualargs(*args)

            fn = gv_generated.revealconst(lltype.Ptr(RESIDUAL_FUNCTYPE))
            if not we_are_translated():
                # run the generated code on top of the llinterp for testing
                exc_data_ptr = codewriter.exceptiondesc.exc_data_ptr
                llinterp = LLInterpreter(rtyper, exc_data_ptr=exc_data_ptr)
                res = llinterp.eval_graph(fn._obj.graph, residualargs)
                return res
            else:
                return fn(*residualargs)

        def portal_reentry(self, greenargs, redargs):
            jitstate = self.interpreter.jitstate
            curbuilder = jitstate.curbuilder
            rgenop = self.interpreter.rgenop
            i = 0
            cache = self.cache
            key = self.make_key_from_genconsts(greenargs)
            try:
                gv_generated = cache[key]
            except KeyError:
                builder, gv_generated, inputargs_gv = rgenop.newgraph(sigtoken,
                                                                      "generated")
                self.cache[key] = gv_generated
                top_jitstate = self.interpreter.fresh_jitstate(builder)
                newredargs = ()
                red_i = 0
                for color, _, make_arg_redbox, _ in args_specification:
                    if color == "red":
                        box = make_arg_redbox(top_jitstate, inputargs_gv, red_i)
                        red_i += make_arg_redbox.consumes
                        newredargs += (box,)
                newredargs = list(newredargs)

                self.graph_compilation_queue.append(
                    (top_jitstate, greenargs, newredargs))
            residualargs_gv = [box.getgenvar(jitstate) for box in redargs]

            gv_res = curbuilder.genop_call(sigtoken, gv_generated,
                                           residualargs_gv)
            self.interpreter.exceptiondesc.fetch_global_excdata(jitstate)

            RESTYPE = RESIDUAL_FUNCTYPE.RESULT
            boxbuilder = rvalue.ll_redboxbuilder(RESTYPE)

            if RESTYPE == lltype.Void:
                retbox = None
            else:
                retbox = boxbuilder(gv_res)
            jitstate.returnbox = retbox
            assert jitstate.next is None


        def compile(self, key, *args):
            portal_ts_args = ()
            rgenop = self.interpreter.rgenop
            builder, gv_generated, inputargs_gv = rgenop.newgraph(sigtoken,
                                                                  "generated")
            self.cache[key] = gv_generated
            top_jitstate = self.interpreter.fresh_jitstate(builder)
            greenargs = ()
            redargs = ()
            red_i = 0
            for color, _, make_arg_redbox, _ in args_specification:
                llvalue = args[0]
                args = args[1:]
                if color == "green":
                    greenargs += (rgenop.genconst(llvalue),)
                else:
                    box = make_arg_redbox(top_jitstate, inputargs_gv, red_i)
                    red_i += make_arg_redbox.consumes
                    redargs += (box,)
            greenargs = list(greenargs)
            redargs = list(redargs)

            self.graph_compilation_queue.append((top_jitstate, greenargs, redargs))
            self.compile_more_functions()
            return gv_generated

        
        # debug helpers
        def readportal(self, *args):
            i = 0
            key = ()
            for color, _, _, _ in args_specification:
                if color == "green":
                    x = args[i]
                    if isinstance(lltype.typeOf(x), lltype.Ptr): 
                        x = llmemory.cast_ptr_to_adr(x)
                    key = key + (x,)
                i = i + 1
            cache = self.cache
            try:
                gv_generated = cache[key]
            except KeyError:
                return lltype.nullptr(RESIDUAL_FUNCTYPE)
            fn = gv_generated.revealconst(lltype.Ptr(RESIDUAL_FUNCTYPE))
            return fn
            
        def readallportals(self):
            return [gv_gen.revealconst(lltype.Ptr(RESIDUAL_FUNCTYPE))
                    for gv_gen in self.cache.values()]

        def get_residual_fnptr(self):
            lst = self.readallportals()
            if len(lst) == 1:
                return lst[0]
            elif len(lst) == 0:
                raise Exception("no residual graph!")
            else:
                raise Exception("multiple residual graphs")

    return PortalState


def getjitenterargdesc(lowleveltype, RGenOp):
    assert not isinstance(lowleveltype, lltype.ContainerType)
    redportargdesccls = RedJitEnterArgDesc
    if isinstance(lowleveltype, lltype.Ptr):
        if isinstance(lowleveltype.TO, lltype.Struct):
            if lowleveltype.TO._hints.get('virtualizable', False):
                redportargdesccls = RedVirtualizableStructJitEnterArgDesc
    return redportargdesccls(lowleveltype, RGenOp)

class RedJitEnterArgDesc:
    __metaclass__ = cachedtype

    def __init__(self, original_concretetype, RGenOp):
        assert original_concretetype is not lltype.Void, (
            "cannot make red boxes for the lltype Void")
        self.original_concretetype = original_concretetype
        self.RGenOp = RGenOp
        self.build_portal_arg_helpers()

    def build_portal_arg_helpers(self):
        def collect_residual_args(v):
            return (v,)
        self.collect_residual_args = collect_residual_args

        TYPE = self.original_concretetype
        boxcls = rvalue.ll_redboxcls(TYPE)
        
        def make_arg_redbox(jitstate, inputargs_gv, i):
            gv_arg = inputargs_gv[i]
            box = boxcls(gv_arg)
            return box
        self.make_arg_redbox = make_arg_redbox
        make_arg_redbox.consumes = 1

    def residual_argtypes(self):
        return [self.original_concretetype]

    def residual_args_collector(self):
        return self.collect_residual_args

    def arg_redbox_maker(self):
        return self.make_arg_redbox


class RedVirtualizableStructJitEnterArgDesc(RedJitEnterArgDesc):
    typedesc = None
    _s_c_typedesc = None

    def gettypedesc(self):
        if self.typedesc is None:
            T = self.original_concretetype.TO
            self.typedesc = rcontainer.StructTypeDesc(self.RGenOp, T)
        return self.typedesc

    def build_portal_arg_helpers(self):
        typedesc = self.gettypedesc()
        redirected_fielddescs = unrolling_iterable(
                                    typedesc.redirected_fielddescs)
        TYPE = self.original_concretetype

        def make_arg_redbox(jitstate, inputargs_gv, i):
            box = typedesc.factory()
            jitstate.add_virtualizable(box)
            content = box.content
            assert isinstance(content, rcontainer.VirtualizableStruct)
            content_boxes = content.content_boxes
            gv_outside = inputargs_gv[i]
            i += 1
            for fieldesc, j in redirected_fielddescs:
                content_boxes[j] = fieldesc.makebox(None, inputargs_gv[i])
                i += 1
            content_boxes[-1] = rvalue.PtrRedBox(gv_outside,
                                                 known_nonzero = True)
            return box
        
        self.make_arg_redbox = make_arg_redbox
        make_arg_redbox.consumes = len(typedesc.redirected_fielddescs)+1

    def residual_argtypes(self):
        argtypes = [self.original_concretetype]
        typedesc = self.gettypedesc()
        for fielddesc, _ in typedesc.redirected_fielddescs:
            FIELDTYPE = fielddesc.RESTYPE
            argtypes.append(FIELDTYPE)
        return argtypes

    def residual_args_collector(self):
        typedesc = self.gettypedesc()
        return typedesc.collect_residual_args
    
