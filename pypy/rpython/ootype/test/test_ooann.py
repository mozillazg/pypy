from pypy.rpython.ootype.ootype import *
from pypy.annotation import model as annmodel
from pypy.objspace.flow import FlowObjSpace
from pypy.translator.annrpython import RPythonAnnotator


def test_simple_new():
    C = Class("test", None, {'a': Signed})
    
    def oof():
        c = new(C)
        return c.a

    a = RPythonAnnotator()
    s = a.build_types(oof, [])
    #a.translator.view()

    assert s.knowntype == int

def test_simple_instanceof():
    C = Class("test", None, {'a': Signed})
    
    def oof():
        c = new(C)
        return instanceof(c, C)

    a = RPythonAnnotator()
    s = a.build_types(oof, [])
    #a.translator.view()

    assert s.knowntype == bool

def test_simple_null():
    C = Class("test", None, {'a': Signed})
    
    def oof():
        c = null(C)
        return c

    a = RPythonAnnotator()
    s = a.build_types(oof, [])
    #a.translator.view()

    assert s == annmodel.SomeRef(C)

def test_method():
    C = Class("test", None, {"a": (Signed, 3)})

    M = Meth([C], Signed)
    def m_(self, other):
       return self.a + other.a
    m = meth(M, _name="m", _callable=m_)

    addMethods(C, {"m": m})

    def oof():
        c = new(C)
        return c.m(c)
    
    a = RPythonAnnotator()
    s = a.build_types(oof, [])
    # a.translator.view()

    assert s.knowntype == int

def test_unionof():
    C1 = Class("C1", None)
    C2 = Class("C2", C1)
    C3 = Class("C3", C1)

    def oof(f):
        if f:
            c = new(C2)
        else:
            c = new(C3)
        return c

    a = RPythonAnnotator()
    s = a.build_types(oof, [bool])
    #a.translator.view()

    assert s == annmodel.SomeRef(C1)

def test_static_method():
    F = StaticMethod([Signed, Signed], Signed)
    def f_(a, b):
       return a+b
    f = static_meth(F, "f", _callable=f_)

    def oof():
        return f(2,3)

    a = RPythonAnnotator()
    s = a.build_types(oof, [])
    #a.translator.view()

    assert s.knowntype = int

