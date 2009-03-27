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
    
