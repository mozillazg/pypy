from pypy.lang.io.parserhack import interpret
from pypy.lang.io.model import W_Message
import py

def test_message_arg_at():
    inp = 'a := method(x, y, z, call); a(1,2,3) argAt(1)'
    res, space = interpret(inp)
    assert res.name == '2'
    
    
def test_call_evalArgAt():
    inp = """t := 99; a := method(x, y, z, call); a(1,t,3) evalArgAt(1)"""
    res, space = interpret(inp)
    assert res.value == 99
    
def test_call_sender():
    inp = """foo := Object clone
    foo a := method(x, y, z, call); 
    foo a(1,2,3) sender"""
    res, space = interpret(inp)
    assert res == space.w_lobby
    
def test_call_receiver():
    inp = """foo := Object clone
    foo a := method(x, y, z, call); 
    foo a(1,2,3) target"""
    res, space = interpret(inp)
    assert res == space.w_lobby.slots['foo']