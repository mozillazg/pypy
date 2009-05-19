from pypy.lang.io.parserhack import interpret
from pypy.lang.io.model import W_Number
import py
def test_even_simpler():
    x, _ = interpret("2")
    assert x.value == 2

def test_simple():
    x, _ = interpret("2 + 2")
    assert x.value == 4
    
def test_simple_minus():
    x, _ = interpret("2 - 2")
    assert x.value == 0

def test_plus_in_context():
    x, _ = interpret("""x := 7
    c := method(2 - x)
    c()
    """)
    assert x.value == -5
    
def test_plus_in_method():
    inp = """c := Object clone
    c f := 5
    c g := method(3 + f)
    c g(7)
    """
    res, space = interpret(inp)
    assert res.value == 8
    
