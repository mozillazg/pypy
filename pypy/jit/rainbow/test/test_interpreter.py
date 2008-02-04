import py
from pypy.translator.translator import TranslationContext, graphof
from pypy.jit.hintannotator.annotator import HintAnnotator
from pypy.jit.hintannotator.policy import StopAtXPolicy, HintAnnotatorPolicy
from pypy.jit.hintannotator.model import SomeLLAbstractConstant, OriginFlags
from pypy.jit.hintannotator.model import originalconcretetype
from pypy.jit.rainbow.bytecode import BytecodeWriter, label, tlabel, assemble
from pypy.jit.codegen.llgraph.rgenop import RGenOp as LLRGenOp
from pypy.jit.rainbow.test.test_serializegraph import AbstractSerializationTest
from pypy.jit.rainbow import bytecode
from pypy.jit.timeshifter import rtimeshift, exception, rvalue
from pypy.rpython.lltypesystem import lltype, rstr
from pypy.rpython.llinterp import LLInterpreter
from pypy.annotation import model as annmodel
from pypy.objspace.flow.model import summary
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

    RGenOp = LLRGenOp

    def setup_class(cls):
        from pypy.jit.timeshifter.test.conftest import option
        cls.on_llgraph = cls.RGenOp is LLRGenOp
        cls._cache = {}
        cls._cache_order = []

    def teardown_class(cls):
        del cls._cache
        del cls._cache_order

    def serialize(self, func, values, backendoptimize=False):
        key = func, backendoptimize
        try:
            cache, argtypes = self._cache[key]
        except KeyError:
            pass
        else:
            self.__dict__.update(cache)
            assert argtypes == getargtypes(self.rtyper.annotator, values)
            return self.writer, self.jitcode, self.argcolors

        if len(self._cache_order) >= 3:
            del self._cache[self._cache_order.pop(0)]
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
        writer = BytecodeWriter(t, hannotator, self.RGenOp)
        jitcode = writer.make_bytecode(graph2)
        argcolors = []

        # make residual functype
        ha = self.hannotator
        RESTYPE = originalconcretetype(hannotator.binding(graph2.getreturnvar()))
        ARGS = []
        for var in graph2.getargs():
            # XXX ignoring virtualizables for now
            binding = hannotator.binding(var)
            if not binding.is_green():
                ARGS.append(originalconcretetype(binding))
        self.RESIDUAL_FUNCTYPE = lltype.FuncType(ARGS, RESTYPE)

        for i, ll_val in enumerate(values):
            color = writer.varcolor(graph2.startblock.inputargs[i])
            argcolors.append(color)
        self.writer = writer
        self.jitcode = jitcode
        self.argcolors = argcolors

        cache = self.__dict__.copy()
        self._cache[key] = cache, getargtypes(rtyper.annotator, values)
        self._cache_order.append(key)
        return writer, jitcode, argcolors

    def interpret(self, ll_function, values, opt_consts=[], *args, **kwds):
        # XXX clean this mess up
        writer, jitcode, argcolors = self.serialize(ll_function, values)
        hrtyper = bytecode.PseudoHRTyper(RGenOp=writer.RGenOp,
                                         annotator=writer.translator.annotator,
                                         rtyper=writer.translator.annotator.base_translator.rtyper)
        edesc = exception.ExceptionDesc(hrtyper, False)
        rgenop = writer.RGenOp()
        sigtoken = rgenop.sigToken(self.RESIDUAL_FUNCTYPE)
        builder, gv_generated, inputargs_gv = rgenop.newgraph(sigtoken, "generated")
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
        red_i = 0
        for i, (color, ll_val) in enumerate(zip(argcolors, values)):
            if color == "green":
                greenargs.append(writer.RGenOp.constPrebuiltGlobal(ll_val))
            else:
                TYPE = lltype.typeOf(ll_val)
                kind = rgenop.kindToken(TYPE)
                boxcls = rvalue.ll_redboxcls(TYPE)
                if i in opt_consts:
                    gv_arg = rgenop.genconst(ll_val)
                else:
                    gv_arg = inputargs_gv[red_i]
                redargs.append(boxcls(kind, gv_arg))
                residualargs.append(ll_val)
                red_i += 1
        jitstate = writer.interpreter.run(jitstate, jitcode, greenargs, redargs)
        if jitstate is not None:
            ll_finish_jitstate(jitstate, edesc, sigtoken)
        builder.end()
        generated = gv_generated.revealconst(lltype.Ptr(self.RESIDUAL_FUNCTYPE))
        graph = generated._obj.graph
        self.residual_graph = graph
        if conftest.option.view:
            graph.show()
        llinterp = LLInterpreter(self.rtyper)
        res = llinterp.eval_graph(graph, residualargs)
        return res

    def check_insns(self, expected=None, **counts):
        self.insns = summary(self.residual_graph)
        if expected is not None:
            assert self.insns == expected
        for opname, count in counts.items():
            assert self.insns.get(opname, 0) == count

class SimpleTests(AbstractInterpretationTest):
    def test_simple_fixed(self):
        py.test.skip("green return")
        def ll_function(x, y):
            return hint(x + y, concrete=True)
        res = self.interpret(ll_function, [5, 7])
        assert res == 12
        self.check_insns({})

    def test_very_simple(self):
        def f(x, y):
            return x + y
        res = self.interpret(f, [1, 2])
        assert res == 3
        self.check_insns({"int_add": 1})

    def test_convert_const_to_red(self):
        def f(x):
            return x + 1
        res = self.interpret(f, [2])
        assert res == 3
        self.check_insns({"int_add": 1})

    def test_loop_convert_const_to_redbox(self):
        def ll_function(x, y):
            x = hint(x, concrete=True)
            tot = 0
            while x:    # conversion from green '0' to red 'tot'
                tot += y
                x -= 1
            return tot
        res = self.interpret(ll_function, [7, 2])
        assert res == 14
        self.check_insns({'int_add': 7})

    def test_green_switch(self):
        def f(green, x, y):
            green = hint(green, concrete=True)
            if green:
                return x + y
            return x - y
        res = self.interpret(f, [1, 1, 2])
        assert res == 3
        self.check_insns({"int_add": 1})
        res = self.interpret(f, [0, 1, 2])
        assert res == -1
        self.check_insns({"int_sub": 1})

    def test_simple_opt_const_propagation2(self):
        def ll_function(x, y):
            return x + y
        res = self.interpret(ll_function, [5, 7], [0, 1])
        assert res == 12
        self.check_insns({})

    def test_simple_opt_const_propagation1(self):
        def ll_function(x):
            return -x
        res = self.interpret(ll_function, [5], [0])
        assert res == -5
        self.check_insns({})

    def test_loop_folding(self):
        def ll_function(x, y):
            tot = 0
            x = hint(x, concrete=True)    
            while x:
                tot += y
                x -= 1
            return tot
        res = self.interpret(ll_function, [7, 2], [0, 1])
        assert res == 14
        self.check_insns({})

    def test_red_switch(self):
        def f(x, y):
            if x:
                return x
            return y
        res = self.interpret(f, [1, 2])
        assert res == 1

    def test_merge(self):
        def f(x, y, z):
            if x:
                a = y - z
            else:
                a = y + z
            return 1 + a
        res = self.interpret(f, [1, 2, 3])
        assert res == 0

    def test_loop_merging(self):
        def ll_function(x, y):
            tot = 0
            while x:
                tot += y
                x -= 1
            return tot
        res = self.interpret(ll_function, [7, 2], [])
        assert res == 14
        self.check_insns(int_add = 2,
                         int_is_true = 2)

        res = self.interpret(ll_function, [7, 2], [0])
        assert res == 14
        self.check_insns(int_add = 2,
                         int_is_true = 1)

        res = self.interpret(ll_function, [7, 2], [1])
        assert res == 14
        self.check_insns(int_add = 1,
                         int_is_true = 2)

        res = self.interpret(ll_function, [7, 2], [0, 1])
        assert res == 14
        self.check_insns(int_add = 1,
                         int_is_true = 1)

    def test_loop_merging2(self):
        def ll_function(x, y):
            tot = 0
            while x:
                if tot < 3:
                    tot *= y
                else:
                    tot += y
                x -= 1
            return tot
        res = self.interpret(ll_function, [7, 2])
        assert res == 0

    def test_two_loops_merging(self):
        def ll_function(x, y):
            tot = 0
            while x:
                tot += y
                x -= 1
            while y:
                tot += y
                y -= 1
            return tot
        res = self.interpret(ll_function, [7, 3], [])
        assert res == 27
        self.check_insns(int_add = 3,
                         int_is_true = 3)

    def test_convert_greenvar_to_redvar(self):
        def ll_function(x, y):
            hint(x, concrete=True)
            return x - y
        res = self.interpret(ll_function, [70, 4], [0])
        assert res == 66
        self.check_insns(int_sub = 1)
        res = self.interpret(ll_function, [70, 4], [0, 1])
        assert res == 66
        self.check_insns({})

    def test_green_across_split(self):
        def ll_function(x, y):
            hint(x, concrete=True)
            if y > 2:
                z = x - y
            else:
                z = x + y
            return z
        res = self.interpret(ll_function, [70, 4], [0])
        assert res == 66
        self.check_insns(int_add = 1,
                         int_sub = 1)

    def test_merge_const_before_return(self):
        def ll_function(x):
            if x > 0:
                y = 17
            else:
                y = 22
            x -= 1
            y += 1
            return y+x
        res = self.interpret(ll_function, [-70], [])
        assert res == 23-71
        self.check_insns({'int_gt': 1, 'int_add': 2, 'int_sub': 2})

    def test_merge_3_redconsts_before_return(self):
        def ll_function(x):
            if x > 2:
                y = hint(54, variable=True)
            elif x > 0:
                y = hint(17, variable=True)
            else:
                y = hint(22, variable=True)
            x -= 1
            y += 1
            return y+x
        res = self.interpret(ll_function, [-70], [])
        assert res == ll_function(-70)
        res = self.interpret(ll_function, [1], [])
        assert res == ll_function(1)
        res = self.interpret(ll_function, [-70], [])
        assert res == ll_function(-70)

    def test_merge_const_at_return(self):
        py.test.skip("green return")
        def ll_function(x):
            if x > 0:
                return 17
            else:
                return 22
        res = self.interpret(ll_function, [-70], [])
        assert res == 22
        self.check_insns({'int_gt': 1})

    def test_arith_plus_minus(self):
        def ll_plus_minus(encoded_insn, nb_insn, x, y):
            acc = x
            pc = 0
            while pc < nb_insn:
                op = (encoded_insn >> (pc*4)) & 0xF
                op = hint(op, concrete=True)
                if op == 0xA:
                    acc += y
                elif op == 0x5:
                    acc -= y
                pc += 1
            return acc
        assert ll_plus_minus(0xA5A, 3, 32, 10) == 42
        res = self.interpret(ll_plus_minus, [0xA5A, 3, 32, 10], [0, 1])
        assert res == 42
        self.check_insns({'int_add': 2, 'int_sub': 1})

    def test_call_simple(self):
        def ll_add_one(x):
            return x + 1
        def ll_function(y):
            return ll_add_one(y)
        res = self.interpret(ll_function, [5], [])
        assert res == 6
        self.check_insns({'int_add': 1})

    def test_call_2(self):
        def ll_add_one(x):
            return x + 1
        def ll_function(y):
            return ll_add_one(y) + y
        res = self.interpret(ll_function, [5], [])
        assert res == 11
        self.check_insns({'int_add': 2})

    def test_call_3(self):
        def ll_add_one(x):
            return x + 1
        def ll_two(x):
            return ll_add_one(ll_add_one(x)) - x
        def ll_function(y):
            return ll_two(y) * y
        res = self.interpret(ll_function, [5], [])
        assert res == 10
        self.check_insns({'int_add': 2, 'int_sub': 1, 'int_mul': 1})

    def test_call_4(self):
        def ll_two(x):
            if x > 0:
                return x + 5
            else:
                return x - 4
        def ll_function(y):
            return ll_two(y) * y

        res = self.interpret(ll_function, [3], [])
        assert res == 24
        self.check_insns({'int_gt': 1, 'int_add': 1,
                          'int_sub': 1, 'int_mul': 1})

        res = self.interpret(ll_function, [-3], [])
        assert res == 21
        self.check_insns({'int_gt': 1, 'int_add': 1,
                          'int_sub': 1, 'int_mul': 1})

    def test_void_call(self):
        def ll_do_nothing(x):
            pass
        def ll_function(y):
            ll_do_nothing(y)
            return y

        res = self.interpret(ll_function, [3], [])
        assert res == 3

    def test_green_call(self):
        def ll_add_one(x):
            return x+1
        def ll_function(y):
            z = ll_add_one(y)
            z = hint(z, concrete=True)
            return hint(z, variable=True)

        res = self.interpret(ll_function, [3], [0])
        assert res == 4
        self.check_insns({})

    def test_split_on_green_return(self):
        def ll_two(x):
            if x > 0:
                return 17
            else:
                return 22
        def ll_function(x):
            n = ll_two(x)
            return hint(n+1, variable=True)
        res = self.interpret(ll_function, [-70], [])
        assert res == 23
        self.check_insns({'int_gt': 1})

class TestLLType(SimpleTests):
    type_system = "lltype"
