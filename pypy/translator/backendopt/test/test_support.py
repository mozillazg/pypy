from pypy.translator.unsimplify import varoftype
from pypy.translator.translator import TranslationContext, graphof
from pypy.translator.backendopt.support import \
     find_loop_blocks, find_backedges

from pypy.rpython.rtyper import LowLevelOpList
from pypy.rpython.lltypesystem import lltype
from pypy.objspace.flow import model

#__________________________________________________________
# test loop detection

def test_find_backedges():
    def f(k):
        result = 0
        for i in range(k):
            result += 1
        for j in range(k):
            result += 1
        return result
    t = TranslationContext()
    t.buildannotator().build_types(f, [int])
    t.buildrtyper().specialize()
    graph = graphof(t, f)
    backedges = find_backedges(graph)
    assert len(backedges) == 2

def test_find_loop_blocks():
    def f(k):
        result = 0
        for i in range(k):
            result += 1
        for j in range(k):
            result += 1
        return result
    t = TranslationContext()
    t.buildannotator().build_types(f, [int])
    t.buildrtyper().specialize()
    graph = graphof(t, f)
    loop_blocks = find_loop_blocks(graph)
    assert len(loop_blocks) == 4

def test_find_loop_blocks_simple():
    def f(a):
        if a <= 0:
            return 1
        return f(a - 1)
    t = TranslationContext()
    t.buildannotator().build_types(f, [int])
    t.buildrtyper().specialize()
    graph = graphof(t, f)
    backedges = find_backedges(graph)
    assert backedges == []
    loop_blocks = find_loop_blocks(graph)
    assert len(loop_blocks) == 0

def test_find_loop_blocks2():
    class A:
        pass
    def f(n):
        a1 = A()
        a1.x = 1
        a2 = A()
        a2.x = 2
        if n > 0:
            a = a1
        else:
            a = a2
        return a.x
    t = TranslationContext()
    t.buildannotator().build_types(f, [int])
    t.buildrtyper().specialize()
    graph = graphof(t, f)
    backedges = find_backedges(graph)
    assert backedges == []
    loop_blocks = find_loop_blocks(graph)
    assert len(loop_blocks) == 0

def test_find_loop_blocks3():
    import os
    def ps(loops):
        return 42.0, 42.1
    def f(loops):
        benchtime, stones = ps(abs(loops))
        s = '' # annotator happiness
        if loops >= 0:
            s = ("RPystone(%s) time for %d passes = %f" %
                 (23, loops, benchtime) + '\n' + (
                 "This machine benchmarks at %f pystones/second" % stones))
        os.write(1, s)
        if loops == 12345:
            f(loops-1)
    t = TranslationContext()
    t.buildannotator().build_types(f, [int])
    t.buildrtyper().specialize()
    graph = graphof(t, f)
    backedges = find_backedges(graph)
    assert backedges == []
    loop_blocks = find_loop_blocks(graph)
    assert len(loop_blocks) == 0

