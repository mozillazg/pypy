import py
from pypy.lang.smalltalk import objspace

space = objspace.ObjSpace()

def ismetaclass(w_cls):
    # Heuristic to detect if this is a metaclass. Don't use apart
    # from in this test file, because classtable['w_Metaclass'] is
    # bogus after loading an image.
    return w_cls.w_class is space.classtable['w_Metaclass']

def test_every_class_is_an_instance_of_a_metaclass():
    for (nm, w_cls) in space.classtable.items():
        assert ismetaclass(w_cls) or ismetaclass(w_cls.w_class)

def test_every_metaclass_inherits_from_class_and_behavior():
    s_Class = space.classtable['w_Class'].as_class_get_shadow(space)
    s_Behavior = space.classtable['w_Behavior'].as_class_get_shadow(space)
    for (nm, w_cls) in space.classtable.items():
        if ismetaclass(w_cls):
            shadow = w_cls.as_class_get_shadow(space)
            assert shadow.inherits_from(s_Class)
    assert s_Class.inherits_from(s_Behavior)

def test_metaclass_of_metaclass_is_an_instance_of_metaclass():
    w_Metaclass = space.classtable['w_Metaclass']
    assert w_Metaclass.w_class.w_class is w_Metaclass

def test_ruint():
    from pypy.rlib.rarithmetic import r_uint
    import sys
    for num in [0, 1, 41, 100, 2**31, sys.maxint + 1]:
        num = r_uint(num)
        assert space.unwrap_uint(space.wrap_uint(num)) == num
    for num in [-1, -100, -sys.maxint]:
        py.test.raises(objspace.WrappingError, space.wrap_uint, num)
    for obj in [space.wrap_char('a'), space.wrap_int(-1)]:
        py.test.raises(objspace.UnwrappingError, space.unwrap_uint, obj)
    byteobj = space.wrap_uint(sys.maxint + 1)
    byteobj.bytes.append('\x01')
    py.test.raises(objspace.UnwrappingError, space.unwrap_uint, byteobj)
    

