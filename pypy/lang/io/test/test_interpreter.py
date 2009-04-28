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
    w_number = W_Number(space, 1)
    assert space.w_lobby.slots['a'] == w_number
    assert x == w_number
    assert space.w_lobby.slots['a'] is x
    
    
def test_clone_object():
    x, space = interpret('Object clone')
    assert x.protos == [space.w_object]
    
import py
def test_clone_number():
    x, space = interpret('1 clone')
    assert x.value == 1
    assert x.protos[0].protos == [space.w_number]