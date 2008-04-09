from pypy.rpython.test.test_llinterp import gengraph, interpret
from pypy.rpython.lltypesystem import lltype
from pypy.rlib import rgc # Force registration of gc.collect
import gc

def test_collect():
    def f():
        return gc.collect()

    t, typer, graph = gengraph(f, [])
    ops = list(graph.iterblockops())
    assert len(ops) == 1
    op = ops[0][1]
    assert op.opname == 'gc__collect'


    res = interpret(f, [])
    
    assert res is None
    
def test_can_move():
    T0 = lltype.GcStruct('T')
    T1 = lltype.GcArray(lltype.Float)
    def f(i):
        if i:
            return rgc.can_move(T0)
        else:
            return rgc.can_move(T1)

    t, typer, graph = gengraph(f, [int])
    ops = list(graph.iterblockops())
    res = [op for op in ops if op[1].opname == 'gc_can_move']
    assert len(res) == 2

    res = interpret(f, [1])
    
    assert res == True
    
