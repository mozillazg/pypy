
""" Direct tests of optmodel.py
"""

from pypy.jit.metainterp.test.test_resoperation import FakeBox, FakeDescr
from pypy.jit.metainterp import resoperation as rop
from pypy.jit.metainterp import optmodel

def test_make_forwarded_copy():    
    op = rop.create_resop_1(rop.rop.INT_IS_ZERO, 1, FakeBox('a'))
    assert not op.is_mutable
    op2 = op.make_forwarded_copy(rop.rop.INT_IS_TRUE)
    assert op2.opnum == rop.rop.INT_IS_TRUE
    assert op2.getarg(0) == FakeBox('a')
    op._forwarded = None
    op2 = op.make_forwarded_copy(rop.rop.INT_IS_TRUE, FakeBox('b'))
    assert op2.is_mutable
    assert op2.opnum == rop.rop.INT_IS_TRUE
    assert op2.getarg(0) == FakeBox('b')
    assert op2 is not op
    op = rop.create_resop_2(rop.rop.INT_ADD, 3, FakeBox("a"), FakeBox("b"))
    op2 = op.make_forwarded_copy(rop.rop.INT_SUB)
    assert op2.opnum == rop.rop.INT_SUB
    assert op2.getarglist() == [FakeBox("a"), FakeBox("b")]
    op._forwarded = None
    op2 = op.make_forwarded_copy(rop.rop.INT_SUB, None, FakeBox("c"))
    assert op2.opnum == rop.rop.INT_SUB
    assert op2.getarglist() == [FakeBox("a"), FakeBox("c")]
    op = rop.create_resop_3(rop.rop.STRSETITEM, None, FakeBox('a'),
                            FakeBox('b'), FakeBox('c'))
    op2 = op.make_forwarded_copy(rop.rop.UNICODESETITEM, None, FakeBox("c"))
    assert op2.opnum == rop.rop.UNICODESETITEM
    assert op2.getarglist() == [FakeBox("a"), FakeBox("c"), FakeBox("c")]    
    mydescr = FakeDescr()
    op = rop.create_resop(rop.rop.CALL_PURE_i, 13, [FakeBox('a'), FakeBox('b'),
                            FakeBox('c')], descr=mydescr)
    op2 = op.make_forwarded_copy(rop.rop.CALL_i)
    assert op2.getarglist() == ['a', 'b', 'c']
    op._forwarded = None
    op2 = op.make_forwarded_copy(rop.rop.CALL_i, [FakeBox('a')])
    assert op2.getarglist() == ['a']

def test_failargs():
    op = rop.create_resop_0(rop.rop.GUARD_NO_OVERFLOW, None)
    assert not hasattr(op, 'setfailargs')
    op2 = op.make_forwarded_copy()
    assert op._forwarded is op2
    op2.setfailargs([1, 2, 3])
    assert op2.getfailargs() == [1, 2, 3]
