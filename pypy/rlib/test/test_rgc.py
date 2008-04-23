from pypy.rpython.test.test_llinterp import gengraph, interpret
from pypy.rpython.lltypesystem import lltype
from pypy.rlib import rgc # Force registration of gc.collect
import gc
import py

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
            return rgc.can_move(lltype.malloc(T0))
        else:
            return rgc.can_move(lltype.malloc(T1, 1))

    t, typer, graph = gengraph(f, [int])
    ops = list(graph.iterblockops())
    res = [op for op in ops if op[1].opname == 'gc_can_move']
    assert len(res) == 2

    res = interpret(f, [1])
    
    assert res == True
    
def test_raw_array():
    py.test.skip("Not working")
    from pypy.rpython.lltypesystem.rstr import STR
    from pypy.rpython.annlowlevel import hlstr
    
    def f():
        arr = rgc.raw_array_of_shape(STR, 1)
        arr[0] = 'a'
        arr = rgc.resize_raw_array(arr, 1, 2)
        arr[1] = 'b'
        return hlstr(rgc.cast_raw_array_to_shape(STR, arr))

    assert f() == 'ab'
#    from pypy.translator.c.test.test_genc import compile
#    fn = compile(f, [])
#    assert fn() == 'ab'
