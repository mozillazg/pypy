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
    shadow.methoddict["foo"] = 1
    shadow.methoddict["bar"] = 2
    w_subclass = mockclass(0, w_superclass=w_class)
    subshadow = w_subclass.as_class_get_shadow()
    assert subshadow.s_superclass is shadow
    subshadow.methoddict["foo"] = 3
    assert shadow.lookup("foo") == 1
    assert shadow.lookup("bar") == 2
    py.test.raises(MethodNotFound, shadow.lookup, "zork")
    assert subshadow.lookup("foo") == 3
    assert subshadow.lookup("bar") == 2
    py.test.raises(MethodNotFound, subshadow.lookup, "zork")

def test_w_compiledin():
    w_super = mockclass(0)
    w_class = mockclass(0, w_superclass=w_super)
    supershadow = w_super.as_class_get_shadow()
    supershadow.installmethod("foo", model.W_CompiledMethod(0))
    classshadow = w_class.as_class_get_shadow()
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

def test_compiledmethod_fetchbyte():
    w_method = model.W_CompiledMethod()
    w_method.bytes = "abc"
    w_method.literalsize = 2
    w_method.fetchbyte(9) == ord('a')
    w_method.fetchbyte(10) == ord('b')
    w_method.fetchbyte(11) == ord('c')

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
