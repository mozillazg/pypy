import sys
from pypy.objspace.flow.model import Variable
from pypy.tool.algo.color import DependencyGraph
from pypy.tool.algo.unionfind import UnionFind

def perform_register_allocation(graph, kind_filter, identity_op_filter=None):
    """Perform register allocation for the Variables of the given kind
    in the graph.  
    """
    regalloc = RegAllocator(graph, kind_filter, identity_op_filter)
    regalloc.make_dependencies()
    regalloc.coalesce_variables()
    regalloc.find_node_coloring()
    return regalloc


class RegAllocator(object):
    DEBUG_REGALLOC = False

    def __init__(self, graph, kind_filter, identity_op_filter=None):
        self.graph = graph
        self.kind_filter = kind_filter
        if identity_op_filter is not None:
            self.identity_op_filter = identity_op_filter

    def identity_op_filter(self, op):
        return False     # default implementation

    def make_dependencies(self):
        dg = DependencyGraph()
        uf = UnionFind()
        for block in self.graph.iterblocks():
            # Compute die_at = {Variable: index_of_operation_with_last_usage}
            die_at = dict.fromkeys(block.inputargs, 0)
            for i, op in enumerate(block.operations):
                for v in op.args:
                    if isinstance(v, Variable):
                        die_at[v] = i
                    elif is_iterable(v):
                        for v1 in v:
                            if isinstance(v1, Variable):
                                die_at[v1] = i
                if op.result is not None:
                    die_at[op.result] = i + 1
            if is_iterable(block.exitswitch):
                for x in block.exitswitch:
                    die_at.pop(x, None)
            else:
                die_at.pop(block.exitswitch, None)
            for link in block.exits:
                for v in link.args:
                    die_at.pop(v, None)
            die_at = [(value, key) for (key, value) in die_at.items()]
            die_at.sort()
            die_at.append((sys.maxint,))
            # Done.  XXX if we need to perform register allocation on
            # the same graph with various 'kinds', the code above this
            # line runs several times to produce the same result...
            livevars = [v for v in block.inputargs if self.kind_filter(v)]
            # Add the variables of this block to the dependency graph
            for i, v in enumerate(livevars):
                dg.add_node(v)
                for j in range(i):
                    dg.add_edge(livevars[j], v)
            livevars = set(livevars)
            die_index = 0
            for i, op in enumerate(block.operations):
                while die_at[die_index][0] == i:
                    try:
                        livevars.remove(die_at[die_index][1])
                    except KeyError:
                        pass
                    die_index += 1
                if op.result is not None and self.kind_filter(op.result):
                    if self.identity_op_filter(op):
                        rep1 = uf.find_rep(op.args[0])
                        _, rep2, _ = uf.union(rep1, op.result)
                        assert rep2 is rep1
                    else:
                        dg.add_node(op.result)
                        for v in livevars:
                            assert self.kind_filter(v)
                            dg.add_edge(uf.find_rep(v), op.result)
                    livevars.add(op.result)
        self._depgraph = dg
        self._unionfind = uf

    def coalesce_variables(self):
        pendingblocks = list(self.graph.iterblocks())
        while pendingblocks:
            block = pendingblocks.pop()
            # Aggressively try to coalesce each source variable with its
            # target.  We start from the end of the graph instead of
            # from the beginning.  This is a bit arbitrary, but the idea
            # is that the end of the graph runs typically more often
            # than the start, given that we resume execution from the
            # middle during blackholing.
            for link in block.exits:
                if link.last_exception is not None:
                    self._depgraph.add_node(link.last_exception)
                if link.last_exc_value is not None:
                    self._depgraph.add_node(link.last_exc_value)
                for i, v in enumerate(link.args):
                    self._try_coalesce(v, link.target.inputargs[i])

    def _try_coalesce(self, v, w):
        if isinstance(v, Variable) and self.kind_filter(v):
            dg = self._depgraph
            uf = self._unionfind
            v0 = uf.find_rep(v)
            w0 = uf.find_rep(w)
            if v0 is not w0 and v0 not in dg.neighbours[w0]:
                _, rep, _ = uf.union(v0, w0)
                assert uf.find_rep(v0) is uf.find_rep(w0) is rep
                if rep is v0:
                    dg.coalesce(w0, v0)
                else:
                    assert rep is w0
                    dg.coalesce(v0, w0)

    def find_node_coloring(self):
        self._coloring = self._depgraph.find_node_coloring()
        if self.DEBUG_REGALLOC:
            for block in self.graph.iterblocks():
                print block
                for v in block.getvariables():
                    print '\t', v, '\t', self.getcolor(v)

    def getcolor(self, v):
        return self._coloring[self._unionfind.find_rep(v)]

    def swapcolors(self, col1, col2):
        for key, value in self._coloring.items():
            if value == col1:
                self._coloring[key] = col2
            elif value == col2:
                self._coloring[key] = col1


def is_iterable(x):
    try:
        iter(x)
        return True
    except (TypeError, AttributeError):
        return False
