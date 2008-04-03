from pypy.translator.simplify import get_graph
from pypy.rpython.lltypesystem.lloperation import llop, LL_OPERATIONS
from pypy.rpython.lltypesystem import lltype

class GraphAnalyzer(object):
    """generic way to analyze graphs: recursively follow it until the first
    operation is found on which self.operation_is_true returns True"""
    def __init__(self, translator):
        self.translator = translator
        self.analyzed_calls = {}

    # methods to be overridden by subclass

    def operation_is_true(self, op):
        raise NotImplementedError("abstract base class")

    def analyze_exceptblock(self, block, seen=None):
        return False

    def analyze_startblock(self, block, seen=None):
        return False

    def analyze_external_call(self, op):
        return True

    def analyze_external_method(self, op, TYPE, meth):
        return True

    def analyze_link(self, graph, link):
        return False

    # general methods

    def analyze(self, op, seen=None):
        if op.opname == "direct_call":
            graph = get_graph(op.args[0], self.translator)
            if graph is None:
                return self.analyze_external_call(op)
            return self.analyze_direct_call(graph, seen)
        elif op.opname == "indirect_call":
            if op.args[-1].value is None:
                return True
            return self.analyze_indirect_call(op.args[-1].value, seen)
        elif op.opname == "oosend":
            name = op.args[0].value
            TYPE = op.args[1].concretetype
            _, meth = TYPE._lookup(name)
            graph = getattr(meth, 'graph', None)
            if graph is None:
                return self.analyze_external_method(op, TYPE, meth)
            return self.analyze_oosend(TYPE, name, seen)
        if self.operation_is_true(op):
            return True

    def analyze_direct_call(self, graph, seen=None):
        if graph in self.analyzed_calls:
            return self.analyzed_calls[graph]
        if seen is None:
            seen = {}
        if graph in seen:
            self.analyzed_calls[graph] = False
            return False
        else:
            seen[graph] = True
        for block in graph.iterblocks():
            if block is graph.startblock:
                if self.analyze_startblock(block, seen):
                    self.analyzed_calls[graph] = True
                    return True
            if block is graph.exceptblock:
                if self.analyze_exceptblock(block, seen):
                    self.analyzed_calls[graph] = True
                    return True
            for op in block.operations:
                if self.analyze(op, seen):
                    self.analyzed_calls[graph] = True
                    return True
            for exit in block.exits:
                if self.analyze_link(graph, exit):
                    self.analyzed_calls[graph] = True
                    return True
        self.analyzed_calls[graph] = False
        return False

    def analyze_indirect_call(self, graphs, seen=None):
        for graph in graphs:
            if self.analyze_direct_call(graph, seen):
                return True
        return False

    def analyze_oosend(self, TYPE, name, seen=None):
        graphs = TYPE._lookup_graphs(name)
        return self.analyze_indirect_call(graphs, seen)

    def analyze_all(self, graphs=None):
        if graphs is None:
            graphs = self.translator.graphs
        for graph in graphs:
            for block, op in graph.iterblockops():
                self.analyze(op)


class ImpurityAnalyzer(GraphAnalyzer):
    """An impure graph has side-effects or depends on state that
    can be mutated.  A pure graph always gives the same answer for
    given arguments."""

    def analyze_exceptblock(self, block, seen=None):
        return True      # for now, we simplify and say that functions
                         # raising exceptions cannot be pure

    def operation_is_true(self, op):
        # must return True if the operation is *impure*
        operation = LL_OPERATIONS[op.opname]
        if operation.canfold:
            return False     # pure
        if operation is llop.debug_assert:
            return False     # debug_assert is pure enough
        if operation in (llop.getfield, llop.getarrayitem):
            TYPE = op.args[0].concretetype.TO
            return not TYPE._hints.get('immutable')  # impure if not immutable
        if operation is llop.getinteriorfield:
            # if any of the containers along the way is immutable,
            # the final field cannot be modified (as it is inside
            # that particular immutable container).
            TYPE = op.args[0].concretetype.TO
            if TYPE._hints.get('immutable'):
                return False    # pure
            for v_index in op.args[1:-1]:
                if v_index.concretetype is lltype.Void:
                    name = v_index.value
                    assert isinstance(name, str)
                    TYPE = getattr(TYPE, name)
                else:
                    assert v_index.concretetype is lltype.Signed
                    TYPE = TYPE.OF
                if TYPE._hints.get('immutable'):
                    return False    # pure
            return True      # all mutable, impure
        # --- operation not special-cased, impure ---
        return True

    def analyze_direct_call(self, graph, seen=None):
        try:
            func = graph.func
            if getattr(func, "_pure_function_", False):
                return False
        except AttributeError:
            pass
        return GraphAnalyzer.analyze_direct_call(self, graph, seen)

    def analyze_external_method(self, op, TYPE, meth):
        if getattr(meth, "_pure_meth", False):
            return False
        else:
            return GraphAnalyzer.analyze_external_method(self, op, TYPE, meth)
