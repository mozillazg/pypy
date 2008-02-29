from pypy import conftest
from pypy.translator.translator import graphof
from pypy.jit.timeshifter.test.test_timeshift import TestLLType as TSTestLLType, getargtypes
from pypy.jit.timeshifter.hrtyper import HintRTyper
from pypy.jit.timeshifter.test.test_timeshift import P_NOVIRTUAL, StopAtXPolicy
from pypy.jit.timeshifter.test.test_vlist import P_OOPSPEC
from pypy.rpython.llinterp import LLInterpreter
from pypy.rpython.lltypesystem import lltype
from pypy.objspace.flow.model import  summary
from pypy.rlib.jit import hint
from pypy.jit.codegen.llgraph.rgenop import RGenOp as LLRGenOp

import py.test


class PortalTest(object):
    RGenOp = LLRGenOp
    small = True

    def setup_class(cls):
        from pypy.jit.timeshifter.test.conftest import option
        if option.use_dump_backend:
            from pypy.jit.codegen.dump.rgenop import RDumpGenOp
            cls.RGenOp = RDumpGenOp
        cls._cache = {}
        cls._cache_order = []
        cls.on_llgraph = cls.RGenOp is LLRGenOp

    def teardown_class(cls):
        del cls._cache
        del cls._cache_order

    def postprocess_timeshifting(self):
        self.readportalgraph = self.hrtyper.readportalgraph
        self.readallportalsgraph = self.hrtyper.readallportalsgraph
        
    def _timeshift_from_portal(self, main, portal, main_args,
                              inline=None, policy=None,
                              backendoptimize=False):
        # decode the 'values' if they are specified as strings
        if hasattr(main, 'convert_arguments'):
            assert len(main.convert_arguments) == len(main_args)
            main_args = [decoder(value) for decoder, value in zip(
                                        main.convert_arguments,
                                        main_args)]
        key = main, portal, inline, policy, backendoptimize
        try:
            cache, argtypes = self._cache[key]
        except KeyError:
            pass
        else:
            self.__dict__.update(cache)
            assert argtypes == getargtypes(self.rtyper.annotator, main_args)
            return main_args

        hs, ha, self.rtyper = TSTestLLType.hannotate(main, main_args, portal=portal,
                                   policy=policy, inline=inline,
                                   backendoptimize=backendoptimize)

        t = self.rtyper.annotator.translator
        self.maingraph = graphof(t, main)
        # make the timeshifted graphs
        self.hrtyper = HintRTyper(ha, self.rtyper, self.RGenOp)
        origportalgraph = graphof(t, portal)
        self.hrtyper.specialize(origportalgraph=origportalgraph,
                           view = conftest.option.view and self.small)

        #if conftest.option.view and self.small:
        #    t.view()
        self.postprocess_timeshifting()
        self.readportalgraph = self.hrtyper.readportalgraph

        # Populate the cache
        if len(self._cache_order) >= 3:
            del self._cache[self._cache_order.pop(0)]
        cache = self.__dict__.copy()
        self._cache[key] = cache, getargtypes(self.rtyper.annotator, main_args)
        self._cache_order.append(key)
        return main_args

    
    def timeshift_from_portal(self, main, portal, main_args,
                              inline=None, policy=None,
                              backendoptimize=False):
        main_args = self._timeshift_from_portal(main, portal, main_args,
                                                inline=inline, policy=policy,
                                                backendoptimize=backendoptimize)
        self.main_args = main_args
        self.main_is_portal = main is portal
        exc_data_ptr = self.hrtyper.exceptiondesc.exc_data_ptr
        llinterp = LLInterpreter(self.rtyper, exc_data_ptr=exc_data_ptr)
        res = llinterp.eval_graph(self.maingraph, main_args)
        return res

    def get_residual_graph(self):
        exc_data_ptr = self.hrtyper.exceptiondesc.exc_data_ptr
        llinterp = LLInterpreter(self.rtyper, exc_data_ptr=exc_data_ptr)
        if self.main_is_portal:
            residual_graph = llinterp.eval_graph(self.readportalgraph,
                                                 self.main_args)._obj.graph
        else:
            residual_graphs = llinterp.eval_graph(self.readallportalsgraph, [])
            assert residual_graphs.ll_length() == 1
            residual_graph = residual_graphs.ll_getitem_fast(0)._obj.graph
        return residual_graph
            
    def check_insns(self, expected=None, **counts):
        residual_graph = self.get_residual_graph()
        self.insns = summary(residual_graph)
        if expected is not None:
            assert self.insns == expected
        for opname, count in counts.items():
            assert self.insns.get(opname, 0) == count


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

    def count_direct_calls(self):
        residual_graph = self.get_residual_graph()
        calls = {}
        for block in residual_graph.iterblocks():
            for op in block.operations:
                if op.opname == 'direct_call':
                    graph = getattr(op.args[0].value._obj, 'graph', None)
                    calls[graph] = calls.get(graph, 0) + 1
        return calls
        
class TestPortal(PortalTest):
