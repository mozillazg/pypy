
from pypy.translator.translator import graphof
from pypy.annotation.annrpython import RPythonAnnotator
from pypy.tool.algo.color import DependencyGraph

def test_one():
    def f(a, b, c):
        d = a + b
        e = b + c
        f = d + e
        return d + e + f

    a = RPythonAnnotator()
    a.build_types(f, [int, int, int])
    graph = graphof(a.translator, f)
    dep_graph = DependencyGraph(graph)
