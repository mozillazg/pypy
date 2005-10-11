from pypy.rpython.ootype.ootype import *
from pypy.annotation import model as annmodel
from pypy.objspace.flow import FlowObjSpace
from pypy.translator.annrpython import RPythonAnnotator


def test_simple_new():
    C = Class("test", None, {'a': Signed})
    
    def oof():
    	c = new(C)
	return c.a

    a =	RPythonAnnotator()
    s = a.build_types(oof, [])
    #a.translator.view()

    assert s.knowntype == int

def test_simple_instanceof():
    C = Class("test", None, {'a': Signed})
    
    def oof():
    	c = new(C)
	return instanceof(c, C)

    a =	RPythonAnnotator()
    s = a.build_types(oof, [])
    #a.translator.view()

    assert s.knowntype == bool
