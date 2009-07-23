from pypy.lang.io.parserhack import interpret
from pypy.lang.io.model import W_Message
import py

def test_message_arg_at():
    inp = 'a := method(x, y, z, call); a(1,2,3) argAt(1)'
    res, space = interpret(inp)
    assert res.name == '2'
    
    
def test_message_evalArgAt():
    inp = """t := 99; a := method(x, y, z, call); a(1,t,3) evalArgAt(1)"""
    res, space = interpret(inp)
    assert res.value == 99