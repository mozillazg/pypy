from pypy.translator.backendoptimization import remove_void
from pypy.translator.translator import Translator
from pypy.rpython.lltype import Void
from pypy.rpython.llinterp import LLInterpreter
from pypy.objspace.flow.model import checkgraph

def annotate_and_remove_void(f, annotate):
    t = Translator(f)
    a = t.annotate(annotate)
    t.specialize()
    remove_void(t)
    return t

def test_remove_void_args():
    def f(i):
        return [1,2,3,i][i]
    t = annotate_and_remove_void(f, [int])
    for func, graph in t.flowgraphs.iteritems():
        assert checkgraph(graph) is None
        for arg in graph.startblock.inputargs:
            assert arg.concretetype is not Void
    interp = LLInterpreter(t.flowgraphs, t.rtyper)
    assert interp.eval_function(f, [0]) == 1 

