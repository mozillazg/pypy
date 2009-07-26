from pypy.lang.io.parserhack import interpret
from pypy.lang.io.model import W_Number
from math import isnan, isinf
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
    
def test_modulo_int_int():
    inp = '5 % 3'
    res, space = interpret(inp)
    assert res.value == 2
    
def test_modulo_int_float():
    inp = '5 % 3.2'
    res, space = interpret(inp)
    assert res.value == 1.7999999999999998
    
def test_module_float_float():
    inp = '5.3 % 3.2'
    res, space = interpret(inp)
    assert res.value == 2.0999999999999996
    
def test_modulo_neg_int_int():
    inp = '-8 % 3'
    res, space = interpret(inp)
    assert res.value == -2
    
def test_modulo_int_neg_int():
    inp = '8 % -3'
    res, space = interpret(inp)
    assert res.value == 2
    
def test_modulo_int_neg_int_neg():
    inp = '-8 % -3'
    res, space = interpret(inp)
    assert res.value == -2
    
def test_modulo_float_float():
    inp = '8.3 % 3.2'
    res, space = interpret(inp)
    assert res.value == 1.9000000000000004
    
def test_modulo_neg_float_float():
    inp = '-8.3 % 3.2'
    res, space = interpret(inp)
    assert res.value == -1.9000000000000004

def test_modulo_float_neg_float():
    inp = '8.3 % -3.2'
    res, space = interpret(inp)
    assert res.value == 1.9000000000000004

def test_modulo_neg_float_neg_float():
    inp = '-8.3 % -3.2'
    res, space = interpret(inp)
    assert res.value == -1.9000000000000004
    
def test_alias_modulo():
    inp = '-8.3 mod(-3.2)'
    res, space = interpret(inp)
    assert res.value == -1.9000000000000004
    
def test_pow():
    inp1 = '5 ** -2.2'
    inp2 = '5 pow(-2.2)'
    res1, space = interpret(inp1)
    res2, space = interpret(inp2)
    assert res1.value >= 0.0289911865471078 \
        and res1.value <= 0.0289911865471079 \
        and res2.value == res1.value

def test_ceil():    
    inp = '3.3 ceil'
    res, space = interpret(inp)
    assert res.value == 4

def test_floor():
    inp = '3.9 floor'
    res, space = interpret(inp)
    assert res.value == 3
    
def test_round():
    inp = '3.3 round'
    res, space = interpret(inp)
    assert res.value == 3
    
    inp = '3.7 round'
    res, space = interpret(inp)
    assert res.value == 4
    
    inp = '3.5 round'
    res, space = interpret(inp)
    assert res.value == 4
    
    inp = '-3.4 round'
    res, space = interpret(inp)
    assert res.value == -3
    
def test_as_number():
    inp = '234 asNumber'
    res, _ = interpret(inp)
    assert res.value == 234
    
def test_divide():
    inp = '3/2'
    res, _ = interpret(inp)
    assert res.value == 1.5
    
def test_division_by_zero():
    inp = '3/0'
    res, _ = interpret(inp)
    assert isinf(res.value)
    
def test_division_zero_by_zero():
    inp = '0/0'
    res, _ = interpret(inp)
    assert isnan(res.value)
    
def test_multiply():
    inp = '6*7'
    res, _  = interpret(inp)
    assert res.value == 42
    
def test_equals():
    inp = '3 == 5'
    res, space = interpret(inp)
    assert res == space.w_false
    
    inp = '5 == 5'
    res, space = interpret(inp)
    assert res == space.w_true
    
def test_compare():
    inp = '7 compare(7)'
    res, space = interpret(inp)
    assert res.value == 0
    
    inp = '7 compare(8)'
    res, space = interpret(inp)
    assert res.value == -1
    
    inp = '7 compare(6)'
    res, space = interpret(inp)
    assert res.value == 1