from pypy.lang.io.parserhack import interpret
import py
from pypy.lang.io.model import W_Object, W_List, W_Block

def test_map_asObject():
    inp = 'Map clone atPut("1", 12345) atPut("2", 99) atPut("3", 3) atPut("4", 234) asObject'
    res, space = interpret(inp)
    assert res.slots['1'].value == 12345
    assert res.slots['2'].value == 99
    assert res.slots['3'].value == 3
    assert res.slots['4'].value == 234
    
def test_map_asObject_clones_object_proto():
    inp = 'Map clone atPut("1", 12345) atPut("2", 99) atPut("3", 3) atPut("4", 234) asObject'
    res, space = interpret(inp)
    assert isinstance(res, W_Object)
    assert res.protos == [space.w_object]
    
def test_map_as_lit():
    py.test.skip("Depends on ==")
    inp = 'Map clone atPut("1", 12345) atPut("2", 99) atPut("3", 3) atPut("4", 234) asList'
    res, space = interpret(inp)
    assert isinstance(res, W_List)
    l = [(ll.items[0].value, ll.items[1].value) for ll in res.items]
    assert l == [('1', 12345), ('2', 99), ('3', 3), ('4', 234)]
    
def test_new_slot():
    inp = """timers ::= 1"""
    res, space = interpret(inp)
    assert space.w_lobby.slots['timers'].value == 1
    # assert isinstance(space.w_lobby.slots['setTimers'], W_Block)
    
def test_new_slot_complex():
    inp = """a := Object clone 
    a do(
        timers ::= 1
    )
    a setTimers(99)
    a timers"""
    
    res, space = interpret(inp)
    assert res.value == 99
    a = space.w_lobby.slots['a']
    assert 'timers' in a.slots
    assert 'setTimers' in a.slots
    # assert isinstance(a.slots['setTimers'], W_Block)