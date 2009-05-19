from pypy.lang.io.parserhack import parse, interpret
from pypy.lang.io.model import W_Object
import py.test


def test_object_do():
    inp = '4 do(a := 23)'
    res, space = interpret(inp)
    assert res.slots['a'].value == 23
    assert res.value == 4
    
def test_object_do_multiple_slots():
    inp = 'Object do(a := 23; b := method(a + 5); a := 1); Object b'
    res, space = interpret(inp)
    assert res.value == 6
    assert space.w_object.slots['a'].value == 1
    
def test_object_anon_slot():
    inp = 'Object getSlot("+")("foo")'
    res, space = interpret(inp)
    assert res.value == 'foo'