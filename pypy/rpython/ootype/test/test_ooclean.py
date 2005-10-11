from pypy.translator.translator import Translator
from pypy.rpython import lltype
from pypy.rpython.ootype import ootype

def check_only_ootype(graph):
    def check_ootype(v):
        t = v.concretetype
        assert isinstance(t, ootype.Primitive) or isinstance(t, ootype.OOType)
	
    for block in graph.iterblocks():
    	for var in block.getvariables():
	    check_ootype(var)
	for const in block.getconstants():
	    check_ootype(const)

def test_simple():
    def f(a, b):
        return a + b
    t = Translator(f)
    t.annotate([int, int])
    t.specialize()

    graph = t.flowgraphs[f]
    check_only_ootype(graph)

def test_simple_call():
    def f(a, b):
        return a + b

    def g():
        return f(5, 3)

    t = Translator(g)
    t.annotate([])
    t.specialize()

    graph = t.flowgraphs[g]
    check_only_ootype(graph)
