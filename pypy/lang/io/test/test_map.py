from pypy.lang.io.parserhack import parse, interpret
from pypy.lang.io.model import W_Map, W_Number, W_ImmutableSequence
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
    inp = 'Map clone atPut(1, "bar") atPut(nil, "ipsum") atPut("foo", 123) at(nil)'
    res, space = interpret(inp)
    assert res.value == 'ipsum'