#
# Contains the logic to decide, based on the policy, which graphs
# to transform to JitCodes or not.
#

from pypy.jit.codewriter import support
from pypy.translator.simplify import get_funcobj


class CallControl(object):

    def __init__(self, rtyper=None, portal_runner_obj=None):
        self.rtyper = rtyper
        self.portal_runner_obj = portal_runner_obj

    def find_all_graphs(self, portal_graph, policy):
        def is_candidate(graph):
            return policy.look_inside_graph(graph)
        
        todo = [portal_graph]
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
            if funcobj is self.portal_runner_obj:
                return 'recursive'
            targetgraph = funcobj.graph
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
