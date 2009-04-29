from pypy.lang.io.parserhack import parse, interpret
from pypy.lang.io.model import W_Block
import py.test
# "W_Message(space,"method", [W_Message(space,"1", [],), ],)"
def test_get_slot():
    input = "a := 1; a"
    #import pdb; pdb.set_trace()
    res, space = interpret(input)
    assert res.value == 1

def test_parse_method():
    # py.test.skip()
    inp = "a := method(1)\na"
    # import pdb; pdb.set_trace()
    res,space = interpret(inp)
    assert res.value == 1
    
def test_call_method_with_args():
    inp = "a := method(x, x+1)\na(2)"
    res,space = interpret(inp)
    assert res.value == 3
    
def test_call_method_without_all_args():
    inp = "a := method(x, y, z, 42)\na(2)"
    res,space = interpret(inp)
    assert res.value == 42
    
def test_unspecified_args_are_nil():
    inp = "a := method(x, y, z, z)\na(2)"
    res,space = interpret(inp)
    assert res == space.w_nil
    
def test_superfluous_args_are_ignored():
    inp = "a := method(x, y, z, z)\na(1,2,3,4,5,6,6,7)"
    res,space = interpret(inp)
    assert res.value == 3
    
def test_method_proto():
    inp = 'a := method(f)'
    res, space = interpret(inp)
    method = space.w_lobby.slots['a']
    assert method.protos == [space.w_block]
    
def test_block_proto():
    inp = 'Block'
    res,space = interpret(inp)
    assert isinstance(res, W_Block)
    assert res.protos == [space.w_object]
    
def test_call_on_method():
    inp = 'a := method(x, x + 1); getSlot("a") call(3)'
    res, space = interpret(inp)
    assert res.value == 4