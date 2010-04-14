"""
the whole algorithm is based on the following paper:
http://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.86.1578&rep=rep1&type=pdf

and the source code of libFIRM (file ir/be/becopyheur.c):
http://pp.info.uni-karlsruhe.de/firm/Main_Page
"""


class DependencyGraph(object):

    def __init__(self):
        self.neighbours = {}

    def add_node(self, v):
        assert v not in self.neighbours, "duplicate vertex %r" % (v,)
        self.neighbours[v] = set()

    def add_edge(self, v1, v2):
        self.neighbours[v1].add(v2)
        self.neighbours[v2].add(v1)

    def lexicographic_order(self):
        sigma = [set(self.neighbours)]
        result = []
        while sigma:
            v = sigma[0].pop()
            yield v
            newsigma = []
            neighb = self.neighbours[v]
            for s in sigma:
                s1 = set()
                s2 = set()
                for x in s:
                    if x in neighb:
                        s1.add(x)
                    else:
                        s2.add(x)
                if s1:
                    newsigma.append(s1)
                if s2:
                    newsigma.append(s2)
            sigma = newsigma


_emptyset = frozenset()


##class Unit(object):
##    """An optimization unit.  Represents a phi instruction."""
##    def __init__(self, result, args):
##        self.result = result
##        self.args = args

##    def optimize(self, depgraph):
##        self.queue = []
##        self.insert_qnode(QNode(...
