from pypy.lang.io.parserhack import parse, interpret
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