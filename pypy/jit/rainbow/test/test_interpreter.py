import py
from pypy.translator.translator import TranslationContext, graphof
from pypy.translator.simplify import simplify_graph
from pypy.jit.codegen.llgraph.rgenop import RGenOp as LLRGenOp
from pypy.jit.hintannotator.annotator import HintAnnotator
from pypy.jit.hintannotator.policy import StopAtXPolicy, HintAnnotatorPolicy
from pypy.jit.hintannotator.model import SomeLLAbstractConstant, OriginFlags
from pypy.jit.hintannotator.model import originalconcretetype
from pypy.jit.rainbow.codewriter import LLTypeBytecodeWriter, OOTypeBytecodeWriter, label, tlabel, assemble
from pypy.jit.rainbow.portal import PortalRewriter
from pypy.jit.rainbow.test.test_serializegraph import AbstractSerializationTest
from pypy.jit.timeshifter import rtimeshift, rvalue
from pypy.rpython.lltypesystem import lltype, rstr
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.llinterp import LLInterpreter, LLException
from pypy.rpython.module.support import LLSupport
from pypy.annotation import model as annmodel
from pypy.annotation.policy import AnnotatorPolicy
from pypy.objspace.flow.model import summary, Variable
from pypy.rlib.debug import ll_assert
from pypy.rlib.jit import hint
from pypy.rlib.objectmodel import keepalive_until_here
from pypy.rlib.rarithmetic import ovfcheck
from pypy import conftest

import sys

P_NOVIRTUAL = HintAnnotatorPolicy(novirtualcontainer=True)
P_OOPSPEC = HintAnnotatorPolicy(novirtualcontainer=True, oopspec=True)
P_OOPSPEC_NOVIRTUAL = HintAnnotatorPolicy(oopspec=True,
                                          novirtualcontainer=True,
                                          entrypoint_returns_red=False)

def getargtypes(annotator, values):
    if values is None:    # for backend tests producing stand-alone exe's
        from pypy.annotation.listdef import s_list_of_strings
        return [s_list_of_strings]
    return [annotation(annotator, x) for x in values]

def annotation(a, x):
    T = lltype.typeOf(x)
    if T == lltype.Ptr(rstr.STR):
        t = str
    else:
        t = annmodel.lltype_to_annotation(T)
    return a.typeannotation(t)



def hannotate(func, values, policy=None, inline=None, backendoptimize=False,
              portal=None, type_system="lltype"):
    # build the normal ll graphs for ll_function
    t = TranslationContext()
    annpolicy = AnnotatorPolicy()
    annpolicy.allow_someobjects = False
    a = t.buildannotator(policy=annpolicy)
    argtypes = getargtypes(a, values)
    a.build_types(func, argtypes)
    rtyper = t.buildrtyper(type_system = type_system)
    rtyper.specialize()
    if inline:
        auto_inlining(t, threshold=inline)
    if backendoptimize:
        from pypy.translator.backendopt.all import backend_optimizations
        backend_optimizations(t, inline_threshold=inline or 0)
    if portal is None:
        portal = func

    if hasattr(policy, "seetranslator"):
        policy.seetranslator(t)
    graph1 = graphof(t, portal)
    # build hint annotator types
    if policy.hotpath:
        from pypy.jit.hintannotator.hotpath import HotPathHintAnnotator
        hannotator = HotPathHintAnnotator(base_translator=t, policy=policy)
        hs = hannotator.build_hotpath_types()
    else:
        hannotator = HintAnnotator(base_translator=t, policy=policy)
        hs = hannotator.build_types(graph1,
            [SomeLLAbstractConstant(v.concretetype, {OriginFlags(): True})
             for v in graph1.getargs()])
    hannotator.simplify()
    if conftest.option.view:
        hannotator.translator.view()
    return hs, hannotator, rtyper


class InterpretationTest(object):

    RGenOp = LLRGenOp
    small = False
    translate_support_code = False       # only works for portal tests for now

    # these staticmethods should go to TestLLType, they are here only
    # for compatibility with other tests that inherit from
    # InterpretationTest
    
    @staticmethod
    def Ptr(T):
        return lltype.Ptr(T)

    @staticmethod
    def GcStruct(name, *fields, **kwds):
        S = lltype.GcStruct(name, *fields, **kwds)
        return S

    malloc = staticmethod(lltype.malloc)
    nullptr = staticmethod(lltype.nullptr)

    @staticmethod
    def malloc_immortal(T):
        return lltype.malloc(T, immortal=True)

    def setup_class(cls):
        cls.on_llgraph = cls.RGenOp is LLRGenOp
        cls._cache = {}
        cls._cache_order = []

    def teardown_class(cls):
        del cls._cache
        del cls._cache_order

    def create_writer(self, t, hannotator, RGenOp):
        if self.type_system == 'lltype':
            return LLTypeBytecodeWriter(t, hannotator, self.RGenOp)
        else:
            return OOTypeBytecodeWriter(t, hannotator, self.RGenOp)

    def _serialize(self, func, values, policy=None,
                  inline=None, backendoptimize=False,
                  portal=None):
        if len(self._cache_order) >= 3:
            del self._cache[self._cache_order.pop(0)]
        # build the normal ll graphs for ll_function
        if policy is None:
            policy = P_OOPSPEC_NOVIRTUAL
        if portal is None:
            portal = func
        hs, hannotator, rtyper = hannotate(func, values, policy, inline,
                                           backendoptimize, portal,
                                           type_system=self.type_system)
        self.rtyper = rtyper
        self.hintannotator = hannotator
        t = hannotator.translator
        if policy.hotpath:
            graph2 = t.graphs[0]
        else:
            graph2 = graphof(t, portal)
            self.graph = graph2
            self.maingraph = graphof(rtyper.annotator.translator, func)
        writer = self.create_writer(t, hannotator, self.RGenOp)
        jitcode = writer.make_bytecode(graph2)
        # the bytecode writer can ask for llhelpers about lists and dicts
        rtyper.specialize_more_blocks() 
        self.writer = writer
        self.jitcode = jitcode

        if policy.hotpath:
            return


        # rewire the original portal

        rewriter = PortalRewriter(self.hintannotator, self.rtyper, self.RGenOp,
                                  writer, self.translate_support_code)
        self.rewriter = rewriter
        origportalgraph = graphof(self.rtyper.annotator.translator, portal)
        portalgraph = graphof(t, portal)
        rewriter.rewrite(origportalgraph=origportalgraph,
                         portalgraph=portalgraph,
                         view = conftest.option.view and self.small)
        self.RESIDUAL_FUNCTYPE = rewriter.RESIDUAL_FUNCTYPE


    def serialize(self, func, values, policy=None,
                  inline=None, backendoptimize=False,
                  portal=None, **kwds):
        key = func, backendoptimize
        try:
            cache, argtypes = self._cache[key]
        except KeyError:
            pass
        else:
            self.__dict__.update(cache)
            assert argtypes == getargtypes(self.rtyper.annotator, values)
            return self.writer, self.jitcode
        if len(self._cache_order) >= 3:
            del self._cache[self._cache_order.pop(0)]
        self._serialize(func, values, policy, inline, backendoptimize, portal)
        cache = self.__dict__.copy()
        self._cache[key] = cache, getargtypes(self.rtyper.annotator, values)
        self._cache_order.append(key)
        return self.writer, self.jitcode

    def interpret(self, ll_function, values, opt_consts=[], *args, **kwds):
        if hasattr(ll_function, 'convert_arguments'):
            assert len(ll_function.convert_arguments) == len(values)
            values = [decoder(value) for decoder, value in zip(
                                        ll_function.convert_arguments, values)]
        writer, jitcode= self.serialize(ll_function, values, **kwds)
        argcolors = []
        for i, ll_val in enumerate(values):
            color = writer.varcolor(self.graph.startblock.inputargs[i])
            argcolors.append(color)
        rgenop = writer.interpreter.rgenop
        sigtoken = rgenop.sigToken(self.RESIDUAL_FUNCTYPE)
        builder, gv_generated, inputargs_gv = rgenop.newgraph(sigtoken, "generated")
        builder.start_writing()
        jitstate = writer.interpreter.fresh_jitstate(builder)
        
        # build arguments
        greenargs = []
        redargs = []
        residualargs = []
        red_i = 0
        for i, (color, ll_val) in enumerate(zip(argcolors, values)):
            if color == "green":
                greenargs.append(rgenop.genconst(ll_val))
            else:
                TYPE = lltype.typeOf(ll_val)
                boxcls = rvalue.ll_redboxcls(TYPE)
                if i in opt_consts:
                    gv_arg = rgenop.genconst(ll_val)
                else:
                    gv_arg = inputargs_gv[red_i]
                redargs.append(boxcls(gv_arg))
                residualargs.append(ll_val)
                red_i += 1
        jitstate = writer.interpreter.run(jitstate, jitcode, greenargs, redargs)
        if jitstate is not None:
            writer.interpreter.finish_jitstate(sigtoken)
        builder.end()
        generated = gv_generated.revealconst(lltype.Ptr(self.RESIDUAL_FUNCTYPE))
        graph = generated._obj.graph
        self.residual_graph = graph
        if conftest.option.view:
            graph.show()
        llinterp = LLInterpreter(
            self.rtyper, exc_data_ptr=writer.exceptiondesc.exc_data_ptr)

        if 'check_raises' not in kwds:
            res = llinterp.eval_graph(graph, residualargs)
        else:
            try:
                llinterp.eval_graph(graph, residualargs)
            except LLException, e:
                exc = kwds['check_raises']
                assert llinterp.find_exception(e) is exc, (
                    "wrong exception type")
            else:
                raise AssertionError("DID NOT RAISE")
            return True
        return res

    def interpret_raises(self, ExcCls, ll_function, values, opt_consts=[],
                         *args, **kwds):
        kwds['check_raises'] = ExcCls
        return self.interpret(ll_function, values, opt_consts, *args, **kwds)

    def get_residual_graph(self):
        return self.residual_graph

    def simplify_graph(self):
        graph = self.get_residual_graph()
        simplify_graph(graph)

    def check_insns(self, expected=None, **counts):
        graph = self.get_residual_graph()
        self.insns = summary(graph)
        if expected is not None:
            expected = self.translate_insns(expected)
            assert self.insns == expected
        counts = self.translate_insns(counts)
        for opname, count in counts.items():
            assert self.insns.get(opname, 0) == count

    def translate_insns(self, insns):
        return insns

    def check_oops(self, expected=None, **counts):
        if not self.on_llgraph:
            return
        oops = {}
        residual_graph = self.get_residual_graph()
        for block in residual_graph.iterblocks():
            for op in block.operations:
                if op.opname == 'direct_call':
                    f = getattr(op.args[0].value._obj, "_callable", None)
                    if hasattr(f, 'oopspec'):
                        name, _ = f.oopspec.split('(', 1)
                        oops[name] = oops.get(name, 0) + 1
        if expected is not None:
            assert oops == expected
        for name, count in counts.items():
            assert oops.get(name, 0) == count

    def check_flexswitches(self, expected_count):
        residual_graph = self.get_residual_graph()
        count = 0
        for block in residual_graph.iterblocks():
            if (isinstance(block.exitswitch, Variable) and
                block.exitswitch.concretetype is lltype.Signed):
                count += 1
        assert count == expected_count

class SimpleTests(InterpretationTest):
    small = True

    def test_simple_fixed(self):
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

    def test_call_5(self):
        def ll_two(x):
            if x > 0:
                return x + 5
            else:
                return x - 4
        def ll_function(y):
            if y > 2:
                return ll_two(y) * y
            else:
                return ll_two(y + 3) * y

        res = self.interpret(ll_function, [3], [])
        assert res == 24
        self.check_insns({'int_gt': 3, 'int_add': 3,
                          'int_sub': 2, 'int_mul': 2})

        res = self.interpret(ll_function, [-3], [])
        assert res == 12
        self.check_insns({'int_gt': 3, 'int_add': 3,
                          'int_sub': 2, 'int_mul': 2})

    def test_call_6(self):
        def ll_two(x):
            if x > 0:
                return x + 5
            else:
                return x - 4
        def ll_function(y):
            if y > 2:
                y -= 2
            return ll_two(y) * y

        res = self.interpret(ll_function, [3], [])
        assert res == 6
        self.check_insns({'int_gt': 2, 'int_add': 1,
                          'int_sub': 2, 'int_mul': 1})

        res = self.interpret(ll_function, [-3], [])
        assert res == 21
        self.check_insns({'int_gt': 2, 'int_add': 1,
                          'int_sub': 2, 'int_mul': 1})

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
            return z

        res = self.interpret(ll_function, [3], [0])
        assert res == 4
        self.check_insns({})

    def test_green_call_void_return(self):
        def ll_boring(x):
            return
        def ll_function(y):
            z = ll_boring(y)
            z = hint(y, concrete=True)
            return z

        res = self.interpret(ll_function, [3], [0])
        assert res == 3
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

    def test_recursive_call(self):
        def indirection(n, fudge):
            return ll_pseudo_factorial(n, fudge)
        def ll_pseudo_factorial(n, fudge):
            k = hint(n, concrete=True)
            if n <= 0:
                return 1
            return n * ll_pseudo_factorial(n - 1, fudge + n) - fudge
        res = self.interpret(indirection, [4, 2], [0])
        expected = ll_pseudo_factorial(4, 2)
        assert res == expected
        

    def test_simple_struct(self):
        S = self.GcStruct('helloworld',
                          ('hello', lltype.Signed),
                          ('world', lltype.Signed),
                          hints={'immutable': True})
        malloc = self.malloc
        
        def ll_function(s):
            return s.hello * s.world

        def struct_S(string):
            items = string.split(',')
            assert len(items) == 2
            s1 = malloc(S)
            s1.hello = int(items[0])
            s1.world = int(items[1])
            return s1
        ll_function.convert_arguments = [struct_S]

        res = self.interpret(ll_function, ["6,7"], [])
        assert res == 42
        self.check_insns({'getfield': 2, 'int_mul': 1})
        res = self.interpret(ll_function, ["8,9"], [0])
        assert res == 72
        self.check_insns({})

    def test_simple_array(self):
        A = lltype.GcArray(lltype.Signed, 
                            hints={'immutable': True})
        def ll_function(a):
            return a[0] * a[1]

        def int_array(string):
            items = [int(x) for x in string.split(',')]
            n = len(items)
            a1 = lltype.malloc(A, n)
            for i in range(n):
                a1[i] = items[i]
            return a1
        ll_function.convert_arguments = [int_array]

        res = self.interpret(ll_function, ["6,7"], [])
        assert res == 42
        self.check_insns({'getarrayitem': 2, 'int_mul': 1})
        res = self.interpret(ll_function, ["8,3"], [0])
        assert res == 24
        self.check_insns({})

    def test_arraysize(self):
        A = lltype.GcArray(lltype.Signed)
        def ll_function(a):
            return len(a)

        def int_array(string):
            items = [int(x) for x in string.split(',')]
            n = len(items)
            a1 = lltype.malloc(A, n)
            for i in range(n):
                a1[i] = items[i]
            return a1
        ll_function.convert_arguments = [int_array]

        res = self.interpret(ll_function, ["6,7"], [])
        assert res == 2
        self.check_insns({'getarraysize': 1})
        res = self.interpret(ll_function, ["8,3,3,4,5"], [0])
        assert res == 5
        self.check_insns({})


    def test_simple_struct_malloc(self):
        py.test.skip("blue containers: to be reimplemented")
        S = lltype.GcStruct('helloworld', ('hello', lltype.Signed),
                                          ('world', lltype.Signed))               
        def ll_function(x):
            s = lltype.malloc(S)
            s.hello = x
            return s.hello + s.world

        res = self.interpret(ll_function, [3], [])
        assert res == 3
        self.check_insns({'int_add': 1})

        res = self.interpret(ll_function, [3], [0])
        assert res == 3
        self.check_insns({})

    def test_inlined_substructure(self):
        py.test.skip("blue containers: to be reimplemented")
        S = lltype.GcStruct('S', ('n', lltype.Signed))
        T = lltype.GcStruct('T', ('s', S), ('n', lltype.Float))
        def ll_function(k):
            t = lltype.malloc(T)
            t.s.n = k
            l = t.s.n
            return l
        res = self.interpret(ll_function, [7], [])
        assert res == 7
        self.check_insns({})

        res = self.interpret(ll_function, [7], [0])
        assert res == 7
        self.check_insns({})

    def test_degenerated_before_return(self):
        S = lltype.GcStruct('S', ('n', lltype.Signed))
        T = lltype.GcStruct('T', ('s', S), ('n', lltype.Float))
        malloc = self.malloc

        def ll_function(flag):
            t = lltype.malloc(T)
            t.s.n = 3
            s = lltype.malloc(S)
            s.n = 4
            if flag:
                s = t.s
            s.n += 1
            return s.n * t.s.n
        res = self.interpret(ll_function, [0], [])
        assert res == 5 * 3
        res = self.interpret(ll_function, [1], [])
        assert res == 4 * 4

    def test_degenerated_before_return_2(self):
        S = lltype.GcStruct('S', ('n', lltype.Signed))
        T = lltype.GcStruct('T', ('s', S), ('n', lltype.Float))

        def ll_function(flag):
            t = lltype.malloc(T)
            t.s.n = 3
            s = lltype.malloc(S)
            s.n = 4
            if flag:
                pass
            else:
                s = t.s
            s.n += 1
            return s.n * t.s.n
        res = self.interpret(ll_function, [1], [])
        assert res == 5 * 3
        res = self.interpret(ll_function, [0], [])
        assert res == 4 * 4

    def test_degenerated_at_return(self):
        S = lltype.GcStruct('S', ('n', lltype.Signed))
        T = lltype.GcStruct('T', ('s', S), ('n', lltype.Float))

        def ll_function(flag):
            t = lltype.malloc(T)
            t.n = 3.25
            t.s.n = 3
            s = lltype.malloc(S)
            s.n = 4
            if flag:
                s = t.s
            return s

        res = self.interpret(ll_function, [0], [])
        assert res.n == 4
        res = self.interpret(ll_function, [1], [])
        assert res.n == 3

    def test_degenerated_via_substructure(self):
        S = lltype.GcStruct('S', ('n', lltype.Signed))
        T = lltype.GcStruct('T', ('s', S), ('n', lltype.Float))

        def ll_function(flag):
            t = lltype.malloc(T)
            t.s.n = 3
            s = lltype.malloc(S)
            s.n = 7
            if flag:
                pass
            else:
                s = t.s
            t.s.n += 1
            return s.n * t.s.n
        res = self.interpret(ll_function, [1], [])
        assert res == 7 * 4
        res = self.interpret(ll_function, [0], [])
        assert res == 4 * 4

    def test_degenerate_with_voids(self):
        S = self.GcStruct('S', ('y', lltype.Void),
                               ('x', lltype.Signed))
        malloc = self.malloc
        def ll_function():
            s = malloc(S)
            s.x = 123
            return s
        res = self.interpret(ll_function, [], [])
        assert res.x == 123

    def test_plus_minus(self):
        def ll_plus_minus(s, x, y):
            acc = x
            n = len(s)
            pc = 0
            while pc < n:
                op = s[pc]
                op = hint(op, concrete=True)
                if op == '+':
                    acc += y
                elif op == '-':
                    acc -= y
                pc += 1
            return acc
        ll_plus_minus.convert_arguments = [LLSupport.to_rstr, int, int]
        res = self.interpret(ll_plus_minus, ["+-+", 0, 2], [0])
        assert res == ll_plus_minus("+-+", 0, 2)
        self.check_insns({'int_add': 2, 'int_sub': 1})

    def test_red_virtual_container(self):
        # this checks that red boxes are able to be virtualized dynamically by
        # the compiler (the P_NOVIRTUAL policy prevents the hint-annotator from
        # marking variables in blue)
        S = self.GcStruct('S', ('n', lltype.Signed))
        malloc = self.malloc
        def ll_function(n):
            s = malloc(S)
            s.n = n
            return s.n
        res = self.interpret(ll_function, [42], [])
        assert res == 42
        self.check_insns({})


    def test_setarrayitem(self):
        A = lltype.GcArray(lltype.Signed)
        a = lltype.malloc(A, 2, immortal=True)
        def ll_function():
            a[0] = 1
            a[1] = 2
            return a[0]+a[1]
        
        res = self.interpret(ll_function, [], [])
        assert res == 3

    def test_red_array(self):
        A = lltype.GcArray(lltype.Signed)
        def ll_function(x, y, n):
            a = lltype.malloc(A, 2)
            a[0] = x
            a[1] = y
            return a[n]*len(a)

        res = self.interpret(ll_function, [21, -21, 0], [])
        assert res == 42
        self.check_insns({'malloc_varsize': 1,
                          'setarrayitem': 2, 'getarrayitem': 1,
                          'getarraysize': 1, 'int_mul': 1})

        res = self.interpret(ll_function, [21, -21, 1], [])
        assert res == -42
        self.check_insns({'malloc_varsize': 1,
                          'setarrayitem': 2, 'getarrayitem': 1,
                          'getarraysize': 1, 'int_mul': 1})

    def test_red_struct_array(self):
        S = lltype.Struct('s', ('x', lltype.Signed))
        A = lltype.GcArray(S)
        def ll_function(x, y, n):
            a = lltype.malloc(A, 2)
            a[0].x = x
            a[1].x = y
            return a[n].x*len(a)

        res = self.interpret(ll_function, [21, -21, 0], [])
        assert res == 42
        self.check_insns({'malloc_varsize': 1,
                          'setinteriorfield': 2, 'getinteriorfield': 1,
                          'getarraysize': 1, 'int_mul': 1})

        res = self.interpret(ll_function, [21, -21, 1], [])
        assert res == -42
        self.check_insns({'malloc_varsize': 1,
                          'setinteriorfield': 2, 'getinteriorfield': 1,
                          'getarraysize': 1, 'int_mul': 1})


    def test_red_varsized_struct(self):
        A = lltype.Array(lltype.Signed)
        S = lltype.GcStruct('S', ('foo', lltype.Signed), ('a', A))
        def ll_function(x, y, n):
            s = lltype.malloc(S, 3)
            s.foo = len(s.a)-1
            s.a[0] = x
            s.a[1] = y
            return s.a[n]*s.foo

        res = self.interpret(ll_function, [21, -21, 0], [])
        assert res == 42
        self.check_insns(malloc_varsize=1,
                         getinteriorarraysize=1)

        res = self.interpret(ll_function, [21, -21, 1], [])
        assert res == -42
        self.check_insns(malloc_varsize=1,
                         getinteriorarraysize=1)

    def test_array_of_voids(self):
        A = lltype.GcArray(lltype.Void)
        def ll_function(n):
            a = lltype.malloc(A, 3)
            a[1] = None
            b = a[n]
            res = a, b
            keepalive_until_here(b)      # to keep getarrayitem around
            return res

        res = self.interpret(ll_function, [2], [])
        assert len(res.item0) == 3

    def test_red_propagate(self):
        S = self.GcStruct('S', ('n', lltype.Signed))
        malloc = self.malloc
        def ll_function(n, k):
            s = malloc(S)
            s.n = n
            if k < 0:
                return -123
            return s.n * k
        res = self.interpret(ll_function, [3, 8], [])
        assert res == 24
        self.check_insns({'int_lt': 1, 'int_mul': 1})

    def test_red_subcontainer(self):
        S = lltype.GcStruct('S', ('n', lltype.Signed))
        T = lltype.GcStruct('T', ('s', S), ('n', lltype.Float))
        def ll_function(k):
            t = lltype.malloc(T)
            s = t.s
            s.n = k
            if k < 0:
                return -123
            result = s.n * (k-1)
            keepalive_until_here(t)
            return result
        res = self.interpret(ll_function, [7], [])
        assert res == 42
        self.check_insns({'int_lt': 1, 'int_mul': 1, 'int_sub': 1})


    def test_red_subcontainer_cast(self):
        S = lltype.GcStruct('S', ('n', lltype.Signed))
        T = lltype.GcStruct('T', ('s', S), ('n', lltype.Float))
        def ll_function(k):
            t = lltype.malloc(T)
            s = lltype.cast_pointer(lltype.Ptr(S), t)
            s.n = k
            if k < 0:
                return -123
            result = s.n * (k-1)
            keepalive_until_here(t)
            return result
        res = self.interpret(ll_function, [7], [])
        assert res == 42
        self.check_insns({'int_lt': 1, 'int_mul': 1, 'int_sub': 1})


    def test_merge_structures(self):
        S = self.GcStruct('S', ('n', lltype.Signed))
        T = self.GcStruct('T', ('s', self.Ptr(S)), ('n', lltype.Signed))
        malloc = self.malloc

        def ll_function(flag):
            if flag:
                s = malloc(S)
                s.n = 1
                t = malloc(T)
                t.s = s
                t.n = 2
            else:
                s = malloc(S)
                s.n = 5
                t = malloc(T)
                t.s = s
                t.n = 6
            return t.n + t.s.n
        res = self.interpret(ll_function, [0], [])
        assert res == 5 + 6
        self.check_insns({'int_is_true': 1, 'int_add': 1})
        res = self.interpret(ll_function, [1], [])
        assert res == 1 + 2
        self.check_insns({'int_is_true': 1, 'int_add': 1})


    def test_green_with_side_effects(self):
        S = self.GcStruct('S', ('flag', lltype.Bool))
        s = self.malloc(S)
        s.flag = False
        def ll_set_flag(s):
            s.flag = True
        def ll_function():
            s.flag = False
            ll_set_flag(s)
            return s.flag
        res = self.interpret(ll_function, [], [])
        assert res == True
        self.check_insns({'setfield': 2, 'getfield': 1})

    def test_deepfrozen_interior(self):
        T = lltype.Struct('T', ('x', lltype.Signed))
        A = lltype.Array(T)
        S = lltype.GcStruct('S', ('a', A))
        s = lltype.malloc(S, 3, zero=True)
        s.a[2].x = 42
        def f(n):
            s1 = hint(s, variable=True)
            s1 = hint(s1, deepfreeze=True)
            return s1.a[n].x

        # malloc-remove the interior ptr
        res = self.interpret(f, [2], [0], backendoptimize=True)
        assert res == 42
        self.check_insns({})

    def test_compile_time_const_tuple(self):
        d = {(4, 5): 42, (6, 7): 12}
        def f(a, b):
            d1 = hint(d, deepfreeze=True)
            return d1[a, b]

        # malloc-remove the interior ptr
        res = self.interpret(f, [4, 5], [0, 1],
                             backendoptimize=True)
        assert res == 42
        self.check_insns({})

    def test_residual_red_call(self):
        def g(x):
            return x+1

        def f(x):
            return 2*g(x)

        res = self.interpret(f, [20], [], policy=StopAtXPolicy(g))
        assert res == 42
        self.check_insns(int_add=0)

    def test_residual_red_call_with_exc(self):
        def h(x):
            if x > 0:
                return x+1
            else:
                raise ValueError

        def g(x):
            return 2*h(x)

        def f(x):
            hint(None, global_merge_point=True)
            try:
                return g(x)
            except ValueError:
                return 7

        stop_at_h = StopAtXPolicy(h)
        res = self.interpret(f, [20], [], policy=stop_at_h)
        assert res == 42
        self.check_insns(int_add=0)

        res = self.interpret(f, [-20], [], policy=stop_at_h)
        assert res == 7
        self.check_insns(int_add=0)

    def test_red_call_ignored_result(self):
        def g(n):
            return n * 7
        def f(n, m):
            g(n)   # ignore the result
            return m

        res = self.interpret(f, [4, 212], [], policy=P_NOVIRTUAL)
        assert res == 212

    def test_simple_meth(self):
        class Base(object):
            def m(self):
                raise NotImplementedError
            pass  # for inspect.getsource() bugs

        class Concrete(Base):
            def m(self):
                return 42
            pass  # for inspect.getsource() bugs

        def f(flag):
            if flag:
                o = Base()
            else:
                o = Concrete()
            return o.m()

        res = self.interpret(f, [0], [0], policy=P_NOVIRTUAL)
        assert res == 42
        self.check_insns({})

        res = self.interpret(f, [0], [], policy=P_NOVIRTUAL)
        assert res == 42
        self.check_insns(indirect_call=0)

    def test_simple_red_meth(self):
        class Base(object):
            def m(self, n):
                raise NotImplementedError
            pass  # for inspect.getsource() bugs

        class Concrete(Base):
            def m(self, n):
                return 21*n
            pass  # for inspect.getsource() bugs

        def f(flag, x):
            if flag:
                o = Base()
            else:
                o = Concrete()
            return o.m(x)

        res = self.interpret(f, [0, 2], [0], policy=P_NOVIRTUAL)
        assert res == 42
        self.check_insns({'int_mul': 1})

    def test_simple_red_meth_vars_around(self):
        class Base(object):
            def m(self, n):
                raise NotImplementedError
            pass  # for inspect.getsource() bugs

        class Concrete(Base):
            def m(self, n):
                return 21*n
            pass  # for inspect.getsource() bugs

        def f(flag, x, y, z):
            if flag:
                o = Base()
            else:
                o = Concrete()
            return (o.m(x)+y)-z

        res = self.interpret(f, [0, 2, 7, 5], [0], policy=P_NOVIRTUAL)
        assert res == 44
        self.check_insns({'int_mul': 1, 'int_add': 1, 'int_sub': 1})

    def test_green_red_mismatch_in_call(self):
        def add(a,b, u):
            return a+b

        def f(x, y, u):
            r = add(x+1,y+1, u)
            z = x+y
            z = hint(z, concrete=True) + r   # this checks that 'r' is green
            return hint(z, variable=True)

        res = self.interpret(f, [4, 5, 0], [], policy=P_NOVIRTUAL)
        assert res == 20


    def test_recursive_with_red_termination_condition(self):
        py.test.skip('Does not terminate')
        def indirection(n):
            return ll_factorial
        def ll_factorial(n):
            if n <= 0:
                return 1
            return n * ll_factorial(n - 1)

        res = self.interpret(indirection, [5], [])
        assert res == 120
        
    def test_simple_indirect_call(self):
        def g1(v):
            return v * 2

        def g2(v):
            return v + 2

        def f(flag, v):
            if hint(flag, concrete=True):
                g = g1
            else:
                g = g2
            return g(v)

        res = self.interpret(f, [0, 40], [0])
        assert res == 42
        self.check_insns({'int_add': 1})

    def test_normalize_indirect_call(self):
        def g1(v):
            return -17

        def g2(v):
            return v + 2

        def f(flag, v):
            if hint(flag, concrete=True):
                g = g1
            else:
                g = g2
            return g(v)

        res = self.interpret(f, [0, 40], [0])
        assert res == 42
        self.check_insns({'int_add': 1})

        res = self.interpret(f, [1, 40], [0])
        assert res == -17
        self.check_insns({})

    def test_normalize_indirect_call_more(self):
        def g1(v):
            if v >= 0:
                return -17
            else:
                return -155

        def g2(v):
            return v + 2

        def f(flag, v):
            w = g1(v)
            if hint(flag, concrete=True):
                g = g1
            else:
                g = g2
            return g(v) + w

        res = self.interpret(f, [0, 40], [0])
        assert res == 25
        self.check_insns({'int_add': 2, 'int_ge': 1})

        res = self.interpret(f, [1, 40], [0])
        assert res == -34
        self.check_insns({'int_ge': 2, 'int_add': 1})

        res = self.interpret(f, [0, -1000], [0])
        assert res == f(False, -1000)
        self.check_insns({'int_add': 2, 'int_ge': 1})

        res = self.interpret(f, [1, -1000], [0])
        assert res == f(True, -1000)
        self.check_insns({'int_ge': 2, 'int_add': 1})

    def test_green_char_at_merge(self):
        def f(c, x):
            c = chr(c)
            c = hint(c, concrete=True)
            if x:
                x = 3
            else:
                x = 1
            c = hint(c, variable=True)
            return len(c*x)

        res = self.interpret(f, [ord('a'), 1], [], policy=P_NOVIRTUAL)
        assert res == 3

        res = self.interpret(f, [ord('b'), 0], [], policy=P_NOVIRTUAL)
        assert res == 1

    def test_self_referential_structures(self):
        S = lltype.GcForwardReference()
        S.become(lltype.GcStruct('s',
                                 ('ps', lltype.Ptr(S))))

        def f(x):
            s = lltype.malloc(S)
            if x:
                s.ps = lltype.malloc(S)
            return s
        def count_depth(s):
            x = 0
            while s:
                x += 1
                s = s.ps
            return x
        
        res = self.interpret(f, [3], [], policy=P_NOVIRTUAL)
        assert count_depth(res) == 2

    def test_known_nonzero(self):
        S = self.GcStruct('s', ('x', lltype.Signed))
        malloc = self.malloc
        nullptr = self.nullptr
        global_s = self.malloc_immortal(S)
        global_s.x = 100

        def h():
            s = malloc(S)
            s.x = 50
            return s
        def g(s, y):
            if s:
                return s.x * 5
            else:
                return -12 + y
        def f(x, y):
            hint(None, global_merge_point=True)
            x = hint(x, concrete=True)
            if x == 1:
                return g(nullptr(S), y)
            elif x == 2:
                return g(global_s, y)
            elif x == 3:
                s = malloc(S)
                s.x = y
                return g(s, y)
            elif x == 4:
                s = h()
                return g(s, y)
            else:
                s = h()
                if s:
                    return g(s, y)
                else:
                    return 0

        P = StopAtXPolicy(h)

        res = self.interpret(f, [1, 10], [0], policy=P)
        assert res == -2
        self.check_insns(int_mul=0, int_add=1)

        res = self.interpret(f, [2, 10], [0], policy=P)
        assert res == 500
        self.check_insns(int_mul=1, int_add=0)

        res = self.interpret(f, [3, 10], [0], policy=P)
        assert res == 50
        self.check_insns(int_mul=1, int_add=0)

        res = self.interpret(f, [4, 10], [0], policy=P)
        assert res == 250
        self.check_insns(int_mul=1, int_add=1)

        res = self.interpret(f, [5, 10], [0], policy=P)
        assert res == 250
        self.check_insns(int_mul=1, int_add=0)

    def test_debug_assert_ptr_nonzero(self):
        S = self.GcStruct('s', ('x', lltype.Signed))
        malloc = self.malloc
        def h():
            s = malloc(S)
            s.x = 42
            return s
        def g(s):
            # assumes that s is not null here
            ll_assert(bool(s), "please don't give me a null")
            return 5
        def f(m):
            hint(None, global_merge_point=True)
            s = h()
            n = g(s)
            if not s:
                n *= m
            return n

        P = StopAtXPolicy(h)

        res = self.interpret(f, [17], [], policy=P)
        assert res == 5
        self.check_insns(int_mul=0)

    def test_indirect_red_call(self):
        def h1(n):
            return n*2
        def h2(n):
            return n*4
        l = [h1, h2]
        def f(n, x):
            h = l[n&1]
            return h(n) + x

        P = StopAtXPolicy()
        res = self.interpret(f, [7, 3], policy=P)
        assert res == f(7,3)
        self.check_insns(indirect_call=1, direct_call=1)

    def test_indirect_red_call_with_exc(self):
        def h1(n):
            if n < 0:
                raise ValueError
            return n*2
        def h2(n):
            if n < 0:
                raise ValueError
            return n*4
        l = [h1, h2]
        def g(n, x):
            h = l[n&1]
            return h(n) + x

        def f(n, x):
            hint(None, global_merge_point=True)
            try:
                return g(n, x)
            except ValueError:
                return -1111

        P = StopAtXPolicy()
        res = self.interpret(f, [7, 3], policy=P)
        assert res == f(7,3)
        self.check_insns(indirect_call=1)

        res = self.interpret(f, [-7, 3], policy=P)
        assert res == -1111
        self.check_insns(indirect_call=1)

    def test_indirect_gray_call(self):
        def h1(w, n):
            w[0] =  n*2
        def h2(w, n):
            w[0] = n*4
        l = [h1, h2]
        def f(n, x):
            w = [0]
            h = l[n&1]
            h(w, n)
            return w[0] + x

        P = StopAtXPolicy()
        res = self.interpret(f, [7, 3], policy=P)
        assert res == f(7,3)

    def test_indirect_residual_red_call(self):
        def h1(n):
            return n*2
        def h2(n):
            return n*4
        l = [h1, h2]
        def f(n, x):
            h = l[n&1]
            return h(n) + x

        P = StopAtXPolicy(h1, h2)
        res = self.interpret(f, [7, 3], policy=P)
        assert res == f(7,3)
        self.check_insns(indirect_call=1)

    def test_constant_indirect_red_call(self):
        def h1(m, n, x):
            return x-2
        def h2(m, n, x):
            return x*4
        l = [h1, h2]
        def f(m, n, x):
            m = hint(m, concrete=True)
            frozenl = hint(l, deepfreeze=True)
            h = frozenl[n&1]
            return h(m, 5, x)

        P = StopAtXPolicy()
        res = self.interpret(f, [1, 7, 3], [0, 1], policy=P)
        assert res == f(1,7,3)
        self.check_insns({'int_mul': 1})
        res = self.interpret(f, [1, 4, 113], [0, 1], policy=P)
        assert res == f(1,4,113)
        self.check_insns({'int_sub': 1})

    def test_constant_indirect_red_call_no_result(self):
        class A:
            pass
        glob_a = A()
        def h1(m, n, x):
            glob_a.x = x-2
        def h2(m, n, x):
            glob_a.x = x*4
        l = [h1, h2]
        def f(m, n, x):
            m = hint(m, concrete=True)
            frozenl = hint(l, deepfreeze=True)
            h = frozenl[n&1]
            h(m, 5, x)
            return glob_a.x

        P = StopAtXPolicy()
        res = self.interpret(f, [1, 7, 3], [0, 1], policy=P)
        assert res == f(1,7,3)
        self.check_insns(int_mul=1, int_sub=0)
        res = self.interpret(f, [1, 4, 113], [0, 1], policy=P)
        assert res == f(1,4,113)
        self.check_insns(int_sub=1, int_mul=0)

    def test_indirect_sometimes_residual_pure_red_call(self):
        def h1(x):
            return x-2
        def h2(x):
            return x*4
        l = [h1, h2]
        def f(n, x):
            hint(None, global_merge_point=True)
            hint(n, concrete=True)
            frozenl = hint(l, deepfreeze=True)
            h = frozenl[n&1]
            return h(x)

        P = StopAtXPolicy(h1)
        P.oopspec = True
        res = self.interpret(f, [7, 3], [], policy=P)
        assert res == f(7,3)
        self.check_insns({'int_mul': 1})
        res = self.interpret(f, [4, 113], [], policy=P)
        assert res == f(4,113)
        self.check_insns({'direct_call': 1})

    def test_indirect_sometimes_residual_pure_but_fixed_red_call(self):
        def h1(x):
            return x-2
        def h2(x):
            return x*4
        l = [h1, h2]
        def f(n, x):
            hint(None, global_merge_point=True)
            frozenl = hint(l, deepfreeze=True)
            h = frozenl[n&1]
            z = h(x)
            hint(z, concrete=True)
            return z

        P = StopAtXPolicy(h1)
        P.oopspec = True
        res = self.interpret(f, [7, 3], [], policy=P)
        assert res == f(7,3)
        self.check_insns({})
        res = self.interpret(f, [4, 113], [], policy=P)
        assert res == f(4,113)
        self.check_insns({})

    def test_manual_marking_of_pure_functions(self):
        d = {}
        def h1(s):
            try:
                return d[s]
            except KeyError:
                d[s] = r = s * 15
                return r
        h1._pure_function_ = True
        def f(n):
            hint(None, global_merge_point=True)
            hint(n, concrete=True)
            if n == 0:
                s = 123
            else:
                s = 567
            a = h1(s)
            return hint(a, variable=True)

        P = StopAtXPolicy(h1)
        P.oopspec = True
        res = self.interpret(f, [0], [], policy=P)
        assert res == 123 * 15
        self.check_insns({})
        res = self.interpret(f, [4], [], policy=P)
        assert res == 567 * 15
        self.check_insns({})


    def test_red_int_add_ovf(self):
        def f(n, m):
            try:
                result = ovfcheck(n + m)
            except OverflowError:
                return -42 + m
            return result + 1

        res = self.interpret(f, [100, 20])
        assert res == 121
        self.check_insns(int_add_ovf=1)
        res = self.interpret(f, [100, 20], [0, 1])
        assert res == 121
        self.check_insns()

        res = self.interpret(f, [sys.maxint, 1])
        assert res == -41
        self.check_insns(int_add_ovf=1)
        res = self.interpret(f, [sys.maxint, 5], [0, 1])
        assert res == -42 + 5
        self.check_insns()

    def test_green_int_add_ovf(self):
        py.test.skip("not working yet")
        def f(n, m):
            try:
                res = ovfcheck(n + m)
            except OverflowError:
                res = -42
            hint(res, concrete=True)
            return res

        res = self.interpret(f, [100, 20])
        assert res == 120
        self.check_insns({})
        res = self.interpret(f, [sys.maxint, 1])
        assert res == -42
        self.check_insns({})

    def test_nonzeroness_assert_while_compiling(self):
        class X:
            pass
        class Y:
            pass

        def g(x, y):
            if y.flag:
                return x.value
            else:
                return -7

        def h(n):
            if n:
                x = X()
                x.value = n
                return x
            else:
                return None

        y = Y()

        def f(n):
            y.flag = True
            g(h(n), y)
            y.flag = False
            return g(h(0), y)

        res = self.interpret(f, [42], policy=P_NOVIRTUAL)
        assert res == -7

    def test_segfault_while_compiling(self):
        class X:
            pass
        class Y:
            pass

        def g(x, y):
            x = hint(x, deepfreeze=True)
            if y.flag:
                return x.value
            else:
                return -7

        def h(n):
            if n:
                x = X()
                x.value = n
                return x
            else:
                return None

        y = Y()

        def f(n):
            y.flag = True
            g(h(n), y)
            y.flag = False
            return g(h(0), y)

        res = self.interpret(f, [42], policy=P_NOVIRTUAL)
        assert res == -7

    def test_switch(self):
        def g(n, x):
            if n == 0:
                return 12 + x
            elif n == 1:
                return 34 + x
            elif n == 3:
                return 56 + x
            elif n == 7:
                return 78 + x
            else:
                return 90 + x
        def f(n, m):
            x = g(n, n)   # gives a red switch
            y = g(hint(m, concrete=True), n)   # gives a green switch
            return x - y

        res = self.interpret(f, [7, 2], backendoptimize=True)
        assert res == 78 - 90
        res = self.interpret(f, [8, 1], backendoptimize=True)
        assert res == 90 - 34

    def test_switch_char(self):
        def g(n, x):
            n = chr(n)
            if n == '\x00':
                return 12 + x
            elif n == '\x01':
                return 34 + x
            elif n == '\x02':
                return 56 + x
            elif n == '\x03':
                return 78 + x
            else:
                return 90 + x
        def f(n, m):
            x = g(n, n)   # gives a red switch
            y = g(hint(m, concrete=True), n)   # gives a green switch
            return x - y

        res = self.interpret(f, [3, 0], backendoptimize=True)
        assert res == 78 - 12
        res = self.interpret(f, [2, 4], backendoptimize=True)
        assert res == 56 - 90

    def test_simple_substitute_graph(self):

        class MetaG:
            def __init__(self, codewriter):
                pass

            def _freeze_(self):
                return True

            def metafunc(self, jitstate, abox, bbox):
                from pypy.jit.timeshifter.rvalue import IntRedBox
                builder = jitstate.curbuilder
                gv_result = builder.genop2("int_sub", abox.getgenvar(jitstate),
                                           bbox.getgenvar(jitstate))
                return IntRedBox(gv_result)

        def g(a, b):
            return a + b

        def f(a, b):
            x = g(a, b)
            y = g(b, a)
            return x + y

        class MyPolicy(HintAnnotatorPolicy):
            novirtualcontainer = True
            
            def look_inside_graph(self, graph):
                if graph.func is g:
                    return MetaG   # replaces g with a meta-call to metafunc()
                else:
                    return True

        res = self.interpret(f, [3, 6], policy=MyPolicy())
        assert res == 0
        self.check_insns({'int_add': 1, 'int_sub': 2})

    def test_substitute_graph_void(self):

        class MetaG:
            def __init__(self, codewriter):
                pass

            def _freeze_(self):
                return True

            def metafunc(self, jitstate, space, mbox):
                from pypy.jit.timeshifter.rvalue import IntRedBox
                builder = jitstate.curbuilder
                gv_result = builder.genop1("int_neg", mbox.getgenvar(jitstate))
                return IntRedBox(gv_result)

        class Fz(object):
            x = 10
            
            def _freeze_(self):
                return True

        def g(fz, m):
            return m * fz.x

        fz = Fz()

        def f(n, m):
            x = g(fz, n)
            y = g(fz, m)
            hint(y, concrete=True)
            return x + g(fz, y)

        class MyPolicy(HintAnnotatorPolicy):
            novirtualcontainer = True
            
            def look_inside_graph(self, graph):
                if graph.func is g:
                    return MetaG   # replaces g with a meta-call to metafunc()
                else:
                    return True

        res = self.interpret(f, [3, 6], policy=MyPolicy())
        assert res == -3 + 600
        self.check_insns({'int_neg': 1, 'int_add': 1})

    def test_hash_of_green_string_is_green(self):
        py.test.skip("unfortunately doesn't work")
        def f(n):
            if n == 0:
                s = "abc"
            elif n == 1:
                s = "cde"
            else:
                s = "fgh"
            return hash(s)

        res = self.interpret(f, [0])
        self.check_insns({'int_eq': 2})
        assert res == f(0)

    def test_misplaced_global_merge_point(self):
        def g(n):
            hint(None, global_merge_point=True)
            return n+1
        def f(n):
            hint(None, global_merge_point=True)
            return g(n)
        py.test.raises(AssertionError, self.interpret, f, [7], [])

    def test_learn_boolvalue(self):
        class A(object):
            pass
        def f(b, x):
            a = A()
            a.b = b
            if a.b:
                if a.b:
                    return 1 + x
                return -1 + x
            else:
                if not a.b:
                    return 2 + x
                return -2 + x
        res = self.interpret(f, [False, 5])
        assert res == 7
        self.check_insns({'int_add': 2})

    def test_learn_nonzeroness(self):
        class A:
            pass
        class B:
            pass
        def g(isnotnone):
            if isnotnone:
                return A()
            return None
        def f(isnotnone, x):
            hint(None, global_merge_point=True)
            a = g(isnotnone)
            b = B()
            b.a = a
            if b.a:
                if b.a:
                    return 1 + x
                return -1 + x
            else:
                if not b.a:
                    return 2 + x
                return -2 + x
        res = self.interpret(f, [False, 5], policy=StopAtXPolicy(g))
        assert res == 7
        self.check_insns(int_add=2)

    def test_ptrequality(self):
        class A(object):
            _immutable_ = True
            def __init__(self, a):
                self.a = a

        five = A(5)
        seven = A(7)

        def g(x):
            if x:
                return seven
            return five
        def f(green, red):
            hint(None, global_merge_point=True)
            hint(green, concrete=True)
            a = g(red)
            if green:
                b = seven
            else:
                b = five
            if a is b:
                return a.a
            return -1
        res = self.interpret(f, [True, True], policy=StopAtXPolicy(g))
        assert res == 7
        self.check_insns(getfield=0)

    # void tests
    def test_void_args(self):
        class Space(object):
            true = True
            false = False
            
            def is_true(self, x):
                if x:
                    return self.true
                return self.false

            def add(self, x, y):
                return x + y

            def sub(self, x, y):
                return x - y

            def _freeze_(self):
                return True

        def f(space, x, y):
            if space.is_true(x):
                return space.add(x, y)
            return space.sub(6, y)

        def main1(x, y):
            return f(space, x, y)

        space = Space()
        res = self.interpret(main1, [5, 6])
        assert res == 11

        def g(space, x, y):
            return space.add(x, y)

        def f(space, x, y):
            if space.is_true(x):
                return g(space, x, y)
            return space.sub(6, y)

        def main2(x, y):
            return f(space, x, y)
        res = self.interpret(main2, [5, 6], policy=StopAtXPolicy(g))
        assert res == 11

class TestLLType(SimpleTests):
    type_system = "lltype"

class TestOOType(SimpleTests):
    type_system = "ootype"

    @staticmethod
    def Ptr(T):
        return T

    @staticmethod
    def GcStruct(name, *fields, **kwds):
        if 'hints' in kwds:
            kwds['_hints'] = kwds['hints']
            del kwds['hints']
        I = ootype.Instance(name, ootype.ROOT, dict(fields), **kwds)
        return I

    malloc = staticmethod(ootype.new)
    nullptr = staticmethod(ootype.null)

    @staticmethod
    def malloc_immortal(T):
        return ootype.new(T)

    def translate_insns(self, insns):
        replace = {
            'getfield': 'oogetfield',
            'setfield': 'oosetfield',
            }

        insns = insns.copy()
        for a, b in replace.iteritems():
            if a in insns:
                assert b not in insns
                insns[b] = insns[a]
                del insns[a]
        return insns

    def _skip(self):
        py.test.skip('in progress')

    test_degenerated_before_return = _skip
    test_degenerated_before_return_2 = _skip
    test_degenerated_at_return = _skip
    test_degenerated_via_substructure = _skip
    test_plus_minus = _skip
    test_red_array = _skip
    test_red_struct_array = _skip
    test_red_varsized_struct = _skip
    test_array_of_voids = _skip
    test_red_subcontainer = _skip
    test_red_subcontainer_cast = _skip
    test_deepfrozen_interior = _skip
    test_compile_time_const_tuple = _skip
    test_residual_red_call = _skip
    test_residual_red_call_with_exc = _skip
    test_simple_meth = _skip
    test_simple_red_meth = _skip
    test_simple_red_meth_vars_around = _skip
    test_simple_indirect_call = _skip
    test_normalize_indirect_call = _skip
    test_normalize_indirect_call_more = _skip
    test_green_char_at_merge = _skip
    test_self_referential_structures = _skip
    test_indirect_red_call = _skip
    test_indirect_red_call_with_exc = _skip
    test_indirect_gray_call = _skip
    test_indirect_residual_red_call = _skip
    test_constant_indirect_red_call = _skip
    test_constant_indirect_red_call_no_result = _skip
    test_indirect_sometimes_residual_pure_red_call = _skip
    test_indirect_sometimes_residual_pure_but_fixed_red_call = _skip
    test_manual_marking_of_pure_functions = _skip
    test_red_int_add_ovf = _skip
    test_nonzeroness_assert_while_compiling = _skip
    test_segfault_while_compiling = _skip
    test_learn_boolvalue = _skip
    test_learn_nonzeroness = _skip
    test_void_args = _skip
    test_ptrequality = _skip




