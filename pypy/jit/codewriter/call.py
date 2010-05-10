#
# Contains the logic to decide, based on the policy, which graphs
# to transform to JitCodes or not.
#

from pypy.jit.codewriter import support
from pypy.jit.codewriter.jitcode import JitCode
from pypy.translator.simplify import get_funcobj, get_functype
from pypy.rpython.lltypesystem import lltype, llmemory


class CallControl(object):

    def __init__(self, cpu=None, portal_graph=None):
        self.cpu = cpu
        self.portal_graph = portal_graph
        self.jitcodes = {}             # map {graph: jitcode}
        self.unfinished_graphs = []    # list of graphs with pending jitcodes
        if cpu is not None:
            from pypy.jit.metainterp.effectinfo import VirtualizableAnalyzer
            from pypy.translator.backendopt.canraise import RaiseAnalyzer
            from pypy.translator.backendopt.writeanalyze import \
                                                            ReadWriteAnalyzer
            self.rtyper = cpu.rtyper
            translator = self.rtyper.annotator.translator
            self.raise_analyzer = RaiseAnalyzer(translator)
            self.readwrite_analyzer = ReadWriteAnalyzer(translator)
            self.virtualizable_analyzer = VirtualizableAnalyzer(translator)

    def find_all_graphs(self, policy):
        def is_candidate(graph):
            return policy.look_inside_graph(graph)

        assert self.portal_graph is not None
        todo = [self.portal_graph]
        candidate_graphs = set(todo)

        def callers():
            graph = top_graph
            print graph
            while graph in coming_from:
                graph = coming_from[graph]
                print '<-', graph
        coming_from = {}

        while todo:
            top_graph = todo.pop()
            for _, op in top_graph.iterblockops():
                if op.opname not in ("direct_call", "indirect_call", "oosend"):
                    continue
                kind = self.guess_call_kind(op, is_candidate)
                # use callers() to view the calling chain in pdb
                if kind != "regular":
                    continue
                for graph in self.graphs_from(op, is_candidate):
                    if graph in candidate_graphs:
                        continue
                    assert is_candidate(graph)
                    todo.append(graph)
                    candidate_graphs.add(graph)
                    coming_from[graph] = top_graph
        self.candidate_graphs = candidate_graphs
        return candidate_graphs

    def graphs_from(self, op, is_candidate=None):
        if is_candidate is None:
            is_candidate = self.is_candidate
        if op.opname == 'direct_call':
            funcobj = get_funcobj(op.args[0].value)
            graph = funcobj.graph
            if is_candidate(graph):
                return [graph]     # common case: look inside this graph
        else:
            assert op.opname in ('indirect_call', 'oosend')
            if op.opname == 'indirect_call':
                graphs = op.args[-1].value
            else:
                v_obj = op.args[1].concretetype
                graphs = v_obj._lookup_graphs(op.args[0].value)
            if graphs is not None:
                result = []
                for graph in graphs:
                    if is_candidate(graph):
                        result.append(graph)
                if result:
                    return result  # common case: look inside these graphs,
                                   # and ignore the others if there are any
            else:
                # special case: handle the indirect call that goes to
                # the 'instantiate' methods.  This check is a bit imprecise
                # but it's not too bad if we mistake a random indirect call
                # for the one to 'instantiate'.
                from pypy.rpython.lltypesystem import rclass
                CALLTYPE = op.args[0].concretetype
                if (op.opname == 'indirect_call' and len(op.args) == 2 and
                    CALLTYPE == rclass.OBJECT_VTABLE.instantiate):
                    return list(self._graphs_of_all_instantiate())
        # residual call case: we don't need to look into any graph
        return None

    def _graphs_of_all_instantiate(self):
        for vtable in self.rtyper.lltype2vtable.values():
            if vtable.instantiate:
                yield vtable.instantiate._obj.graph

    def guess_call_kind(self, op, is_candidate=None):
        if op.opname == 'direct_call':
            funcptr = op.args[0].value
            funcobj = get_funcobj(funcptr)
            if getattr(funcobj, 'graph', None) is None:
                return 'residual'
            targetgraph = funcobj.graph
            if targetgraph is self.portal_graph:
                return 'recursive'
            if (hasattr(targetgraph, 'func') and
                hasattr(targetgraph.func, 'oopspec')):
                return 'builtin'
        elif op.opname == 'oosend':
            SELFTYPE, methname, opargs = support.decompose_oosend(op)
            if SELFTYPE.oopspec_name is not None:
                return 'builtin'
        if self.graphs_from(op, is_candidate) is None:
            return 'residual'
        return 'regular'

    def is_candidate(self, graph):
        # used only after find_all_graphs()
        return graph in self.candidate_graphs

    def enum_pending_graphs(self):
        while self.unfinished_graphs:
            graph = self.unfinished_graphs.pop()
            yield graph, self.jitcodes[graph]

    def get_jitcode(self, graph, called_from=None):
        # 'called_from' is only one of the callers, used for debugging.
        try:
            return self.jitcodes[graph]
        except KeyError:
            fnaddr, calldescr = self.get_jitcode_calldescr(graph)
            jitcode = JitCode(graph.name, fnaddr, calldescr,
                              called_from=called_from)
            self.jitcodes[graph] = jitcode
            self.unfinished_graphs.append(graph)
            return jitcode

    def get_jitcode_calldescr(self, graph):
        fnptr = self.rtyper.getcallable(graph)
        FUNC = get_functype(lltype.typeOf(fnptr))
        if self.rtyper.type_system.name == 'ootypesystem':
            XXX
        else:
            fnaddr = llmemory.cast_ptr_to_adr(fnptr)
        NON_VOID_ARGS = [ARG for ARG in FUNC.ARGS if ARG is not lltype.Void]
        calldescr = self.cpu.calldescrof(FUNC, tuple(NON_VOID_ARGS),
                                         FUNC.RESULT)
        return (fnaddr, calldescr)
