
from pypy.rpython.ootypesystem.ootype import *
from pypy.annotation import model as annmodel
from pypy.objspace.flow import FlowObjSpace
from pypy.translator.translator import Translator

def gengraph(f, *args):
    t = Translator(f)
    t.annotate(args)
    #t.view()
    t.specialize(type_system="ootype")
    #t.view()
    return t.flowgraphs[f]

def test_simple_class():
    C = Instance("test", None, {'a': Signed})
    
    def f():
        c = new(C)
        return c

    g = gengraph(f)
    rettype = g.getreturnvar().concretetype
    assert rettype == C
    
