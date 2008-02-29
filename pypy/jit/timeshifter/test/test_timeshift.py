import py
import sys
from pypy.translator.translator import TranslationContext, graphof
from pypy.jit.hintannotator.annotator import HintAnnotator
from pypy.jit.hintannotator.policy import StopAtXPolicy, HintAnnotatorPolicy
from pypy.jit.hintannotator.bookkeeper import HintBookkeeper
from pypy.jit.hintannotator.model import *
from pypy.jit.timeshifter.hrtyper import HintRTyper, originalconcretetype
from pypy.jit.timeshifter import rtimeshift, rvalue
from pypy.objspace.flow.model import summary, Variable
from pypy.rpython.lltypesystem import lltype, llmemory, rstr
from pypy.rlib.jit import hint
from pypy.rlib.objectmodel import keepalive_until_here
from pypy.rlib.debug import ll_assert
from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.rarithmetic import ovfcheck
from pypy.rpython.annlowlevel import PseudoHighLevelCallable, cachedtype
from pypy.rpython.module.support import LLSupport
from pypy.annotation import model as annmodel
from pypy.rpython.llinterp import LLInterpreter, LLException
from pypy.translator.backendopt.inline import auto_inlining
from pypy import conftest
from pypy.jit.conftest import Benchmark
from pypy.jit.codegen.llgraph.rgenop import RGenOp as LLRGenOp

P_NOVIRTUAL = HintAnnotatorPolicy(novirtualcontainer=True)


class Whatever(object):
    """To cheat in the tests that have no way to do the right thing."""
    def __eq__(self, other):
        return True
    def __ne__(self, other):
        return False
    def __and__(self, other):
        return Whatever()     # for test_ovfcheck_adder_direct in codegen.dump


def getargtypes(annotator, values):
    return [annotation(annotator, x) for x in values]

def annotation(a, x):
    T = lltype.typeOf(x)
    if T == lltype.Ptr(rstr.STR):
        t = str
    else:
        t = annmodel.lltype_to_annotation(T)
    return a.typeannotation(t)

class TimeshiftingTests(object):
    RGenOp = LLRGenOp
    small = True
    type_system = 'lltype' # because a lot of tests inherits from this class

    def setup_class(cls):
        from pypy.jit.timeshifter.test.conftest import option
        cls.on_llgraph = cls.RGenOp is LLRGenOp
        if option.use_dump_backend:
            from pypy.jit.codegen.dump.rgenop import RDumpGenOp
            cls.RGenOp = RDumpGenOp
        cls._cache = {}
        cls._cache_order = []

    def teardown_class(cls):
        del cls._cache
        del cls._cache_order

    @classmethod
    def hannotate(cls, func, values, policy=None, inline=None, backendoptimize=False,
                  portal=None):
        # build the normal ll graphs for ll_function
        t = TranslationContext()
        a = t.buildannotator()
        argtypes = getargtypes(a, values)
        a.build_types(func, argtypes)
        rtyper = t.buildrtyper(type_system = cls.type_system)
        rtyper.specialize()
        if inline:
            auto_inlining(t, threshold=inline)
        if backendoptimize:
            from pypy.translator.backendopt.all import backend_optimizations
            backend_optimizations(t, inline_threshold=inline or 0)
        if portal is None:
            portal = func

        policy = cls.fixpolicy(policy)
        if hasattr(policy, "seetranslator"):
            policy.seetranslator(t)
        graph1 = graphof(t, portal)
        # build hint annotator types
        hannotator = HintAnnotator(base_translator=t, policy=policy)
        hs = hannotator.build_types(graph1, [SomeLLAbstractConstant(v.concretetype,
                                                                    {OriginFlags(): True})
                                             for v in graph1.getargs()])
        hannotator.simplify()
        if conftest.option.view:
            hannotator.translator.view()
        return hs, hannotator, rtyper

    @classmethod
    def fixpolicy(cls, policy):
        import copy
        if cls.type_system == 'ootype' and policy is not None:
            newpolicy = copy.copy(policy)
            newpolicy.oopspec = False
            return newpolicy
        else:
            return policy

    def timeshift_cached(self, ll_function, values, inline=None, policy=None,
                         check_raises='ignored anyway',
                         backendoptimize=False):
        # decode the 'values' if they are specified as strings
        if hasattr(ll_function, 'convert_arguments'):
            assert len(ll_function.convert_arguments) == len(values)
            values = [decoder(value) for decoder, value in zip(
                                        ll_function.convert_arguments, values)]

        key = ll_function, inline, policy
        try:
            cache, argtypes = self._cache[key]
        except KeyError:
            pass
        else:
            self.__dict__.update(cache)
            assert argtypes == getargtypes(self.rtyper.annotator, values)
            return values

        if len(self._cache_order) >= 3:
            del self._cache[self._cache_order.pop(0)]
        hs, ha, rtyper = self.hannotate(ll_function, values,
                                        inline=inline, policy=policy,
                                        backendoptimize=backendoptimize)

        # make the timeshifted graphs
        hrtyper = HintRTyper(ha, rtyper, self.RGenOp)
        hrtyper.specialize(view = conftest.option.view and self.small,
                           dont_simplify_again = True)
        fresh_jitstate = hrtyper.ll_fresh_jitstate
        finish_jitstate = hrtyper.ll_finish_jitstate
        exceptiondesc = hrtyper.exceptiondesc
        t = rtyper.annotator.translator

        # make an interface to the timeshifted graphs:
        #
        #  - a green input arg in the timeshifted entry point
        #    must be provided as a value in 'args'
        #
        #  - a redbox input arg in the timeshifted entry point must
        #    be provided as two entries in 'args': a boolean flag
        #    (True=constant, False=variable) and a value
        #
        graph1 = ha.translator.graphs[0]   # the timeshifted entry point
        assert len(graph1.getargs()) == 1 + len(values)
        graph1varargs = graph1.getargs()[1:]
        timeshifted_entrypoint_args_s = []
        argcolors = []
        generate_code_args_s = []

        for v, llvalue in zip(graph1varargs, values):
            s_var = annmodel.ll_to_annotation(llvalue)
            r = hrtyper.bindingrepr(v)
            residual_v = r.residual_values(llvalue)
            if len(residual_v) == 0:
                color = "green"
                timeshifted_entrypoint_args_s.append(s_var)
            else:
                color = "red"
                assert residual_v == [llvalue], "XXX for now"
                timeshifted_entrypoint_args_s.append(hrtyper.s_RedBox)
                generate_code_args_s.append(annmodel.SomeBool())
            argcolors.append(color)
            generate_code_args_s.append(s_var)

        timeshifted_entrypoint_fnptr = rtyper.type_system.getcallable(
            graph1)
        timeshifted_entrypoint = PseudoHighLevelCallable(
            timeshifted_entrypoint_fnptr,
            [hrtyper.s_JITState]
            + timeshifted_entrypoint_args_s,
            hrtyper.s_JITState)
        FUNC = hrtyper.get_residual_functype(ha.translator.graphs[0])
        argcolors = unrolling_iterable(argcolors)
        self.argcolors = argcolors

        def ml_generate_code(rgenop, *args):
            timeshifted_entrypoint_args = ()

            sigtoken = rgenop.sigToken(FUNC)
            builder, gv_generated, inputargs_gv = rgenop.newgraph(sigtoken,
                                                                  "generated")
            builder.start_writing()
            i = 0
            for color in argcolors:
                if color == "green":
                    llvalue = args[0]
                    args = args[1:]
                    timeshifted_entrypoint_args += (llvalue,)
                else:
                    is_constant = args[0]
                    llvalue     = args[1]
                    args = args[2:]
                    TYPE = lltype.typeOf(llvalue)
                    kind = rgenop.kindToken(TYPE)
                    boxcls = rvalue.ll_redboxcls(TYPE)
                    if is_constant:
                        # ignore the inputargs_gv[i], which is still present
                        # to give the residual graph a uniform signature
                        gv_arg = rgenop.genconst(llvalue)
                    else:
                        gv_arg = inputargs_gv[i]
                    box = boxcls(kind, gv_arg)
                    i += 1
                    timeshifted_entrypoint_args += (box,)

            top_jitstate = fresh_jitstate(builder, exceptiondesc)
            top_jitstate = timeshifted_entrypoint(top_jitstate,
                                                  *timeshifted_entrypoint_args)
            if top_jitstate is not None:
                finish_jitstate(top_jitstate, exceptiondesc, sigtoken)

            builder.end()
            generated = gv_generated.revealconst(lltype.Ptr(FUNC))
            return generated

        ml_generate_code.args_s = ["XXX rgenop"] + generate_code_args_s
        ml_generate_code.s_result = annmodel.lltype_to_annotation(
            lltype.Ptr(FUNC))

##        def ml_extract_residual_args(*args):
##            result = ()
##            for color in argcolors:
##                if color == "green":
##                    args = args[1:]
##                else:
##                    is_constant = args[0]
##                    llvalue     = args[1]
##                    args = args[2:]
##                    result += (llvalue,)
##            return result

##        def ml_call_residual_graph(generated, *allargs):
##            residual_args = ml_extract_residual_args(*allargs)
##            return generated(*residual_args)

##        ml_call_residual_graph.args_s = (
##            [ml_generate_code.s_result, ...])
##        ml_call_residual_graph.s_result = annmodel.lltype_to_annotation(
##            RESTYPE)

        self.ml_generate_code = ml_generate_code
##        self.ml_call_residual_graph = ml_call_residual_graph
        self.rtyper = rtyper
        self.hrtyper = hrtyper
        self.annotate_interface_functions()
        #if conftest.option.view and self.small:
        #    from pypy.translator.tool.graphpage import FlowGraphPage
        #    FlowGraphPage(t, ha.translator.graphs).display()

        cache = self.__dict__.copy()
        self._cache[key] = cache, getargtypes(rtyper.annotator, values)
        self._cache_order.append(key)
        return values

    def annotate_interface_functions(self):
        annhelper = self.hrtyper.annhelper
        RGenOp = self.RGenOp
        ml_generate_code = self.ml_generate_code
##        ml_call_residual_graph = self.ml_call_residual_graph

        def ml_main(*args):
            rgenop = RGenOp()
            return ml_generate_code(rgenop, *args)

        ml_main.args_s = ml_generate_code.args_s[1:]
        ml_main.s_result = ml_generate_code.s_result

        self.maingraph = annhelper.getgraph(
            ml_main,
            ml_main.args_s,
            ml_main.s_result)
##        self.callresidualgraph = annhelper.getgraph(
##            ml_call_residual_graph,
##            ml_call_residual_graph.args_s,
##            ml_call_residual_graph.s_result)

        annhelper.finish()

    def timeshift(self, ll_function, values, opt_consts=[], *args, **kwds):
        values = self.timeshift_cached(ll_function, values, *args, **kwds)

        mainargs = []
        residualargs = []
        for i, (color, llvalue) in enumerate(zip(self.argcolors, values)):
            if color == "green":
                mainargs.append(llvalue)
            else:
                mainargs.append(i in opt_consts)
                mainargs.append(llvalue)
                residualargs.append(llvalue)

        # run the graph generator
        exc_data_ptr = self.hrtyper.exceptiondesc.exc_data_ptr
        llinterp = LLInterpreter(self.rtyper, exc_data_ptr=exc_data_ptr)
        ll_generated = llinterp.eval_graph(self.maingraph, mainargs)

        # now try to run the residual graph generated by the builder
        residual_graph = ll_generated._obj.graph
        self.ll_generated = ll_generated
        self.residual_graph = residual_graph
        if conftest.option.view:
            residual_graph.show()

        if 'check_raises' not in kwds:
            res = llinterp.eval_graph(residual_graph, residualargs)
        else:
            try:
                llinterp.eval_graph(residual_graph, residualargs)
            except LLException, e:
                exc = kwds['check_raises']
                assert llinterp.find_exception(e) is exc, (
                    "wrong exception type")
            else:
                raise AssertionError("DID NOT RAISE")
            return True

        if hasattr(ll_function, 'convert_result'):
            res = ll_function.convert_result(res)

        # get some benchmarks with genc
        if Benchmark.ENABLED:
            from pypy.translator.interactive import Translation
            import sys
            testname = sys._getframe(1).f_code.co_name
            def ll_main():
                bench = Benchmark(testname)
                while True:
                    ll_generated(*residualargs)
                    if bench.stop():
                        break
            t = Translation(ll_main)
            main = t.compile_c([])
            main()
        return res

    def timeshift_raises(self, ExcCls, ll_function, values, opt_consts=[],
                         *args, **kwds):
        kwds['check_raises'] = ExcCls
        return self.timeshift(ll_function, values, opt_consts, *args, **kwds)

    def check_insns(self, expected=None, **counts):
        self.insns = summary(self.residual_graph)
        if expected is not None:
            assert self.insns == expected
        for opname, count in counts.items():
            assert self.insns.get(opname, 0) == count

    def check_oops(self, expected=None, **counts):
        if not self.on_llgraph:
            return
        oops = {}
        for block in self.residual_graph.iterblocks():
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
        count = 0
        for block in self.residual_graph.iterblocks():
            if (isinstance(block.exitswitch, Variable) and
                block.exitswitch.concretetype is lltype.Signed):
                count += 1
        assert count == expected_count


class BaseTestTimeshift(TimeshiftingTests):
    pass

class TestLLType(BaseTestTimeshift):
    type_system = 'lltype'

passing_ootype_tests = set([
    'test_very_simple',
    'test_convert_const_to_redbox',
    'test_simple_opt_const_propagation1',
    'test_simple_opt_const_propagation2',
    'test_loop_folding',
    'test_loop_merging',
    'test_two_loops_merging',
    'test_convert_greenvar_to_redvar',
    'test_green_across_split',
    'test_merge_const_before_return',
    'test_merge_3_redconsts_before_return',
    'test_merge_const_at_return',
    'test_arith_plus_minus',
    ])
class TestOOType(BaseTestTimeshift):
    type_system = 'ootype'

    def __getattribute__(self, name):
        if name.startswith('test_') and name not in passing_ootype_tests:
            def fn():
                py.test.skip("doesn't work yet")
            return fn
        else:
            return object.__getattribute__(self, name)
