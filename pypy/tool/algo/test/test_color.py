from pypy.tool.algo.color import DependencyGraph


def graph1():
    dg = DependencyGraph()
    dg.add_node('a')
    dg.add_node('b')
    dg.add_node('c')
    dg.add_node('d')
    dg.add_node('e')
    dg.add_edge('a', 'b')
    dg.add_edge('a', 'd')
    dg.add_edge('d', 'b')
    dg.add_edge('d', 'e')
    dg.add_edge('b', 'c')
    dg.add_edge('b', 'e')
    dg.add_edge('e', 'c')
    return dg

def test_lexicographic_order():
    dg = graph1()
    order = list(dg.lexicographic_order())
    assert len(order) == 5
    order.reverse()
    # there are many orders that are correct answers, but check that we get
    # the following one, which is somehow the 'first' answer in the order
    # of insertion of nodes.
    assert ''.join(order) == 'acbde'

def test_size_of_largest_clique():
    dg = graph1()
    assert dg.size_of_largest_clique() == 3

def test_find_node_coloring():
    dg = graph1()
    coloring = dg.find_node_coloring()
    assert len(coloring) == 5
    assert sorted(coloring.keys()) == list('abcde')
    assert set(coloring.values()) == set([0, 1, 2])
    for v1, v2list in dg.neighbours.items():
        for v2 in v2list:
            assert coloring[v1] != coloring[v2]
