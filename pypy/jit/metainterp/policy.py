
class JitPolicy:
    def graphs_from(self, op):
        if op.opname == 'direct_call':
            return [op.args[0].value._obj.graph]
        assert op.opname == 'indirect_call'
        return op.args[-1].value

    def guess_call_kind(self, op):
        targetgraphs = self.graphs_from(op)
        if targetgraphs is None:
            return 'residual'
        if len(targetgraphs) == 1:
            [targetgraph] = targetgraphs
            if (hasattr(targetgraph, 'func') and
                hasattr(targetgraph.func, 'oopspec')):
                return 'builtin'
        return 'regular'


class StopAtXPolicy(JitPolicy):
    def __init__(self, *funcs):
        self.funcs = funcs

    def graphs_from(self, op):
        graphs = JitPolicy.graphs_from(self, op)
        if len(graphs) > 1: # XXX a hack
            return graphs
        [graph] = graphs
        if getattr(graph, 'func', None) in self.funcs:
            return None
        return [graph]
