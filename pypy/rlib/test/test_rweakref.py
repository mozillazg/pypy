from pypy.rlib import rgc
from pypy.rlib.rweakref import RWeakValueDictionary
from pypy.rpython.test.test_llinterp import interpret

class X(object):
    pass


def test_RWeakValueDictionary():
    d = RWeakValueDictionary(X)
    assert d.get("hello") is None
    x1 = X(); x2 = X(); x3 = X()
    d.set("abc", x1)
    d.set("def", x2)
    d.set("ghi", x3)
    assert d.get("abc") is x1
    assert d.get("def") is x2
    assert d.get("ghi") is x3
    assert d.get("hello") is None
    x2 = None
    rgc.collect(); rgc.collect()
    assert d.get("abc") is x1
    assert d.get("def") is None
    assert d.get("ghi") is x3
    assert d.get("hello") is None
    d.set("abc", None)
    assert d.get("abc") is None
    assert d.get("def") is None
    assert d.get("ghi") is x3
    assert d.get("hello") is None
    # resizing should also work
    for i in range(100):
        d.set(str(i), x1)
    for i in range(100):
        assert d.get(str(i)) is x1
    assert d.get("abc") is None
    assert d.get("def") is None
    assert d.get("ghi") is x3
    assert d.get("hello") is None

#def test_rpython_RWeakValueDictionary():
#    interpret(test_RWeakValueDictionary, [])
