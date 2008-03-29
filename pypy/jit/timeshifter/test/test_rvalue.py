import py
from pypy.rpython.lltypesystem import lltype
from pypy.jit.timeshifter import rvalue
from pypy.jit.timeshifter import rcontainer
from pypy.jit.timeshifter.test.support import *


def test_create_int_redbox_var():
    jitstate = FakeJITState()
    gv = FakeGenVar()
    box = rvalue.IntRedBox(gv)
    assert not box.is_constant()
    assert box.getgenvar(jitstate) is gv
    gv2 = FakeGenVar()
    box.setgenvar(gv2) # doesn't raises
    assert box.getgenvar(jitstate) is gv2

    
def test_create_int_redbox_const():
    jitstate = FakeJITState()
    gv = FakeGenConst()
    box = rvalue.IntRedBox(gv)
    assert box.is_constant()
    assert box.getgenvar(jitstate) is gv
    gv2 = FakeGenVar()
    py.test.raises(AssertionError, box.setgenvar, gv2)
    
def test_forcevar():
    jitstate = FakeJITState()
    gv = FakeGenVar()
    intbox = rvalue.IntRedBox(gv)
    assert intbox.forcevar(jitstate, rvalue.copy_memo(), False) is intbox
    
    doublebox = rvalue.DoubleRedBox(FakeGenConst())
    box2 = doublebox.forcevar(jitstate, rvalue.copy_memo(), False)
    assert doublebox is not box2
    assert not box2.is_constant()
    assert doublebox.genvar is not box2.genvar

def test_learn_nonzeroness():
    jitstate = FakeJITState()
    gv = FakeGenVar()
    box = rvalue.PtrRedBox(gv)
    assert not box.known_nonzero
    assert box.learn_nonzeroness(jitstate, True)
    assert box.known_nonzero

    assert not box.learn_nonzeroness(jitstate, False)
    assert box.learn_nonzeroness(jitstate, True)

    box = rvalue.PtrRedBox(gv)
    assert box.learn_nonzeroness(jitstate, False)
    assert box.is_constant()
    assert box.genvar._value == "NULL"
    assert box.learn_nonzeroness(jitstate, False)
    assert not box.learn_nonzeroness(jitstate, True)

def test_box_get_set_field():
    jitstate = FakeJITState()
    V0 = FakeGenVar()
    box = rvalue.PtrRedBox(V0)
    STRUCT = lltype.Struct("dummy", ("foo", lltype.Signed))
    desc = rcontainer.StructFieldDesc(FakeRGenOp, lltype.Ptr(STRUCT), "foo", 0)
    box2 = box.op_getfield(jitstate, desc)
    V1 = box2.genvar
    assert box.known_nonzero
    assert jitstate.curbuilder.ops == [('getfield', (('field', STRUCT, 'foo'), V0), V1)]

    jitstate.curbuilder.ops = []
    V42 = FakeGenVar(42)
    valuebox = rvalue.IntRedBox(V42)
    box.op_setfield(jitstate, desc, valuebox)
    assert jitstate.curbuilder.ops == [('setfield', (('field', STRUCT, 'foo'), V0, V42), None)]
