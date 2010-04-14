from pypy.tool.algo.color import DependencyGraph


def test_perfect_elimination_order():
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
    order = list(dg.perfect_elimination_order())
    assert len(order) == 5
    assert ''.join(order) in [
        'adbce', 'adbec', 'adcbe', 'adceb', 'adebc', 'adecb',
        'acbde', 'acbed', 'acdbe', 'acdeb', 'acebd', 'acedb',
        'cebad', 'cebda', 'ceabd', 'ceadb', 'cedba', 'cedab',
        'cabde', 'cabed', 'cadbe', 'cadeb', 'caebd', 'caedb',
        ]
