import sys
from pypy.objspace.flow.model import Variable
from pypy.tool.algo.color import DependencyGraph
from pypy.tool.algo.unionfind import UnionFind
from pypy.jit.metainterp.history import getkind

def perform_register_allocation(graph, kind):
    """Perform register allocation for the Variables of the given 'kind'
    in the 'graph'."""
    regalloc = RegAllocator(graph, kind)
    regalloc.make_dependencies()
    regalloc.coalesce_variables()
    regalloc.find_node_coloring()
    return regalloc


class RegAllocator(object):
    DEBUG_REGALLOC = False

    def __init__(self, graph, kind):
        self.graph = graph
        self.kind = kind

    def make_dependencies(self):
        dg = DependencyGraph()
        for block in self.graph.iterblocks():
            # Compute die_at = {Variable: index_of_operation_with_last_usage}
            die_at = dict.fromkeys(block.inputargs, 0)
            for i, op in enumerate(block.operations):
                for v in op.args:
                    if isinstance(v, Variable):
                        die_at[v] = i
                if op.result is not None:
                    die_at[op.result] = i
            die_at.pop(block.exitswitch, None)
            for link in block.exits:
                for v in link.args:
                    die_at.pop(v, None)
            # Add the variables of this block to the dependency graph
            for i, v in enumerate(block.inputargs):
                dg.add_node(v)
                for j in range(i):
                    dg.add_edge(block.inputargs[j], v)
            die_at = [(value, key) for (key, value) in die_at.items()]
            die_at.sort()
            die_at.append((sys.maxint,))
            # Done.  XXX the code above this line runs 3 times
            # (for kind in KINDS) to produce the same result...
            livevars = set(block.inputargs)
            die_index = 0
            for i, op in enumerate(block.operations):
                while die_at[die_index][0] == i:
                    livevars.remove(die_at[die_index][1])
                    die_index += 1
                if getkind(op.result.concretetype) == self.kind:
                    livevars.add(op.result)
                    dg.add_node(op.result)
                    for v in livevars:
                        if getkind(v.concretetype) == self.kind:
                            dg.add_edge(v, op.result)
        self._depgraph = dg

    def coalesce_variables(self):
        uf = UnionFind()
        dg = self._depgraph
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
                for i, v in enumerate(link.args):
                    if (isinstance(v, Variable) and
                        getkind(v.concretetype) == self.kind):
                        w = link.target.inputargs[i]
                        v0 = uf.find_rep(v)
                        w0 = uf.find_rep(w)
                        if v0 is not w0 and v0 not in dg.neighbours[w0]:
                            _, rep, _ = uf.union(v0, w0)
                            if rep is v0:
                                dg.coalesce(w0, v0)
                            else:
                                assert rep is w0
                                dg.coalesce(v0, w0)
        self._unionfind = uf

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
