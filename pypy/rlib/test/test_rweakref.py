from pypy.rlib import rgc
from pypy.rlib.rweakref import RWeakValueDictionary
from pypy.rpython.test.test_llinterp import interpret

class X(object):
    pass


def make_test(go_away=True, loop=100):
    def f():
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
        if go_away:
            x2 = None
            rgc.collect(); rgc.collect()
        assert d.get("abc") is x1
        assert d.get("def") is x2
        assert d.get("ghi") is x3
        assert d.get("hello") is None
        d.set("abc", None)
        assert d.get("abc") is None
        assert d.get("def") is x2
        assert d.get("ghi") is x3
        assert d.get("hello") is None
        # resizing should also work
        for i in range(loop):
            d.set(str(i), x1)
        for i in range(loop):
            assert d.get(str(i)) is x1
        assert d.get("abc") is None
        assert d.get("def") is x2
        assert d.get("ghi") is x3
        assert d.get("hello") is None
    return f

def test_RWeakValueDictionary():
    make_test()()

def test_rpython_RWeakValueDictionary():
    # we don't implement the correct weakref behavior in lltype when
    # directly interpreted, but we can still test that the rest works.
    interpret(make_test(go_away=False, loop=12), [])
