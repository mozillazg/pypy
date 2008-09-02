from pypy import conftest
from pypy.translator.translator import TranslationContext
from pypy.translator.backendopt.all import backend_optimizations
from pypy.translator.transform import insert_ll_stackcheck

def test_simple():
    class A(object):
        def __init__(self, n):
            self.n = n
            
    def f(a):
        x = A(a.n+1)
        if x.n == 10:
            return
        f(x)

    def g(n):
        f(A(n))
    
    t = TranslationContext()
    a = t.buildannotator()
    a.build_types(g, [int])
    a.simplify()
    t.buildrtyper().specialize()        
    backend_optimizations(t)
    t.checkgraphs()
    n = insert_ll_stackcheck(t)
    t.checkgraphs()
    assert n == 1
    if conftest.option.view:
        t.view()
    

    
    
