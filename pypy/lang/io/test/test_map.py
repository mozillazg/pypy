from pypy.lang.io.parserhack import parse, interpret
from pypy.lang.io.model import W_Map, W_Number, W_ImmutableSequence, W_List
import py.test

def test_map_proto():
    inp = 'Lobby Core Map'
    res, space = interpret(inp)
    assert res == space.w_map
    assert isinstance(res, W_Map)
    
def test_map_clone():
    inp = 'Map clone'
    res, space = interpret(inp)
    assert isinstance(res, W_Map)
    assert res.protos == [space.w_map]
    assert space.w_map.protos == [space.w_object]
    
def test_at_put():
    inp = 'Map clone atPut("foo", "bar")'
    res, space = interpret(inp)
    keys = [(entry.key.value) for entry in res.items.values()]
    assert keys == ['foo']
    values = [(entry.value.value) for entry in res.items.values()]
    assert values == ['bar']
    
def test_at():
    inp = 'Map clone atPut("foo", "bar") atPut("lorem", "ipsum") at("foo")'
    res, space = interpret(inp)
    assert res.value == 'bar'
    
def test_key_hashing():
    inp = 'Map clone atPut("1", "bar") atPut("nil", "ipsum") atPut("foo", 123) at("nil")'
    res, space = interpret(inp)
    assert res.value == 'ipsum'
    
def test_empty():
    inp = 'Map clone atPut("1", "bar") atPut("nil", "ipsum") atPut("foo", 123) empty'
    res, space = interpret(inp)
    assert res.items == {}
    
def test_atIfAbsentPut():
    inp = 'Map clone atPut("1", nil) atIfAbsentPut("1", "lorem")'
    res, space = interpret(inp)
    assert res == space.w_nil
    
    inp = 'Map clone atPut("2", "bar") atIfAbsentPut("1", "lorem")'
    res, space = interpret(inp)
    assert res.value == 'lorem'
    
def test_has_key():
    inp = 'Map clone atPut("1", nil) atPut("2", "lorem") hasKey("1")'
    res, space = interpret(inp)
    assert res == space.w_true
    
    inp = 'Map clone atPut("1", nil) atPut("2", "lorem") hasKey("99")'
    res, space = interpret(inp)
    assert res == space.w_false
    
def test_size():
    inp = 'Map clone size'
    res, space = interpret(inp)
    assert res.value == 0
    
    inp = 'Map clone atPut("1", nil) atPut("2", "lorem") size'
    res, space = interpret(inp)
    assert res.value == 2
    
def test_remve_at():
    inp = 'Map clone atPut("1", "nil") atPut("2", "lorem") atPut("3", 3) atPut("4", 234) removeAt("2")'
    res, space = interpret(inp)
    keys = [(entry.key.value) for entry in res.items.values()]
    assert keys == ['1', '3', '4']
    values = [(entry.value.value) for entry in res.items.values()]
    assert values == ['nil', 3, 234]
    
def test_has_value():
    inp = 'Map clone atPut("1", "nil") atPut("2", "lorem") atPut("3", 3) atPut("4", 234) hasValue("234")'
    res, space = interpret(inp)
    assert res == space.w_true
    
    inp = 'Map clone atPut("1", "nil") atPut("2", "lorem") atPut("3", 3) atPut("4", 234) hasValue("1234567890")'
    res, space = interpret(inp)
    assert res == space.w_false
    
def test_values():
    inp = 'Map clone atPut("1", 12345) atPut("2", 99) atPut("3", 3) atPut("4", 234) values'
    res, space = interpret(inp)
    assert isinstance(res, W_List)
    values = [x.value for x in res.items]
    should = [12345, 99, 3, 234]
    assert len(should) == len(values)
    for x in values:
        assert x in should

def test_foreach():
    inp = """b := Map clone do(
        atPut("1", 12345) 
        atPut("2", 99) 
        atPut("3", 3) 
        atPut("4", 234)
    )
    c := list()
    b foreach(key, value, c append(list(key, value))); c"""
    res,space = interpret(inp)
    value = sorted([(x.items[0].value, x.items[1].value) for x in res.items])
    assert value == [('1', 12345), ('2', 99), ('3', 3), ('4', 234)]

def test_map_foreach_leaks():
    inp = """b := Map clone do(
        atPut("1", 12345) 
        atPut("2", 99) 
        atPut("3", 3) 
        atPut("4", 234)
    )
    c := list()
    b foreach(key, value, c append(list(key, value))); list(key,value)"""
    res,space = interpret(inp)
    l = [x.value for x in res.items]
    assert l == ['4', 234]
    
def test_keys():
    inp = """b := Map clone do(
        atPut("1", 12345) 
        atPut("2", 99) 
        atPut("3", 3) 
        atPut("4", 234)
    )
    b keys"""
    res, space = interpret(inp)
    keys = sorted([x.value for x in res.items])
    assert keys == ['1', '2', '3', '4']

def test_do_on_map_sum():
    inp = """
    Map do(
        sum := method(
            s := 0
            self foreach(key, value, s := s + value)
            // debugger    
            s
        )
    )
    Map clone atPut("a", 123) atPut("b", 234) atPut("c", 345) sum"""
    res, _ = interpret(inp)
    assert isinstance(res, W_Number)
    assert res.value == 702


def test_map_asObject_inline():
    inp = """
    Map do(
    	asObject := method(
    		o := Object clone
    		self foreach(k, v, o setSlot(k, getSlot("v")))
            o
    	)
    )
    Map clone atPut("1", 12345) atPut("2", 99) atPut("3", 3) atPut("4", 234) asObject"""
    res, space = interpret(inp)
    assert res.slots['1'].value == 12345
    assert res.slots['2'].value == 99
    assert res.slots['3'].value == 3
    assert res.slots['4'].value == 234
