from pypy.lang.io.parserhack import interpret
from pypy.lang.io.model import W_Object, W_Number, W_Message
import py

def test_compiler_is_present():
    inp = "Compiler"
    res, space = interpret(inp)
    assert isinstance(res, W_Object)
    assert res.slots['type'].value == 'Compiler'
    assert res.protos == [space.w_object]

def test_parse_number():
    inp = 'Compiler messageForString("42")'
    res, space = interpret(inp)
    assert isinstance(res, W_Message)
    assert res.name == '42'
    assert isinstance(res.cached_result, W_Number)
    assert res.cached_result.value == 42
    
def test_parse_hexnumber():
    inp = 'Compiler messageForString("0xf")'
    res, space = interpret(inp)
    assert isinstance(res, W_Message)
    assert res.name == '0xf'
    assert isinstance(res.cached_result, W_Number)
    assert res.cached_result.value == 15
    
def test_parse_message_with_artguments():
    inp = 'Compiler messageForString("a(1,2)")'
    res, space = interpret(inp)
    assert isinstance(res, W_Message)
    assert res.name == 'a'
    assert len(res.arguments) == 2
    assert res.arguments[0].name == '1'
    assert res.arguments[1].name == '2'
    
def test_parse_message_chain():
    inp = 'Compiler messageForString("1 2")'
    res, space = interpret(inp)
    assert isinstance(res, W_Message)
    assert res.name == '1'
    assert isinstance(res.next, W_Message)
    assert res.next.name == '2'
    assert res.next.cached_result.value == 2
    
def test_parse_longer_message_chain():
    inp = 'Compiler messageForString("1 2 3 4 5 6")'
    res, space = interpret(inp)
    
    assert isinstance(res, W_Message)
    assert res.name == '1'
    
    n = res.next
    assert isinstance(n, W_Message)
    assert n.name == '2'

    n = n.next
    assert isinstance(n, W_Message)
    assert n.name == '3'
    
    n = n.next
    assert isinstance(n, W_Message)
    assert n.name == '4'

    n = n.next
    assert isinstance(n, W_Message)
    assert n.name == '5'

    n = n.next
    assert isinstance(n, W_Message)
    assert n.name == '6'
    
def test_parse_empty_input():
    inp = 'Compiler messageForString("")'
    res, space = interpret(inp)
    assert isinstance(res, W_Message)
    assert res.name == 'nil'