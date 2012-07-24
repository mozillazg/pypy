import py
from pypy.jit.metainterp import resoperation as rop
from pypy.jit.metainterp.history import AbstractDescr

class FakeBox(object):
    def __init__(self, v):
        self.v = v

    def __eq__(self, other):
        return self.v == other.v

    def __ne__(self, other):
        return not self == other

    def __str__(self):
        return self.v

    def is_constant(self):
        return False

class FakeDescr(AbstractDescr):
    def __repr__(self):
        return 'descr'

def test_arity_mixins():
    cases = [
        (0, rop.NullaryOp),
        (1, rop.UnaryOp),
        (2, rop.BinaryOp),
        (3, rop.TernaryOp),
        (9, rop.N_aryOp)
        ]

    def test_case(n, cls):
        obj = cls()
        obj.initarglist(range(n))
        assert obj.getarglist() == range(n)
        for i in range(n):
            obj.setarg(i, i*2)
        assert obj.numargs() == n
        for i in range(n):
            assert obj.getarg(i) == i*2
        py.test.raises(IndexError, obj.getarg, n+1)
        py.test.raises(IndexError, obj.setarg, n+1, 0)

    for n, cls in cases:
        test_case(n, cls)

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

    op = rop.create_resop(rop.rop.CALL_p, lltype.nullptr(llmemory.GCREF.TO),
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

def test_get_deep_immutable_oplist():
    ops = [rop.create_resop_2(rop.rop.INT_ADD, 3, FakeBox('a'), FakeBox('b'))]
    newops = rop.get_deep_immutable_oplist(ops)
    py.test.raises(TypeError, "newops.append('foobar')")
    py.test.raises(TypeError, "newops[0] = 'foobar'")
    py.test.raises(AssertionError, "newops[0].setarg(0, 'd')")
    py.test.raises(AssertionError, "newops[0].setdescr('foobar')")

def test_clone():
    mydescr = AbstractDescr()
    op = rop.create_resop_0(rop.rop.GUARD_NO_EXCEPTION, None, descr=mydescr)
    op.setfailargs([3])
    op2 = op.clone()
    assert not op2 is op
    assert op2.getresult() is None
    assert op2.getfailargs() is op.getfailargs()
    op = rop.create_resop_1(rop.rop.INT_IS_ZERO, 1, FakeBox('a'))
    op2 = op.clone()
    assert op2 is not op
    assert op2._arg0 == FakeBox('a')
    assert op2.getint() == 1
    op = rop.create_resop_2(rop.rop.INT_ADD, 1, FakeBox('a'), FakeBox('b'))
    op2 = op.clone()
    assert op2 is not op
    assert op2._arg0 == FakeBox('a')
    assert op2._arg1 == FakeBox('b')
    assert op2.getint() == 1
    op = rop.create_resop_3(rop.rop.STRSETITEM, None, FakeBox('a'),
                            FakeBox('b'), FakeBox('c'))
    op2 = op.clone()
    assert op2 is not op
    assert op2._arg0 == FakeBox('a')
    assert op2._arg1 == FakeBox('b')
    assert op2._arg2 == FakeBox('c')
    assert op2.getresult() is None
    op = rop.create_resop(rop.rop.CALL_i, 13, [FakeBox('a'), FakeBox('b'),
                            FakeBox('c')], descr=mydescr)
    op2 = op.clone()
    assert op2 is not op
    assert op2._args == [FakeBox('a'), FakeBox('b'), FakeBox('c')]
    assert op2.getint() == 13

def test_repr():
    mydescr = FakeDescr()
    op = rop.create_resop_0(rop.rop.GUARD_NO_EXCEPTION, None, descr=mydescr)
    assert repr(op) == 'guard_no_exception(, descr=descr)'
    op = rop.create_resop_2(rop.rop.INT_ADD, 3, FakeBox("a"), FakeBox("b"))
    assert repr(op) == '3 = int_add(a, b)'
