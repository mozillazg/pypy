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
    keys = [(key.value) for key in res.items.keys()]
    assert keys == ['foo']
    values = [(val.value) for val in res.items.values()]
    assert values == ['bar']