from pypy.rpython.ootype.ootype import *
from pypy.annotation import model as annmodel
from pypy.objspace.flow import FlowObjSpace
from pypy.translator.annrpython import RPythonAnnotator


def test_simple():
    C = Class("test", None, {'a': Signed})

    def oof():
    	c = new(C)
	return c.a

    a =	RPythonAnnotator()
    s = a.build_types(oof, [])
    assert s.knowntype == int

