from pypy.lang.io.model import W_Message, W_ImmutableSequence
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

def test_set_slot():
    space = ObjSpace()
    input = "a := b"
    ast = parse(input, space)
    a = W_Message(space, '"a"', [])
    a.literal_value = space.w_immutable_sequence.clone_and_init('a')
    
    assert ast == W_Message(space, "setSlot", [a, W_Message(space, 'b', [])], )