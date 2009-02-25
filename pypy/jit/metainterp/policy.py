
class JitPolicy(object):

    def look_inside_function(self, func):
        # explicitly pure functions are always opaque
        if getattr(func, '_pure_function_', False):
            return False
        return True

    def look_inside_graph(self, graph):
        try:
            func = graph.func
        except AttributeError:
            return True
        return self.look_inside_function(func)

    def graphs_from(self, op):
        if op.opname == 'direct_call':
            graph = op.args[0].value._obj.graph
            if self.look_inside_graph(graph):
                return [graph]     # common case: look inside this graph
        else:
            assert op.opname == 'indirect_call'
            graphs = op.args[-1].value
            for graph in graphs:
                if self.look_inside_graph(graph):
                    return graphs  # common case: look inside at least 1 graph
        # residual call case: we don't need to look into any graph
        return None

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

    def look_inside_function(self, func):
        if func in self.funcs:
            return False
        return super(StopAtXPolicy, self).look_inside_function(func)
