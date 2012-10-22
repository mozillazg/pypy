import py
from pypy.jit.metainterp import resoperation as rop
from pypy.jit.metainterp.history import AbstractDescr
from pypy.rpython.lltypesystem import lltype, llmemory

class FakeBox(object):
    type = rop.INT
    
    def __init__(self, v):
        self.v = v

    def __eq__(self, other):
        if isinstance(other, str):
            return self.v == other
        return self.v == other.v

    def __ne__(self, other):
        return not self == other

    def __str__(self):
        return self.v

    def is_constant(self):
        return False

    def _get_hash_(self):
        return 75 + self.v

    def eq(self, other):
        return self.v == other.v

class FakeDescr(AbstractDescr):
    def __repr__(self):
        return 'descr'

    def _get_hash_(self):
        return id(self)

def test_concrete_classes():
    cls = rop.opclasses[rop.rop.INT_ADD]
    assert issubclass(cls, rop.PlainResOp)
    assert issubclass(cls, rop.BinaryOp)
    assert cls.getopnum.im_func(cls) == rop.rop.INT_ADD

    cls = rop.opclasses[rop.rop.CALL_i]
    assert issubclass(cls, rop.ResOpWithDescr)
    assert issubclass(cls, rop.N_aryOp)
    assert cls.getopnum.im_func(cls) == rop.rop.CALL_i

    cls = rop.opclasses[rop.rop.GUARD_TRUE]
    assert issubclass(cls, rop.GuardResOp)
    assert issubclass(cls, rop.UnaryOp)
    assert cls.getopnum.im_func(cls) == rop.rop.GUARD_TRUE

def test_mixins_in_common_base():
    INT_ADD = rop.opclasses[rop.rop.INT_ADD]
    assert len(INT_ADD.__bases__) == 1
    BinaryPlainResOp = INT_ADD.__bases__[0]
    assert BinaryPlainResOp.__name__ == 'BinaryPlainResOpInt'
    assert BinaryPlainResOp.__bases__ == (rop.BinaryOp, rop.ResOpInt,
                                          rop.PlainResOp)
    INT_SUB = rop.opclasses[rop.rop.INT_SUB]
    assert INT_SUB.__bases__[0] is BinaryPlainResOp

def test_instantiate():
    from pypy.rpython.lltypesystem import lltype, llmemory
    
    op = rop.create_resop_2(rop.rop.INT_ADD, 15, FakeBox('a'), FakeBox('b'))
    assert op.getarglist() == [FakeBox('a'), FakeBox('b')]
    assert op.getint() == 15

    mydescr = AbstractDescr()
    op = rop.create_resop(rop.rop.CALL_f, 15.5, [FakeBox('a'),
                                           FakeBox('b')], descr=mydescr)
    assert op.getarglist() == [FakeBox('a'), FakeBox('b')]
    assert op.getfloat() == 15.5
    assert op.getdescr() is mydescr

    op = rop.create_resop(rop.rop.CALL_r, lltype.nullptr(llmemory.GCREF.TO),
                          [FakeBox('a'), FakeBox('b')], descr=mydescr)
    assert op.getarglist() == [FakeBox('a'), FakeBox('b')]
    assert not op.getref_base()
    assert op.getdescr() is mydescr    

def test_can_malloc():
    from pypy.rpython.lltypesystem import lltype, llmemory

    mydescr = AbstractDescr()
    p = lltype.malloc(llmemory.GCREF.TO)
    assert rop.create_resop_0(rop.rop.NEW, p).can_malloc()
    call = rop.create_resop(rop.rop.CALL_i, 3, [FakeBox('a'),
                                                FakeBox('b')], descr=mydescr)
    assert call.can_malloc()
    assert not rop.create_resop_2(rop.rop.INT_ADD, 3, FakeBox('a'),
                                  FakeBox('b')).can_malloc()

def test_repr():
    op = rop.create_resop_0(rop.rop.GUARD_NO_EXCEPTION, None)
    assert repr(op) == 'guard_no_exception()'
    c = op._counter
    i0 = rop.create_resop_0(rop.rop.INPUT_i, 3)
    op = rop.create_resop_2(rop.rop.INT_ADD, 3, i0, i0)
    assert repr(op) == 'i%d = int_add(i%d, i%d)' % (c+1, c, c)
    assert str(op) == 'i%d' % (c + 1,)

class MockOpt(object):
    def __init__(self, replacements):
        self.d = replacements

    def get_value_replacement(self, v):
        if v in self.d:
            return FakeBox('rrr')
        return None

def test_hashes_eq():
    arg1 = rop.create_resop_1(rop.rop.FLOAT_NEG, 12.5,
                              rop.create_resop_0(rop.rop.INPUT_f, 3.5))
    op = rop.create_resop_2(rop.rop.FLOAT_ADD, 13.5, rop.ConstFloat(3.0),
                            arg1)
    ope = rop.create_resop_2(rop.rop.FLOAT_ADD, 13.5, rop.ConstFloat(3.0),
                             arg1)
    op1 = rop.create_resop_2(rop.rop.FLOAT_ADD, 13.5, rop.ConstFloat(3.0),
                            rop.ConstFloat(1.0))
    op2 = rop.create_resop_2(rop.rop.FLOAT_ADD, 13.5, rop.ConstFloat(2.0),
                            arg1)
    op3 = rop.create_resop_2(rop.rop.FLOAT_ADD, 13.2, rop.ConstFloat(3.0),
                            arg1)
    assert op1._get_hash_() != op._get_hash_()
    assert op2._get_hash_() != op._get_hash_()
    assert op3._get_hash_() != op._get_hash_()
    assert not op1.eq(op)
    assert not op.eq(op1)
    assert not op2.eq(op)
    assert not op3.eq(op)
    assert ope._get_hash_() == op._get_hash_()
    assert ope.eq(op)

    op = rop.create_resop_0(rop.rop.INPUT_i, 13)
    op1 = rop.create_resop_0(rop.rop.INPUT_i, 15)
    assert op._get_hash_() != op1._get_hash_()
    assert not op.eq(op1)
    S = lltype.GcStruct('S')
    s = lltype.malloc(S)
    nonnull_ref = lltype.cast_opaque_ptr(llmemory.GCREF, s)
    nullref = lltype.nullptr(llmemory.GCREF.TO)
    op = rop.create_resop_1(rop.rop.NEWSTR, nullref, FakeBox(5))
    op1 = rop.create_resop_1(rop.rop.NEWSTR, nonnull_ref, FakeBox(5))
    assert op._get_hash_() != op1._get_hash_()
    assert not op.eq(op1)
    op = rop.create_resop_1(rop.rop.NEWSTR, nullref, FakeBox(5))
    op1 = rop.create_resop_1(rop.rop.NEWSTR, nullref, FakeBox(5))
    assert op._get_hash_() == op1._get_hash_()
    assert op.eq(op1)
    op = rop.create_resop_1(rop.rop.NEWSTR, nullref, FakeBox(5))
    op1 = rop.create_resop_1(rop.rop.NEWSTR, nullref, FakeBox(15))
    assert op._get_hash_() != op1._get_hash_()
    assert not op.eq(op1)

    descr = FakeDescr()
    descr2 = FakeDescr()
    op = rop.create_resop(rop.rop.CALL_i, 12, [FakeBox(0), FakeBox(2),
                                               FakeBox(4)], descr)
    op1 = rop.create_resop(rop.rop.CALL_i, 12, [FakeBox(0), FakeBox(2),
                                                FakeBox(4)], descr2)
    op2 = rop.create_resop(rop.rop.CALL_i, 12, [FakeBox(0), FakeBox(3),
                                                FakeBox(4)], descr)
    op3 = rop.create_resop(rop.rop.CALL_i, 15, [FakeBox(0), FakeBox(2),
                                                FakeBox(4)], descr)
    assert op1._get_hash_() != op._get_hash_()
    assert op2._get_hash_() != op._get_hash_()
    assert op3._get_hash_() != op._get_hash_()
    assert not op.eq(op1)
    assert not op.eq(op2)
    assert not op.eq(op3)

    # class StrangeDescr(AbstractDescr):
    #     def _get_hash_(self):
    #         return 13

    # descr = StrangeDescr()
    # op1 = rop.create_resop(rop.rop.CALL_i, 12, [rop.BoxInt(0),
    #                                             rop.BoxFloat(2.0),
    #                                            rop.BoxPtr(nullref)], descr)
    # op2 = rop.create_resop(rop.rop.CALL_i, 12, [rop.BoxInt(0),
    #                                             rop.BoxFloat(2.0),
    #                                            rop.BoxPtr(nullref)], descr)
    # assert op1._get_hash_() == op2._get_hash_()
    # assert not op1.eq(op2)
