from pypy.lang.io.parserhack import parse, interpret
from pypy.lang.io.model import W_Block, W_Message
import py.test

def test_parse_block():
    inp = "a := block(1)\na"
    res,space = interpret(inp)
    assert isinstance(res, W_Block)
    assert res.body == W_Message(space, '1', [], None)
    
def test_call_block():
    inp = "a := block(1)\na call"
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
    
    
def test_block_proto_evals_to_nil():
    inp = 'Block call'
    res, space = interpret(inp)
    assert res == space.w_nil