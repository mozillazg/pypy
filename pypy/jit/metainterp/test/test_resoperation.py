import py
from pypy.jit.metainterp import resoperation as rop
from pypy.jit.metainterp.history import AbstractDescr

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
    
    op = rop.ResOperation(rop.rop.INT_ADD, ['a', 'b'], 15)
    assert op.getarglist() == ['a', 'b']
    assert op.getint() == 15

    mydescr = AbstractDescr()
    op = rop.ResOperation(rop.rop.CALL_f, ['a', 'b'], 15.5, descr=mydescr)
    assert op.getarglist() == ['a', 'b']
    assert op.getfloat() == 15.5
    assert op.getdescr() is mydescr

    op = rop.ResOperation(rop.rop.CALL_p, ['a', 'b'],
                          lltype.nullptr(llmemory.GCREF.TO), descr=mydescr)
    assert op.getarglist() == ['a', 'b']
    assert not op.getpointer()
    assert op.getdescr() is mydescr    

def test_can_malloc():
    from pypy.rpython.lltypesystem import lltype, llmemory

    mydescr = AbstractDescr()
    p = lltype.malloc(llmemory.GCREF.TO)
    assert rop.ResOperation(rop.rop.NEW, [], p).can_malloc()
    call = rop.ResOperation(rop.rop.CALL_i, ['a', 'b'], 3, descr=mydescr)
    assert call.can_malloc()
    assert not rop.ResOperation(rop.rop.INT_ADD, ['a', 'b'], 3).can_malloc()

def test_get_deep_immutable_oplist():
    ops = [rop.ResOperation(rop.rop.INT_ADD, ['a', 'b'], 3)]
    newops = rop.get_deep_immutable_oplist(ops)
    py.test.raises(TypeError, "newops.append('foobar')")
    py.test.raises(TypeError, "newops[0] = 'foobar'")
    py.test.raises(AssertionError, "newops[0].setarg(0, 'd')")
    py.test.raises(AssertionError, "newops[0].setdescr('foobar')")
