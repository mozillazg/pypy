from pypy.rlib.jit import virtual_ref
from pypy.rlib._jit_vref import SomeVRef
from pypy.annotation import model as annmodel
from pypy.annotation.annrpython import RPythonAnnotator
from pypy.rpython.test.test_llinterp import interpret
from pypy.rpython.lltypesystem.rclass import OBJECTPTR
from pypy.rpython.lltypesystem import lltype


class X(object):
    pass

class Y(X):
    pass

class Z(X):
    pass


def test_direct():
    x1 = X()
    vref = virtual_ref(x1)
    assert vref() is x1

def test_annotate_1():
    def f():
        return virtual_ref(X())
    a = RPythonAnnotator()
    s = a.build_types(f, [])
    assert isinstance(s, SomeVRef)
    assert isinstance(s.s_instance, annmodel.SomeInstance)
    assert s.s_instance.classdef == a.bookkeeper.getuniqueclassdef(X)

def test_annotate_2():
    def f():
        vref = virtual_ref(X())
        return vref()
    a = RPythonAnnotator()
    s = a.build_types(f, [])
    assert isinstance(s, annmodel.SomeInstance)
    assert s.classdef == a.bookkeeper.getuniqueclassdef(X)

def test_annotate_3():
    def f(n):
        if n > 0:
            return virtual_ref(Y())
        else:
            return virtual_ref(Z())
    a = RPythonAnnotator()
    s = a.build_types(f, [int])
    assert isinstance(s, SomeVRef)
    assert isinstance(s.s_instance, annmodel.SomeInstance)
    assert s.s_instance.classdef == a.bookkeeper.getuniqueclassdef(X)

def test_annotate_4():
    def f(n):
        if n > 0:
            return virtual_ref(X())
        else:
            return None
    a = RPythonAnnotator()
    s = a.build_types(f, [int])
    assert isinstance(s, SomeVRef)
    assert isinstance(s.s_instance, annmodel.SomeInstance)
    assert s.s_instance.classdef == a.bookkeeper.getuniqueclassdef(X)

def test_rtype_1():
    def f():
        return virtual_ref(X())
    x = interpret(f, [])
    assert lltype.typeOf(x) == OBJECTPTR

def test_rtype_2():
    def f():
        vref = virtual_ref(X())
        return vref()
    x = interpret(f, [])
    assert lltype.castable(OBJECTPTR, lltype.typeOf(x)) > 0

def test_rtype_3():
    def f(n):
        if n > 0:
            return virtual_ref(Y())
        else:
            return virtual_ref(Z())
    x = interpret(f, [-5])
    assert lltype.typeOf(x) == OBJECTPTR

def test_rtype_4():
    def f(n):
        if n > 0:
            return virtual_ref(X())
        else:
            return None
    x = interpret(f, [-5])
    assert lltype.typeOf(x) == OBJECTPTR
    assert not x

# the path "we_are_jitted()" is tested in jit/metainterp/test/test_codewriter.
