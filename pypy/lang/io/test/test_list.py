from pypy.lang.io.parserhack import parse, interpret
from pypy.lang.io.model import W_List, W_Number
import py.test


def test_parse_empty_list():
    inp = "a := list()\na"
    res,space = interpret(inp)
    assert isinstance(res, W_List)
    assert res.items == []
    
def test_parse_list():
    inp = "a := list(1,2,3)\na"
    res,space = interpret(inp)
    assert isinstance(res, W_List)
    assert res.items == [W_Number(space, 1), W_Number(space, 2), W_Number(space, 3)]
    
def test_list_proto():
    inp = "a := list(1,2,3)\na"
    res,space = interpret(inp)
    assert isinstance(res, W_List)
    assert res.protos == [space.w_list]
    assert space.w_list.protos == [space.w_object]

def test_list_append():
    inp = "a := list(); a append(1)"
    res,space = interpret(inp)
    assert res.items == [W_Number(space, 1)]

def test_list_append_multiple():
    inp = "a := list(1,2); a append(3,4,5)"
    res,space = interpret(inp)
    assert res.items == [W_Number(space, 1), 
                            W_Number(space, 2),
                            W_Number(space, 3),
                            W_Number(space, 4),
                            W_Number(space, 5)]
    
def test_list_at():
    inp = "a := list(1,2,3); a at(2)"
    res,space = interpret(inp)
    assert res.value == 3
    
def test_list_at_out_of_range_is_nil():
    inp = "a := list(1,2,3); a at(1234)"
    res,space = interpret(inp)
    assert res == space.w_nil
    
def test_list_at_requires_arg():
    inp = "a := list(1,2,3); a at()"
    # Unspecified exception until error handling are introduced
    assert py.test.raises(Exception, 'interpret(inp)')

def test_list_at_requires_numeric_arg():
    inp = 'a := list(1,2,3); a at("2")'
    # Unspecified exception until error handling are introduced
    assert py.test.raises(Exception, 'interpret(inp)')
    
def test_list_foreach_key_value_returns_last():
    inp = 'a := list(1, 2, 3); a foreach(key, value, key+value)'
    res,space = interpret(inp)
    assert res.value == 5
    
def test_list_foreach_value_returns_last():
    inp = 'c := 99; a := list(1, 2, 3); a foreach(value, c)'
    res,space = interpret(inp)
    assert res.value == 99
    
def test_list_foreach_wo_args_returns_last():
    inp = 'c := 99; a := list(1, 2, 3); a foreach(c)'
    res,space = interpret(inp)
    assert res.value == 99
        
def test_list_key_value():
    inp = 'b := list(); a := list(99, 34); a foreach(key, value, b append(list(key, value))); b'
    res,space = interpret(inp)
    value = [(x.items[0].value, x.items[1].value) for x in res.items]
    assert value == [(0, 99), (1, 34)]
    
def test_list_foreach_leaks_variables():
    inp = 'b := list(); a := list(99, 34); a foreach(key, value, b append(list(key, value))); key+value'
    res,space = interpret(inp)
    assert res.value == 35
    
def test_list_with():
    inp = 'a := list(1,2,3); b := a with(99, 34); list(a,b)'
    res, space = interpret(inp)
    a, b = res.items
    # a is proto of b
    assert b.protos == [a]
    
    # b has 1,2,3,99,34 as element
    assert [x.value for x in b.items] == [1, 2, 3, 99, 34]
    
def test_list_index_of():
    inp = 'list(9,8,7,7) indexOf(7)'
    res, _ = interpret(inp)
    assert res.value == 2
    
    inp = 'list(9,8,7,7) indexOf(42)'
    res, space = interpret(inp)
    assert res == space.w_nil
    
def test_list_contains():
    inp = 'list(9,8,7,7) contains(7)'
    res, space = interpret(inp)
    assert res == space.w_true
    
    inp = 'list(9,8,7,7) contains(42)'
    res, space = interpret(inp)
    assert res == space.w_false
    
def test_list_size():
    inp = 'list(9,8,7,7) size'
    res, _ = interpret(inp)
    assert res.value == 4
    
    inp = 'list() size'
    res, _ = interpret(inp)
    assert res.value ==  0
    
def test_list_first_empty():
    inp = 'list() first'
    res, space = interpret(inp)
    assert res == space.w_nil
    
    inp = 'a := list(); a first(3)'
    res, space = interpret(inp)
    assert isinstance(res, W_List)
    assert len(res.items) == 0
    assert res.protos == [space.w_lobby.slots['a']]
    
def test_list_first():
    inp = 'a := list(9,8,7,6,5,4,3,2,1,1); a first'
    res, space = interpret(inp)
    assert isinstance(res, W_Number)
    assert res.value == 9
    
def test_list_first_n():
    inp = 'a := list(9,8,7,6,5,4,3,2,1,1); a first(3)'
    res, space = interpret(inp)
    assert isinstance(res, W_List)
    assert [x.value for x in res.items] == [9,8,7]
    assert res.protos == [space.w_lobby.slots['a']]
    
def test_list_last():
    inp = 'a := list(9,8,7,6,5,4,3,2,1,100); a last'
    res, space = interpret(inp)
    assert isinstance(res, W_Number)
    assert res.value == 100
    
def test_list_last_n():
    inp = 'a := list(9,8,7,6,5,4,3,2,1,100); a last(3)'
    res, space = interpret(inp)
    assert isinstance(res, W_List)
    assert [x.value for x in res.items] == [2, 1, 100]
    assert res.protos == [space.w_lobby.slots['a']]

def test_list_first_n_overflow():    
    inp = 'a := list(9,8,7,6,5,4,3,2,1,100); a first(20)'
    res, space = interpret(inp)
    assert isinstance(res, W_List)
    assert [x.value for x in res.items] == [9,8,7,6,5,4,3,2,1,100]
    assert res.protos == [space.w_lobby.slots['a']]
    

def test_list_last_n_overflow():
    inp = 'a := list(9,8,7,6,5,4,3,2,1,100); a last(20)'
    res, space = interpret(inp)
    assert isinstance(res, W_List)
    assert [x.value for x in res.items] == [9,8,7,6,5,4,3,2,1,100]
    assert res.protos == [space.w_lobby.slots['a']]


def test_empty_list_first_n():
    inp = 'a := list(); a first(20)'
    res, space = interpret(inp)
    assert isinstance(res, W_List)
    assert [x.value for x in res.items] == []
    assert res.protos == [space.w_lobby.slots['a']]

def test_empty_list_last_n():
    inp = 'a := list(); a last(20)'
    res, space = interpret(inp)
    assert isinstance(res, W_List)
    assert [x.value for x in res.items] == []
    assert res.protos == [space.w_lobby.slots['a']]

def test_reverse_in_place():
    inp = 'a := list(9,8,7,6,5,4,3,2,1,100); a reverseInPlace'
    res, space = interpret(inp)
    assert isinstance(res, W_List)
    assert [x.value for x in res.items] == [100,1,2,3,4,5,6,7,8,9]
    
def test_remove_all():
    inp = 'a := list(9,8,7,6,5,4,3,2,1,100); a removeAll; a'
    res, space = interpret(inp)
    assert isinstance(res, W_List)
    assert [x.value for x in res.items] == []

def test_at_put():
    inp = 'a := list(9,8,7,6,5,4,3,2,1,100); a atPut(3, 1045)'
    res, space = interpret(inp)
    assert isinstance(res, W_List)
    assert [x.value for x in res.items] == [9,8,7, 1045, 5, 4, 3, 2, 1, 100]
    
def test_at_put_raises():
    inp = 'a := list(9,8,7,6,5,4,3,2,1,100); a atPut(1000, 1045)'
    py.test.raises(Exception, 'interpret(inp)')

def test_at_put_wo_value():
    inp = 'a := list(9,8,7,6,5,4,3,2,1,100); a atPut(3)'
    res, space = interpret(inp)
    assert isinstance(res, W_List)
    nums = [W_Number(space, i) for i in range(9, 0, -1)]
    nums[3] = space.w_nil
    nums.append(W_Number(space, 100))
    assert [x for x in res.items] == nums
