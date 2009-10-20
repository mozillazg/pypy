from pypy.rpython.test.test_llinterp import interpret
from pypy.rpython.lltypesystem import lltype, llmemory, rstr
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.annlowlevel import llhelper
from pypy.jit.metainterp.warmstate import wrap, unwrap
from pypy.jit.metainterp.warmstate import equal_whatever, hash_whatever
from pypy.jit.metainterp.warmstate import WarmEnterState
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


def test_make_jitcell_getter_default():
    class FakeWarmRunnerDesc:
        green_args_spec = [lltype.Signed, lltype.Float]
    class FakeJitCell:
        pass
    state = WarmEnterState(FakeWarmRunnerDesc())
    get_jitcell = state.make_jitcell_getter_default(FakeJitCell)
    cell1 = get_jitcell((42, 42.5))
    assert isinstance(cell1, FakeJitCell)
    cell2 = get_jitcell((42, 42.5))
    assert cell1 is cell2
    cell3 = get_jitcell((41, 42.5))
    cell4 = get_jitcell((42, 0.25))
    assert cell1 is not cell3 is not cell4 is not cell1

def test_make_jitcell_getter():
    class FakeWarmRunnerDesc:
        green_args_spec = [lltype.Float]
        get_jitcell_at_ptr = None
    state = WarmEnterState(FakeWarmRunnerDesc())
    get_jitcell = state.make_jitcell_getter()
    cell1 = get_jitcell((1.75,))
    cell2 = get_jitcell((1.75,))
    assert cell1 is cell2

def test_make_jitcell_getter_custom():
    class FakeJitCell:
        _TYPE = llmemory.GCREF
    celldict = {}
    def getter(x, y):
        return celldict[x, y]
    def setter(newcell, x, y):
        newcell.x = x
        newcell.y = y
        celldict[x, y] = newcell
    GETTER = lltype.Ptr(lltype.FuncType([lltype.Signed, lltype.Float],
                                        llmemory.GCREF))
    SETTER = lltype.Ptr(lltype.FuncType([llmemory.GCREF, lltype.Signed,
                                         lltype.Float], lltype.Void))
    class FakeWarmRunnerDesc:
        rtyper = None
        cpu = None
        get_jitcell_at_ptr = llhelper(GETTER, getter)
        set_jitcell_at_ptr = llhelper(SETTER, setter)
    #
    state = WarmEnterState(FakeWarmRunnerDesc())
    get_jitcell = state.make_jitcell_getter_custom(FakeJitCell)
    cell1 = get_jitcell((5, 42.5))
    assert isinstance(cell1, FakeJitCell)
    assert cell1.x == 5
    assert cell1.y == 42.5
    cell2 = get_jitcell((5, 42.5))
    assert cell2 is cell1
    cell3 = get_jitcell((41, 42.5))
    cell4 = get_jitcell((42, 0.25))
    assert cell1 is not cell3 is not cell4 is not cell1

def test_make_set_future_values():
    future_values = {}
    class FakeCPU:
        def set_future_value_int(self, j, value):
            future_values[j] = "int", value
        def set_future_value_float(self, j, value):
            future_values[j] = "float", value
    class FakeWarmRunnerDesc:
        cpu = FakeCPU()
        red_args_types = ["int", "float"]
        class metainterp_sd:
            virtualizable_info = None
    #
    state = WarmEnterState(FakeWarmRunnerDesc())
    set_future_values = state.make_set_future_values()
    set_future_values(5, 42.5)
    assert future_values == {
        0: ("int", 5),
        1: ("float", 42.5),
    }
