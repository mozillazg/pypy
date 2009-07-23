from pypy.lang.io.parserhack import interpret
from pypy.lang.io.model import W_Message, W_Block, W_List, W_ImmutableSequence
import py


def test_message_protos():
    inp = "a := block(1)\na"
    res,space = interpret(inp)
    
    assert res.body.protos == [space.w_message]
    assert space.w_message.protos == [space.w_object]
    
def test_message_arg_at():
    inp = 'a := message(foo(2,3,4)); a argAt(1)'
    res, space = interpret(inp)
    assert res.name == '3'

def test_message_arguments():
  inp = """msg := message(B(C D, E));
  msg arguments"""
  res, space = interpret(inp)
  assert isinstance(res, W_List)
  assert res[0].name == 'C'
  assert res[0].next.name == 'D' 
  assert res[1].name == 'E'

def test_message_name():
    inp = """msg := message(B(C D, E));
    msg name"""
    res, space = interpret(inp)
    assert isinstance(res, W_ImmutableSequence)
    assert res.value == 'B'
    
# def test_setIsActivatable():
#     inp = "a := block(1);a setIsActivateable(true); a"
#     res,space = interpret(inp)
#     
#     assert res.value == 1
#     
#     inp = "a := method(1);a setIsActivateable(false); a"
#     res,space = interpret(inp)
#     
#     assert isinstance(res, W_Block)