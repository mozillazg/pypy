from pypy.lang.io.parserhack import interpret
from pypy.lang.io.model import W_Number
def test_even_simpler():
    x, _ = interpret("2")
    assert x.value == 2

def test_simple():
    x, _ = interpret("2 + 2")
    assert x.value == 4
    
def test_simple_minus():
    x, _ = interpret("2 - 2")
    assert x.value == 0
    
def test_set_slot():
    x, space = interpret("a := 1")
    assert space.w_lobby.slots['a'] == W_Number(space, 1)