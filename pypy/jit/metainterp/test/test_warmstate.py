from pypy.rpython.test.test_llinterp import interpret
from pypy.rpython.lltypesystem import lltype, llmemory, rstr
from pypy.rpython.ootypesystem import ootype
from pypy.jit.metainterp.warmstate import wrap, unwrap
from pypy.jit.metainterp.warmstate import equal_whatever, hash_whatever
from pypy.jit.metainterp.history import BoxInt, BoxFloat, BoxPtr
from pypy.jit.metainterp.history import ConstInt, ConstFloat, ConstPtr


def test_unwrap():
    S = lltype.GcStruct('S')
    p = lltype.malloc(S)
    po = lltype.cast_opaque_ptr(llmemory.GCREF, p)
    assert unwrap(lltype.Void, BoxInt(42)) is None
    assert unwrap(lltype.Signed, BoxInt(42)) == 42
    assert unwrap(lltype.Char, BoxInt(42)) == chr(42)
    assert unwrap(lltype.Float, BoxFloat(42.5)) == 42.5
    assert unwrap(lltype.Ptr(S), BoxPtr(po)) == p

def test_wrap():
    def _is(box1, box2):
        return (box1.__class__ == box2.__class__ and
                box1.value == box2.value)
    p = lltype.malloc(lltype.GcStruct('S'))
    po = lltype.cast_opaque_ptr(llmemory.GCREF, p)
    assert _is(wrap(None, 42), BoxInt(42))
    assert _is(wrap(None, 42.5), BoxFloat(42.5))
    assert _is(wrap(None, p), BoxPtr(po))
    assert _is(wrap(None, 42, in_const_box=True), ConstInt(42))
    assert _is(wrap(None, 42.5, in_const_box=True), ConstFloat(42.5))
    assert _is(wrap(None, p, in_const_box=True), ConstPtr(po))

def test_hash_equal_whatever_lltype():
    s1 = rstr.mallocstr(2)
    s2 = rstr.mallocstr(2)
    s1.chars[0] = 'x'; s1.chars[1] = 'y'
    s2.chars[0] = 'x'; s2.chars[1] = 'y'
    def fn(x):
        assert hash_whatever(lltype.typeOf(x), x) == 42
        assert (hash_whatever(lltype.typeOf(s1), s1) ==
                hash_whatever(lltype.typeOf(s2), s2))
        assert equal_whatever(lltype.typeOf(s1), s1, s2)
    fn(42)
    interpret(fn, [42], type_system='lltype')

def test_hash_equal_whatever_ootype():
    def fn(c):
        s1 = ootype.oostring("xy", -1)
        s2 = ootype.oostring("x" + chr(c), -1)
        assert (hash_whatever(ootype.typeOf(s1), s1) ==
                hash_whatever(ootype.typeOf(s2), s2))
        assert equal_whatever(ootype.typeOf(s1), s1, s2)
    fn(ord('y'))
    interpret(fn, [ord('y')], type_system='ootype')
