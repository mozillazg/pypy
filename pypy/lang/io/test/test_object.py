from pypy.lang.io.parserhack import parse, interpret
from pypy.lang.io.model import W_Object, W_Message, W_Number
import py.test


def test_object_do():
    inp = '4 do(a := 23)'
    res, space = interpret(inp)
    assert res.slots['a'].value == 23
    assert res.value == 4
    
def test_do_on_map():
    inp = """
    Map do(
        get := method(i, 
            self at(i)
        )
    )
    Map clone atPut("a", 123) atPut("b", 234) atPut("c", 345) get("b")"""
    res, _ = interpret(inp)
    assert isinstance(res, W_Number)
    assert res.value == 234
    
def test_object_do_multiple_slots():
    inp = 'Object do(a := 23; b := method(a + 5); a := 1); Object b'
    res, space = interpret(inp)
    assert res.value == 6
    assert space.w_object.slots['a'].value == 1
    
def test_object_anon_slot():
    inp = 'Object getSlot("+")("foo")'
    res, space = interpret(inp)
    assert res.value == 'foo'

def test_object_has_slot():
    inp = 'Object hasSlot("foo")'
    res, space = interpret(inp)
    assert res is space.w_false
    
    inp2 = 'Object hasSlot("clone")'
    res, space = interpret(inp2)
    assert res is space.w_true
        
def test_object_question_mark_simple():
    inp = 'Object do(a := 1); Object ?a'
    res, space = interpret(inp)
    assert res is not space.w_nil
    assert res.value == 1
    
    inp2 = 'Object ?a'
    res, space = interpret(inp2)
    assert res is space.w_nil

def test_object_message():
    inp = 'message(foo)'
    res, space = interpret(inp)
    assert isinstance(res, W_Message)
    assert res.name == 'foo'
    
def test_object_substract():
    inp = '-1'
    res, space = interpret(inp)
    assert res.value == -1
    
    inp = '-"a"'
    py.test.raises(Exception, "interpret(inp)")