
# XXX not enough tests, but see also jit/codewriter/test/test_regalloc.py

import py
from pypy.tool.algo.regalloc import perform_register_allocation
from pypy.rpython.test.test_llinterp import gengraph
from pypy.rpython.lltypesystem import lltype
from pypy.rlib.jit import hint


def test_simple():
    def f(a, b, c):
        return (b * c) + a
    def kind_float(v):
        return v.concretetype == lltype.Float

    t, rtyper, graph = gengraph(f, [int, int, float])
    assert [op.opname for op in graph.startblock.operations] == [
        "cast_int_to_float",    # (1) = b
        "float_mul",            # (0) = (1) * (0)
        "cast_int_to_float",    # (1) = a
        "float_add"]            # (0) = (1) + (0)

    regalloc = perform_register_allocation(graph, kind_float)

    py.test.raises(KeyError, regalloc.getcolor, graph.getargs()[0])
    py.test.raises(KeyError, regalloc.getcolor, graph.getargs()[1])

    ops = graph.startblock.operations
    assert regalloc.getcolor(graph.getargs()[2]) == 0
    assert regalloc.getcolor(ops[0].result) == 1
    assert regalloc.getcolor(ops[1].result) == 0
    assert regalloc.getcolor(ops[2].result) == 1
    assert regalloc.getcolor(ops[3].result) == 0
    assert regalloc.getcolor(graph.getreturnvar()) == 0

def test_unused_result():
    def f(x):
        hint(x, blah=True)
        hint(x, blah=True)
        hint(x, blah=True)
        return x
    def kind_float(v):
        return v.concretetype == lltype.Float

    t, rtyper, graph = gengraph(f, [lltype.Float])
    assert [op.opname for op in graph.startblock.operations] == [
        "hint",   # (1) = hint(0)
        "hint",   # (1) = hint(0)
        "hint"]   # (1) = hint(0)

    regalloc = perform_register_allocation(graph, kind_float)
    ops = graph.startblock.operations
    assert regalloc.getcolor(graph.getargs()[0]) == 0
    assert regalloc.getcolor(ops[0].result) == 1
    assert regalloc.getcolor(ops[1].result) == 1
    assert regalloc.getcolor(ops[2].result) == 1
    assert regalloc.getcolor(graph.getreturnvar()) == 0

def test_identity_op():
    def f(x):
        y = hint(x, blah=True)
        z = hint(y, blah=True)
        t = hint(x, blah=True)
        return 0
    def kind_float(v):
        return v.concretetype == lltype.Float
    def identity_op(op):
        return op.opname == 'hint'

    t, rtyper, graph = gengraph(f, [lltype.Float])
    assert [op.opname for op in graph.startblock.operations] == [
        "hint",   # (0) = hint(0)
        "hint",   # (0) = hint(0)
        "hint"]   # (0) = hint(0)

    regalloc = perform_register_allocation(graph, kind_float, identity_op)
    ops = graph.startblock.operations
    assert regalloc.getcolor(graph.getargs()[0]) == 0
    assert regalloc.getcolor(ops[0].result) == 0
    assert regalloc.getcolor(ops[1].result) == 0
    assert regalloc.getcolor(ops[2].result) == 0
