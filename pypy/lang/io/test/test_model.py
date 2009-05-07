from pypy.lang.io.model import parse_literal, W_Number, W_Object
from pypy.lang.io.objspace import ObjSpace

def test_parse_literal():
    space = ObjSpace()
    assert parse_literal(space, "2").value == 2
    assert parse_literal(space, "0xFF").value == 255
    assert parse_literal(space, "2.3").value == 2.3
    assert parse_literal(space, '"a"').value == 'a'
    assert parse_literal(space, 'a') is None

def test_lookup():
    obj = W_Object(None, )
    assert obj.lookup("fail") is None
    a = obj.slots['fail'] = W_Object(None)
    assert obj.lookup("fail") is a

def test_lookup2():
    obj1 = W_Object(None)
    obj2 = W_Object(None)
    a = obj2.slots['foo'] = W_Object(None)
    obj1.protos.append(obj2)
    assert obj1.lookup("foo") is a
    
def test_protos():
    space = ObjSpace()
    x = W_Number(space, 2)
    assert x.protos == [space.w_number]

def test_object_clone():
    space = ObjSpace()
    x = W_Object(space)
    assert x.clone().protos == [x] 
    

def test_clone_number():
    space = ObjSpace()
    x = W_Number(space, 2)
    xx = x.clone()
    assert xx.protos == [x]
    assert isinstance(xx, W_Number)
    
def test_lookup_cycles():
    obj = W_Object(None, )
    obj.protos.append(obj)
    a = obj.slots['not_fail'] = W_Object(None)
    assert obj.lookup("not_fail") is a
    assert obj.lookup('fail') is None
    
def test_lookup_cycling_complex():
    space = ObjSpace()
    a = W_Object(None, )
    b = W_Object(None, )
    c = W_Object(None, )
    a.protos += [a, c]
    c.protos += [b]
    b.protos += [b]
    a.slots['a'] = W_Number(space, 1)
    b.slots['b'] = W_Number(space, 2)
    c.slots['c'] = W_Number(space, 3)
    assert a.lookup('fail') is None
    assert a.lookup('a').value == 1
    assert a.lookup('b').value == 2
    assert a.lookup('c').value == 3