import py
from pypy.lang.smalltalk import model, shadow, objtable
from pypy.lang.smalltalk.shadow import MethodNotFound
from pypy.lang.smalltalk import classtable, utility

def joinbits(values, lengths):
    result = 0
    for each, length in reversed(zip(values, lengths)):
        result = result << length
        result += each
    return result   

mockclass = classtable.bootstrap_class

def test_new():
    w_mycls = mockclass(0)
    w_myinstance = w_mycls.as_class_get_shadow().new()
    assert isinstance(w_myinstance, model.W_PointersObject)
    assert w_myinstance.getclass() is w_mycls
    assert w_myinstance.shadow_of_my_class() is w_mycls.as_class_get_shadow()

def test_new_namedvars():
    w_mycls = mockclass(3)
    w_myinstance = w_mycls.as_class_get_shadow().new()
    assert isinstance(w_myinstance, model.W_PointersObject)
    assert w_myinstance.getclass() is w_mycls
    assert w_myinstance.fetch(0) is objtable.w_nil
    py.test.raises(IndexError, lambda: w_myinstance.fetch(3))
    w_myinstance.store(1, w_myinstance)
    assert w_myinstance.fetch(1) is w_myinstance

def test_bytes_object():
    w_class = mockclass(0, format=shadow.BYTES)
    w_bytes = w_class.as_class_get_shadow().new(20)
    assert w_bytes.getclass() is w_class
    assert w_bytes.size() == 20
    assert w_class.as_class_get_shadow().instsize() == 0
    assert w_bytes.getchar(3) == "\x00"
    w_bytes.setchar(3, "\xAA")
    assert w_bytes.getchar(3) == "\xAA"
    assert w_bytes.getchar(0) == "\x00"
    py.test.raises(IndexError, lambda: w_bytes.getchar(20))

def test_word_object():
    w_class = mockclass(0, format=shadow.WORDS)
    w_bytes = w_class.as_class_get_shadow().new(20)
    assert w_bytes.getclass() is w_class
    assert w_bytes.size() == 20
    assert w_class.as_class_get_shadow().instsize() == 0
    assert w_bytes.getword(3) == 0
    w_bytes.setword(3, 42)  
    assert w_bytes.getword(3) == 42
    assert w_bytes.getword(0) == 0
    py.test.raises(IndexError, lambda: w_bytes.getword(20))

def test_method_lookup():
    w_class = mockclass(0)
    shadow = w_class.as_class_get_shadow()
    shadow.installmethod("foo", 1)
    shadow.installmethod("bar", 2)
    w_subclass = mockclass(0, w_superclass=w_class)
    subshadow = w_subclass.as_class_get_shadow()
    assert subshadow.s_superclass() is shadow
    subshadow.installmethod("foo", 3)
    shadow.initialize_methoddict()
    subshadow.initialize_methoddict()
    assert shadow.lookup("foo") == 1
    assert shadow.lookup("bar") == 2
    py.test.raises(MethodNotFound, shadow.lookup, "zork")
    print subshadow.methoddict
    assert subshadow.lookup("foo") == 3
    assert subshadow.lookup("bar") == 2
    py.test.raises(MethodNotFound, subshadow.lookup, "zork")

def test_w_compiledin():
    w_super = mockclass(0)
    w_class = mockclass(0, w_superclass=w_super)
    supershadow = w_super.as_class_get_shadow()
    supershadow.installmethod("foo", model.W_CompiledMethod(0))
    classshadow = w_class.as_class_get_shadow()
    classshadow.initialize_methoddict()
    assert classshadow.lookup("foo").w_compiledin is w_super

def test_compiledmethod_setchar():
    w_method = model.W_CompiledMethod(3)
    w_method.setchar(0, "c")
    assert w_method.bytes == "c\x00\x00"

def test_hashes():
    w_five = model.W_SmallInteger(5)
    assert w_five.gethash() == 5
    w_class = mockclass(0)
    w_inst = w_class.as_class_get_shadow().new()
    assert w_inst.hash == w_inst.UNASSIGNED_HASH
    h1 = w_inst.gethash()
    h2 = w_inst.gethash()
    assert h1 == h2
    assert h1 == w_inst.hash

def test_compiledmethod_at0():
    w_method = model.W_CompiledMethod()
    w_method.bytes = "abc"
    w_method.header = 100
    w_method.literals = [ 'lit1', 'lit2' ]
    w_method.literalsize = 2
    assert utility.unwrap_int(w_method.at0(0)) == 100
    assert w_method.at0(4) == 'lit1'
    assert w_method.at0(8) == 'lit2'
    assert utility.unwrap_int(w_method.at0(12)) == ord('a')
    assert utility.unwrap_int(w_method.at0(13)) == ord('b')
    assert utility.unwrap_int(w_method.at0(14)) == ord('c')

def test_compiledmethod_atput0():
    w_method = model.W_CompiledMethod(3)
    newheader = joinbits([0,2,0,0,0,0],[9,8,1,6,4,1])
    assert w_method.getliteralsize() == 0
    w_method.atput0(0, utility.wrap_int(newheader))
    assert w_method.getliteralsize() == 8 # 2 from new header * BYTES_PER_WORD (= 4)
    w_method.atput0(4, 'lit1')
    w_method.atput0(8, 'lit2')
    w_method.atput0(12, utility.wrap_int(ord('a')))
    w_method.atput0(13, utility.wrap_int(ord('b')))
    w_method.atput0(14, utility.wrap_int(ord('c')))
    assert utility.unwrap_int(w_method.at0(0)) == newheader
    assert w_method.at0(4) == 'lit1'
    assert w_method.at0(8) == 'lit2'
    assert utility.unwrap_int(w_method.at0(12)) == ord('a')
    assert utility.unwrap_int(w_method.at0(13)) == ord('b')
    assert utility.unwrap_int(w_method.at0(14)) == ord('c')

def test_equals(w_o1=model.W_PointersObject(None,0), w_o2=None):
    if w_o2 is None:
        w_o2 = w_o1
    assert w_o1.equals(w_o2)
    assert w_o2.equals(w_o1)
    
def test_not_equals(w_o1=model.W_PointersObject(None,0),w_o2=model.W_PointersObject(None,0)):
    assert not w_o1.equals(w_o2)
    assert not w_o2.equals(w_o1)
    w_o2 = model.W_SmallInteger(2)
    assert not w_o1.equals(w_o2)
    assert not w_o2.equals(w_o1)
    w_o2 = model.W_Float(5.5)
    assert not w_o1.equals(w_o2)
    assert not w_o2.equals(w_o1)

def test_intfloat_equals():
    test_equals(model.W_SmallInteger(1), model.W_SmallInteger(1))
    test_equals(model.W_SmallInteger(100), model.W_SmallInteger(100))
    test_equals(model.W_Float(1.100), model.W_Float(1.100))

def test_intfloat_notequals():
    test_not_equals(model.W_SmallInteger(1), model.W_Float(1))
    test_not_equals(model.W_Float(100), model.W_SmallInteger(100))
    test_not_equals(model.W_Float(1.100), model.W_Float(1.200))
    test_not_equals(model.W_SmallInteger(101), model.W_SmallInteger(100))

def test_charequals():
    test_equals(utility.wrap_char('a'), utility.wrap_char('a'))
    test_equals(utility.wrap_char('d'), utility.wrap_char('d'))

def test_not_charequals():
    test_not_equals(utility.wrap_char('a'), utility.wrap_char('d'))
    test_not_equals(utility.wrap_char('d'), utility.wrap_int(3))
    test_not_equals(utility.wrap_char('d'), utility.wrap_float(3.0))
