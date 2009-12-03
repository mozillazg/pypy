from pypy.rlib.jit import virtual_ref
from pypy.rlib._jit_vref import SomeVRef
from pypy.annotation import model as annmodel
from pypy.annotation.annrpython import RPythonAnnotator


class X(object):
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
