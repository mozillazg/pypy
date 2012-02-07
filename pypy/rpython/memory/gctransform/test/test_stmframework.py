from pypy.translator.translator import graphof
from pypy.objspace.flow.model import summary
from pypy.rpython.memory.gctransform.test.test_transform import rtype
from pypy.rpython.memory.gctransform.stmframework import (
    StmFrameworkGCTransformer)


def prepare(entrypoint, types, func=None):
    t = rtype(entrypoint, types)
    t.config.translation.gc = 'stmgc'
    transformer = StmFrameworkGCTransformer(t)
    graph = graphof(t, func or entrypoint)
    transformer.transform_graph(graph)
    return t, graph


def test_reader():
    class A(object):
        def __init__(self, x):
            self.x = x
    def f(a1, a2):
        return a1.x
    def entry(n, m):
        return f(A(n), A(m))

    t, graph = prepare(entry, [int, int], f)
    assert summary(graph) == {'stm_getfield': 1}
