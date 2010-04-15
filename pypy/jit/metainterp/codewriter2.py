import sys
from pypy.tool.algo.color import DependencyGraph
from pypy.tool.algo.unionfind import UnionFind
from pypy.objspace.flow.model import Variable


class BytecodeMaker(object):
    DEBUG_REGALLOC = False

    def __init__(self, graph):
        self.graph = graph

    def generate(self):
        self.register_allocation()

    def register_allocation(self):
        dg = DependencyGraph()
        #
        pendingblocks = list(self.graph.iterblocks())
        for block in pendingblocks:
            # Compute die_at = {Variable: index_of_operation_with_last_usage}
            die_at = dict.fromkeys(block.inputargs, 0)
            for i, op in enumerate(block.operations):
                for v in op.args:
                    if isinstance(v, Variable):
                        die_at[v] = i
                if op.result is not None:
                    die_at[op.result] = i
            die_at[block.exitswitch] = sys.maxint
            for link in block.exits:
                for v in link.args:
                    die_at[v] = sys.maxint
            # Add the variables of this block to the dependency graph
            for i, v in enumerate(block.inputargs):
                dg.add_node(v)
                for j in range(i):
                    dg.add_edge(block.inputargs[j], v)
            livevars = set(block.inputargs)
            die_at = [(value, key) for (key, value) in die_at.items()]
            die_at.sort()
            die_at.append((sys.maxint,))
            die_index = 0
            for i, op in enumerate(block.operations):
                while die_at[die_index][0] == i:
                    livevars.remove(die_at[die_index][1])
                    die_index += 1
                if op.result is not None:
                    livevars.add(op.result)
                    dg.add_node(op.result)
                    for v in livevars:
                        dg.add_edge(v, op.result)
        #
        uf = UnionFind()
        while pendingblocks:
            block = pendingblocks.pop()
            # Aggressively try to coalesce each source variable with its target
            for link in block.exits:
                for i, v in enumerate(link.args):
                    if isinstance(v, Variable):
                        w = link.target.inputargs[i]
                        v0 = uf.find_rep(v)
                        w0 = uf.find_rep(w)
                        if v0 not in dg.neighbours[w0]:
                            _, rep, _ = uf.union(v0, w0)
                            assert rep is v0
                            dg.coalesce(w0, v0)
        #
        self._coloring = dg.find_node_coloring()
        self._unionfind = uf
        if self.DEBUG_REGALLOC:
            for block in self.graph.iterblocks():
                print block
                for v in block.getvariables():
                    print '\t', v, '\t', self.getcolor(v)

    def getcolor(self, v):
        return self._coloring[self._unionfind.find_rep(v)]
