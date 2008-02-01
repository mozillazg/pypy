from pypy.translator.translator import TranslationContext, graphof
from pypy.jit.hintannotator.annotator import HintAnnotator
from pypy.jit.hintannotator.policy import StopAtXPolicy, HintAnnotatorPolicy
from pypy.jit.hintannotator.model import SomeLLAbstractConstant, OriginFlags
from pypy.jit.hintannotator.model import originalconcretetype
from pypy.jit.rainbow.bytecode import BytecodeWriter, label, tlabel, assemble
from pypy.jit.codegen.llgraph.rgenop import RGenOp
from pypy.jit.rainbow.test.test_serializegraph import AbstractSerializationTest
from pypy.jit.rainbow import bytecode
from pypy.jit.timeshifter import rtimeshift, exception, rvalue
from pypy.rpython.lltypesystem import lltype, rstr
from pypy.rpython.llinterp import LLInterpreter
from pypy.annotation import model as annmodel
from pypy.rlib.jit import hint
from pypy import conftest

def getargtypes(annotator, values):
    return [annotation(annotator, x) for x in values]

def annotation(a, x):
    T = lltype.typeOf(x)
    if T == lltype.Ptr(rstr.STR):
        t = str
    else:
        t = annmodel.lltype_to_annotation(T)
    return a.typeannotation(t)

P_OOPSPEC_NOVIRTUAL = HintAnnotatorPolicy(oopspec=True,
                                          novirtualcontainer=True,
                                          entrypoint_returns_red=False)

class AbstractInterpretationTest(object):

    def serialize(self, func, values, backendoptimize=False):
        # build the normal ll graphs for ll_function
        t = TranslationContext()
        a = t.buildannotator()
        argtypes = getargtypes(a, values)
        a.build_types(func, argtypes)
        rtyper = t.buildrtyper(type_system = self.type_system)
        rtyper.specialize()
        self.rtyper = rtyper
        if backendoptimize:
            from pypy.translator.backendopt.all import backend_optimizations
            backend_optimizations(t)
        graph1 = graphof(t, func)

        # build hint annotator types
        hannotator = HintAnnotator(base_translator=t, policy=P_OOPSPEC_NOVIRTUAL)
        hs = hannotator.build_types(graph1, [SomeLLAbstractConstant(v.concretetype,
                                                                    {OriginFlags(): True})
                                             for v in graph1.getargs()])
        hannotator.simplify()
        t = hannotator.translator
        self.hannotator = hannotator
        if conftest.option.view:
            t.view()
        graph2 = graphof(t, func)
        self.graph = graph2
        writer = BytecodeWriter(t, hannotator, RGenOp)
        jitcode = writer.make_bytecode(graph2)
        argcolors = []
        for i, ll_val in enumerate(values):
            color = writer.varcolor(graph2.startblock.inputargs[i])
            argcolors.append(color)
        return writer, jitcode, argcolors

    def interpret(self, ll_function, values, opt_consts=[], *args, **kwds):
        # XXX clean this mess up
        writer, jitcode, argcolors = self.serialize(ll_function, values)
        hrtyper = bytecode.PseudoHRTyper(RGenOp=writer.RGenOp,
                                         annotator=writer.translator.annotator,
                                         rtyper=writer.translator.annotator.base_translator.rtyper)
        edesc = exception.ExceptionDesc(hrtyper, False)
        rgenop = writer.RGenOp()
        # make residual functype
        FUNC = lltype.FuncType([lltype.Signed], lltype.Signed)
        ha = self.hannotator
        RESTYPE = originalconcretetype(self.hannotator.binding(self.graph.getreturnvar()))
        ARGS = []
        for var in self.graph.getargs():
            # XXX ignoring virtualizables for now
            binding = self.hannotator.binding(var)
            if not binding.is_green():
                ARGS.append(originalconcretetype(binding))
        FUNC = lltype.FuncType(ARGS, RESTYPE)
        sigtoken = rgenop.sigToken(FUNC)
        builder, gv_generated, inputargs_gv = rgenop.newgraph(sigtoken, "generated")
        print builder, builder.rgenop, rgenop
        builder.start_writing()
        jitstate = rtimeshift.JITState(builder, None,
                                       edesc.null_exc_type_box,
                                       edesc.null_exc_value_box)
        def ll_finish_jitstate(jitstate, exceptiondesc, graphsigtoken):
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
        # build arguments
        greenargs = []
        redargs = []
        residualargs = []
        i = 0
        for color, ll_val in zip(argcolors, values):
            if color == "green":
                greenargs.append(writer.RGenOp.constPrebuiltGlobal(ll_val))
            else:
                TYPE = lltype.typeOf(ll_val)
                kind = rgenop.kindToken(TYPE)
                boxcls = rvalue.ll_redboxcls(TYPE)
                redargs.append(boxcls(kind, inputargs_gv[i]))
                residualargs.append(ll_val)
                i += 1
        writer.interpreter.run(jitstate, jitcode, greenargs, redargs)
        ll_finish_jitstate(writer.interpreter.jitstate, edesc, sigtoken)
        builder.end()
        generated = gv_generated.revealconst(lltype.Ptr(FUNC))
        graph = generated._obj.graph
        if conftest.option.view:
            graph.show()
        llinterp = LLInterpreter(self.rtyper)
        res = llinterp.eval_graph(graph, residualargs)
        return res

    def Xtest_return_green(self):
        def f():
            return 1
        self.interpret(f, [])

    def test_very_simple(self):
        def f(x, y):
            return x + y
        res = self.interpret(f, [1, 2])
        assert res == 3

    def test_green_switch(self):
        def f(green, x, y):
            green = hint(green, concrete=True)
            if green:
                return x + y
            return x - y
        res = self.interpret(f, [1, 1, 2])
        assert res == 3
        res = self.interpret(f, [0, 1, 2])
        assert res == -1

class TestLLType(AbstractInterpretationTest):
    type_system = "lltype"
