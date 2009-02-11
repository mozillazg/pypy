import py
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from history import ResOperation, MergePoint, Jump
from history import BoxInt, BoxPtr, ConstInt, ConstPtr
from codegen386.runner import CPU, GuardFailed

class FakeStats(object):
    pass

class FakeMetaInterp(object):
    def handle_guard_failure(self, gf):
        assert isinstance(gf, GuardFailed)
        assert gf.merge_point.opname == 'merge_point'
        self.gf = gf
        self.recordedvalues = [
                gf.cpu.getvaluebox(gf.frame, gf.merge_point, i).value
                    for i in range(len(gf.merge_point.args))]
        gf.make_ready_for_return(BoxInt(42))

MY_VTABLE = lltype.Struct('my_vtable')    # for tests only

S = lltype.GcForwardReference()
S.become(lltype.GcStruct('S', ('typeptr', lltype.Ptr(MY_VTABLE)),
                              ('value', lltype.Signed),
                              ('next', lltype.Ptr(S)),
                         hints = {'typeptr': True}))
T = lltype.GcStruct('T', ('parent', S),
                         ('next', lltype.Ptr(S)))
U = lltype.GcStruct('U', ('parent', T),
                         ('next', lltype.Ptr(S)))

# ____________________________________________________________

def test_execute_int_operation():
    cpu = CPU(rtyper=None, stats=FakeStats())
    assert (cpu.execute_operation('int_sub', [BoxInt(45), BoxInt(3)], 'int')
            .value == 42)
    assert cpu.execute_operation('int_neg', [BoxInt(45)], 'int').value == -45

class TestX86(object):
    def setup_class(cls):
        cls.cpu = CPU(rtyper=None, stats=FakeStats())

    def test_int_binary_ops(self):
        for op, args, res in [
            ('int_sub', [BoxInt(42), BoxInt(40)], 2),
            ('int_sub', [BoxInt(42), ConstInt(40)], 2),
            ('int_sub', [ConstInt(42), BoxInt(40)], 2),
            ('int_add', [ConstInt(-3), ConstInt(-5)], -8),
            ]:
            assert self.cpu.execute_operation(op, args, 'int').value == res

    def test_int_unary_ops(self):
        for op, args, res in [
            ('int_neg', [BoxInt(42)], -42),
            ('int_neg', [ConstInt(-42)], 42),
            ]:
            assert self.cpu.execute_operation(op, args, 'int').value == res

    def test_int_comp_ops(self):
        for op, args, res in [
            ('int_lt', [BoxInt(40), BoxInt(39)], 0),
            ('int_lt', [BoxInt(40), ConstInt(41)], 1),
            ('int_lt', [ConstInt(41), BoxInt(40)], 0),
            ('int_lt', [ConstInt(40), ConstInt(141)], 1),
            ('int_le', [ConstInt(42), BoxInt(42)], 1),
            ('int_gt', [BoxInt(40), ConstInt(-100)], 1),
            ]:
            assert self.cpu.execute_operation(op, args, 'int').value == res

    def test_execute_ptr_operation(self):
        cpu = self.cpu
        u = lltype.malloc(U)
        u_box = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, u))
        ofs_box = ConstInt(cpu.offsetof(S, 'value'))
        assert cpu.execute_operation('setfield_gc__4', [u_box, ofs_box, BoxInt(3)],
                                     'void') == None
        assert u.parent.parent.value == 3
        u.parent.parent.value += 100
        assert (cpu.execute_operation('getfield_gc__4', [u_box, ofs_box], 'int')
                .value == 103)

    def test_execute_operations_in_env(self):
        cpu = self.cpu
        cpu.set_meta_interp(FakeMetaInterp())
        x = BoxInt(123)
        y = BoxInt(456)
        z = BoxInt(579)
        t = BoxInt(455)
        u = BoxInt(0)    # False
        operations = [
            MergePoint('merge_point', [x, y], []),
            ResOperation('int_add', [x, y], [z]),
            ResOperation('int_sub', [y, ConstInt(1)], [t]),
            ResOperation('int_eq', [t, ConstInt(0)], [u]),
            MergePoint('merge_point', [t, u, z], []),
            ResOperation('guard_false', [u], []),
            Jump('jump', [z, t], []),
            ]
        startmp = operations[0]
        othermp = operations[-3]
        operations[-1].jump_target = startmp
        cpu.compile_operations(operations)
        res = cpu.execute_operations_in_new_frame('foo', startmp,
                                                  [BoxInt(0), BoxInt(10)],
                                                  'int')
        assert res.value == 42
        gf = cpu.metainterp.gf
        assert gf.merge_point is othermp
        assert cpu.metainterp.recordedvalues == [0, True, 55]
        assert gf.guard_op is operations[-2]

    def test_passing_guards(self):
        vtable_for_T = lltype.malloc(MY_VTABLE, immortal=True)
        cpu = self.cpu
        cpu._cache_gcstruct2vtable = {T: vtable_for_T}
        assert cpu.execute_operation('guard_true', [BoxInt(1)], 'void') == None
        assert cpu.execute_operation('guard_false', [BoxInt(0)], 'void') == None
        assert cpu.execute_operation('guard_value', [BoxInt(42), BoxInt(42)],
                                     'void') == None
        t = lltype.malloc(T)
        t.parent.typeptr = vtable_for_T
        t_box = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, t))
        T_box = ConstInt(rffi.cast(lltype.Signed, vtable_for_T))
        null_box = ConstPtr(lltype.cast_opaque_ptr(llmemory.GCREF, lltype.nullptr(T)))
        assert cpu.execute_operation('guard_class', [t_box, T_box], 'void') == None
        assert cpu.execute_operation('guard_nonnull', [t_box], 'void') == None
        assert cpu.execute_operation('guard_isnull', [null_box], 'void') == None

    def test_failing_guards(self):
        vtable_for_T = lltype.malloc(MY_VTABLE, immortal=True)
        vtable_for_U = lltype.malloc(MY_VTABLE, immortal=True)
        cpu = self.cpu
        cpu._cache_gcstruct2vtable = {T: vtable_for_T, U: vtable_for_U}
        cpu.set_meta_interp(FakeMetaInterp())
        t = lltype.malloc(T)
        t.parent.typeptr = vtable_for_T
        t_box = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, t))
        T_box = ConstInt(rffi.cast(lltype.Signed, vtable_for_T))
        u = lltype.malloc(U)
        u.parent.parent.typeptr = vtable_for_U
        u_box = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, u))
        U_box = ConstInt(rffi.cast(lltype.Signed, vtable_for_U))
        null_box = ConstPtr(lltype.cast_opaque_ptr(llmemory.GCREF, lltype.nullptr(T)))
        for opname, args in [('guard_true', [BoxInt(0)]),
                             ('guard_false', [BoxInt(1)]),
                             ('guard_value', [BoxInt(42), BoxInt(41)]),
                             ('guard_class', [t_box, U_box]),
                             ('guard_class', [u_box, T_box]),
                             ('guard_lt', [BoxInt(42), BoxInt(41)]),
                             ('guard_ge', [BoxInt(42), BoxInt(43)]),
                             ('guard_isnull', [u_box]),
                             ('guard_nonnull', [null_box]),
                             ]:
            cpu.metainterp.gf = None
            assert cpu.execute_operation(opname, args, 'void') == None
            assert cpu.metainterp.gf is not None

    def test_misc_int_ops(self):
        for op, args, res in [
            ('int_mod', [BoxInt(7), BoxInt(3)], 1),
            ('int_mod', [ConstInt(0), BoxInt(7)], 0),
            ('int_mod', [BoxInt(13), ConstInt(5)], 3),
            ('int_mod', [ConstInt(33), ConstInt(10)], 3),
            ('int_floordiv', [BoxInt(13), BoxInt(3)], 4),
            ('int_floordiv', [ConstInt(10), ConstInt(10)], 1),
            ('int_floordiv', [BoxInt(42), ConstInt(10)], 4),
            ('int_floordiv', [ConstInt(42), BoxInt(10)], 4),
            ('int_rshift', [ConstInt(3), BoxInt(4)], 3>>4),
            ('int_rshift', [BoxInt(3), ConstInt(10)], 3>>10),
            ]:
            assert self.cpu.execute_operation(op, args, 'int').value == res

    def test_same_as(self):
        u = lltype.malloc(U)
        uadr = lltype.cast_opaque_ptr(llmemory.GCREF, u)
        for op, args, tp, res in [
            ('same_as', [BoxInt(7)], 'int', 7),
            ('same_as', [ConstInt(7)], 'int', 7),
            ('same_as', [BoxPtr(uadr)], 'ptr', uadr),
            ('same_as', [ConstPtr(uadr)], 'ptr', uadr),
            ]:
            assert self.cpu.execute_operation(op, args, tp).value == res


