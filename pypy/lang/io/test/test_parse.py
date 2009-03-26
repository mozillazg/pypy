from pypy.lang.io.model import W_Message
from pypy.lang.io.parserhack import parse
from pypy.lang.io.objspace import ObjSpace

def test_simple():
    space = ObjSpace()
    input = "a b c"
    ast = parse(input, space)
    assert ast == W_Message(space, "a", [], W_Message(space, "b", [], W_Message(space, "c", [],)))
    
def test_simple_args():
    space = ObjSpace()
    input = "a + b c"
    ast = parse(input, space)
    assert ast == W_Message(space, "a", [], W_Message(space, '+', [W_Message(space, "b", [], W_Message(space, 'c', [],))]))

