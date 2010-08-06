# minimal test: just checks that (parts of) rsre can be translated

from pypy.rpython.test.test_llinterp import gengraph
from pypy.rlib.rsre import rsre_core

def main(n):
    assert n >= 0
    pattern = [n] * n
    string = chr(n) * n
    rsre_core.search(pattern, string)
    return 0


def test_gengraph():
    t, typer, graph = gengraph(main, [int])
