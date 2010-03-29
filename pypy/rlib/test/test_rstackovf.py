import sys
from pypy.rlib import rstackovf

def recurse(n):
    if n > 0:
        return recurse(n-1) + n
    return 0

def f(n):
    try:
        recurse(n)
    except rstackovf.StackOverflow:
        return 1
    else:
        return 0


def test_direct():
    assert f(sys.maxint) == 1

def test_llinterp():
    from pypy.rpython.test.test_llinterp import interpret
    res = interpret(f, [sys.maxint])
    assert res == 1
