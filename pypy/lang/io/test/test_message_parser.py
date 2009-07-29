from pypy.lang.io.model import W_Message, W_ImmutableSequence
from pypy.lang.io.parserhack import parse, MessageParser
from pypy.lang.io.objspace import ObjSpace


def test_parse_simple():
    space = ObjSpace()
    input = '("a"[])'
    ast = MessageParser(space, input).parse()
    assert ast == W_Message(space, "a", [])
    
def test_parse_simple_next():
    input = '("a"[]("b"[]))'
    space = ObjSpace()
    ast = MessageParser(space, input).parse()
    assert ast == W_Message(space, "a", [], W_Message(space, 'b', []))
    
def test_parse_args():
    input = '("a"[]("+"[("b"[]),]))'
    space = ObjSpace()
    ast = MessageParser(space, input).parse()
    assert ast == W_Message(space, "a", [], W_Message(space, '+', [W_Message(space, 'b', [])]))
    
def test_parse_quoted_strings():
    input = '("setSlot"[("\\"a\\""[]),("b"[]),])'
    space = ObjSpace()
    ast = MessageParser(space, input).parse()
    assert ast == W_Message(space, "setSlot", [W_Message(space, '"a"', []), W_Message(space, 'b', [])])