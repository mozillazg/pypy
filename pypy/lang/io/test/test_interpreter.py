from pypy.lang.io.parserhack import interpret

def test_even_simpler():
    x = interpret("2")
    assert x.value == 2

def test_simple():
    x = interpret("2 + 2")
    assert x.value == 4
    
def test_simple_minus():
    x = interpret("2 - 2")
    assert x.value == 0