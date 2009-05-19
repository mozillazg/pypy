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
    
def test_method_binding():
    inp = 'c := Object clone; c setSlot("b", 123); c setSlot("a", method(b)); c a'
    res, space = interpret(inp)
    assert res.value == 123
    
def test_method_modified_binding():
    inp = 'c := Object clone; c setSlot("b",123); c setSlot("a", method(x, b)); c setSlot("b",1); c a(3)'
    res, space = interpret(inp)
    assert res.value == 1


def test_block_binding():
    inp = 'c := Object clone; b := 123; c setSlot("a", block(x, b)); c a call(3)'
    res, space = interpret(inp)
    assert res.value == 123

def test_block_modified_binding():
    inp = 'c := Object clone; b := 42; c setSlot("a", block(x, b)); b := 1; c a call(3)'
    res, space = interpret(inp)
    assert res.value == 1
    
def test_block_call_slot():
    py.test.skip()
    inp = """
    Object do(
      /*doc Object inlineMethod
      Creates a method which is executed directly in a receiver (no Locals object is created).
      <br/>
      <pre>
      Io> m := inlineMethod(x := x*2)
      Io> x := 1
      ==> 1
      Io> m
      ==> 2
      Io> m
      ==> 4
      Io> m
      ==> 8
      </pre>
      */  
    	inlineMethod := method(call message argAt(0) setIsActivatable(true))
    )
    m := inlineMethod(x := x*2)
    x := 1
    m
    m
    """
    # from A0_List.io
    res, space = interpret(inp)
    assert space.w_object.slots['inlineMethod'] is not None
    assert res.value == 4
    