import py
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.jit.metainterp.history import ResOperation
from pypy.jit.metainterp.history import (BoxInt, BoxPtr, ConstInt, ConstPtr,
                                         Box)
from pypy.jit.backend.x86.runner import CPU, GuardFailed
from pypy.jit.backend.x86.regalloc import WORD
from pypy.jit.backend.x86 import symbolic
from pypy.jit.metainterp.resoperation import rop
import ctypes
import sys

class FakeStats(object):
    pass

class FakeMetaInterp(object):
    def handle_guard_failure(self, gf):
        assert isinstance(gf, GuardFailed)
        self.gf = gf
        self.recordedvalues = [
                gf.cpu.getvaluebox(gf.frame, gf.guard_op, i).value
                    for i in range(len(gf.guard_op.liveboxes))]
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

class TestX86(object):
    def setup_class(cls):
        cls.cpu = CPU(rtyper=None, stats=FakeStats())

    def execute_operation(self, opname, valueboxes, result_type):
        key = [opname, result_type]
        mp = self.get_compiled_single_operation(opname, result_type, valueboxes)
        boxes = [box for box in valueboxes if isinstance(box, Box)]
        res = self.cpu.execute_operations_in_new_frame(opname, mp, boxes,
                                                       result_type)
        return res

    def get_compiled_single_operation(self, opnum, result_type, valueboxes):
        livevarlist = []
        for box in valueboxes:
            if isinstance(box, Box):
                box = box.clonebox()
            livevarlist.append(box)
        mp = ResOperation(rop.MERGE_POINT,
                        [box for box in livevarlist if isinstance(box, Box)],
                        None)
        if result_type == 'void':
            result = None
        elif result_type == 'int':
            result = BoxInt()
        elif result_type == 'ptr':
            result = BoxPtr()
        else:
            raise ValueError(result_type)
        if result is None:
            results = []
        else:
            results = [result]
        operations = [mp,
                      ResOperation(opnum, livevarlist, result),
                      ResOperation(rop.RETURN, results, None)]
        if operations[1].is_guard():
            operations[1].liveboxes = []
        self.cpu.compile_operations(operations, verbose=False)
        return mp


    def test_int_binary_ops(self):
        for op, args, res in [
            (rop.INT_SUB, [BoxInt(42), BoxInt(40)], 2),
            (rop.INT_SUB, [BoxInt(42), ConstInt(40)], 2),
            (rop.INT_SUB, [ConstInt(42), BoxInt(40)], 2),
            (rop.INT_ADD, [ConstInt(-3), ConstInt(-5)], -8),
            ]:
            assert self.execute_operation(op, args, 'int').value == res

    def test_int_unary_ops(self):
        for op, args, res in [
            (rop.INT_NEG, [BoxInt(42)], -42),
            ]:
            assert self.execute_operation(op, args, 'int').value == res

    def test_int_comp_ops(self):
        for op, args, res in [
            (rop.INT_LT, [BoxInt(40), BoxInt(39)], 0),
            (rop.INT_LT, [BoxInt(40), ConstInt(41)], 1),
            (rop.INT_LT, [ConstInt(41), BoxInt(40)], 0),
            (rop.INT_LE, [ConstInt(42), BoxInt(42)], 1),
            (rop.INT_GT, [BoxInt(40), ConstInt(-100)], 1),
            ]:
            assert self.execute_operation(op, args, 'int').value == res

    def test_execute_ptr_operation(self):
        cpu = self.cpu
        u = lltype.malloc(U)
        u_box = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, u))
        ofs_box = ConstInt(cpu.fielddescrof(S, 'value'))
        assert self.execute_operation(rop.SETFIELD_GC,
                                      [u_box, ofs_box, BoxInt(3)],
                                     'void') == None
        assert u.parent.parent.value == 3
        u.parent.parent.value += 100
        assert (self.execute_operation(rop.GETFIELD_GC, [u_box, ofs_box], 'int')
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
            ResOperation(rop.MERGE_POINT, [x, y], None),
            ResOperation(rop.INT_ADD, [x, y], z),
            ResOperation(rop.INT_SUB, [y, ConstInt(1)], t),
            ResOperation(rop.INT_EQ, [t, ConstInt(0)], u),
            ResOperation(rop.GUARD_FALSE, [u], None),
            ResOperation(rop.JUMP, [z, t], None),
            ]
        startmp = operations[0]
        operations[-1].jump_target = startmp
        operations[-2].liveboxes = [t, u, z]
        cpu.compile_operations(operations)
        res = self.cpu.execute_operations_in_new_frame('foo', startmp,
                                                       [BoxInt(0), BoxInt(10)],
                                                       'int')
        assert res.value == 42
        gf = cpu.metainterp.gf
        assert cpu.metainterp.recordedvalues == [0, True, 55]
        assert gf.guard_op is operations[-2]

    def test_passing_guards(self):
        vtable_for_T = lltype.malloc(MY_VTABLE, immortal=True)
        cpu = self.cpu
        cpu._cache_gcstruct2vtable = {T: vtable_for_T}
        for (opname, args) in [(rop.GUARD_TRUE, [BoxInt(1)]),
                               (rop.GUARD_FALSE, [BoxInt(0)]),
                               (rop.GUARD_VALUE, [BoxInt(42), BoxInt(42)])]:
                assert self.execute_operation(opname, args, 'void') == None
        t = lltype.malloc(T)
        t.parent.typeptr = vtable_for_T
        t_box = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, t))
        T_box = ConstInt(rffi.cast(lltype.Signed, vtable_for_T))
        null_box = ConstPtr(lltype.cast_opaque_ptr(llmemory.GCREF, lltype.nullptr(T)))
        assert self.execute_operation(rop.GUARD_CLASS, [t_box, T_box], 'void') == None

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
        for opname, args in [(rop.GUARD_TRUE, [BoxInt(0)]),
                             (rop.GUARD_FALSE, [BoxInt(1)]),
                             (rop.GUARD_VALUE, [BoxInt(42), BoxInt(41)]),
                             (rop.GUARD_CLASS, [t_box, U_box]),
                             (rop.GUARD_CLASS, [u_box, T_box]),
                             ]:
            cpu.metainterp.gf = None
            assert self.execute_operation(opname, args, 'void') == None
            assert cpu.metainterp.gf is not None

    def test_misc_int_ops(self):
        for op, args, res in [
            (rop.INT_MOD, [BoxInt(7), BoxInt(3)], 1),
            (rop.INT_MOD, [ConstInt(0), BoxInt(7)], 0),
            (rop.INT_MOD, [BoxInt(13), ConstInt(5)], 3),
            (rop.INT_MOD, [ConstInt(33), ConstInt(10)], 3),
            (rop.INT_FLOORDIV, [BoxInt(13), BoxInt(3)], 4),
            (rop.INT_FLOORDIV, [BoxInt(42), ConstInt(10)], 4),
            (rop.INT_FLOORDIV, [ConstInt(42), BoxInt(10)], 4),
            (rop.INT_RSHIFT, [ConstInt(3), BoxInt(4)], 3>>4),
            (rop.INT_RSHIFT, [BoxInt(3), ConstInt(10)], 3>>10),
            ]:
            assert self.execute_operation(op, args, 'int').value == res

    def test_same_as(self):
        py.test.skip("I think no longer needed")
        u = lltype.malloc(U)
        uadr = lltype.cast_opaque_ptr(llmemory.GCREF, u)
        for op, args, tp, res in [
            ('same_as', [BoxInt(7)], 'int', 7),
            ('same_as', [ConstInt(7)], 'int', 7),
            ('same_as', [BoxPtr(uadr)], 'ptr', uadr),
            ('same_as', [ConstPtr(uadr)], 'ptr', uadr),
            ]:
            assert self.execute_operation(op, args, tp).value == res

    def test_allocations(self):
        from pypy.rpython.lltypesystem import rstr
        
        allocs = [None]
        all = []
        def f(size):
            allocs.insert(0, size)
            buf = ctypes.create_string_buffer(size)
            all.append(buf)
            return ctypes.cast(buf, ctypes.c_void_p).value
        func = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int)(f)
        addr = ctypes.cast(func, ctypes.c_void_p).value
        
        try:
            saved_addr = self.cpu.assembler.malloc_func_addr
            self.cpu.assembler.malloc_func_addr = addr
            ofs = symbolic.get_field_token(rstr.STR, 'chars')[0]
            
            res = self.execute_operation(rop.NEWSTR, [ConstInt(7)], 'ptr')
            assert allocs[0] == 7 + ofs + WORD
            resbuf = ctypes.cast(res.value.intval, ctypes.POINTER(ctypes.c_int))
            assert resbuf[ofs/WORD] == 7
            
            # ------------------------------------------------------------

            res = self.execute_operation(rop.NEWSTR, [BoxInt(7)], 'ptr')
            assert allocs[0] == 7 + ofs + WORD
            resbuf = ctypes.cast(res.value.intval, ctypes.POINTER(ctypes.c_int))
            assert resbuf[ofs/WORD] == 7

            # ------------------------------------------------------------

            TP = lltype.GcArray(lltype.Signed)
            ofs = symbolic.get_field_token(TP, 'length')[0]
            descr = ConstInt(self.cpu.arraydescrof(TP))

            res = self.execute_operation(rop.NEW_ARRAY, [descr, ConstInt(10)],
                                             'ptr')
            assert allocs[0] == 10*WORD + ofs + WORD
            resbuf = ctypes.cast(res.value.intval, ctypes.POINTER(ctypes.c_int))
            assert resbuf[ofs/WORD] == 10

            # ------------------------------------------------------------

            res = self.execute_operation(rop.NEW_ARRAY, [descr, BoxInt(10)],
                                             'ptr')
            assert allocs[0] == 10*WORD + ofs + WORD
            resbuf = ctypes.cast(res.value.intval, ctypes.POINTER(ctypes.c_int))
            assert resbuf[ofs/WORD] == 10
            
        finally:
            self.cpu.assembler.malloc_func_addr = saved_addr

    def test_stringitems(self):
        from pypy.rpython.lltypesystem.rstr import STR
        ofs = symbolic.get_field_token(STR, 'chars')[0]
        ofs_items = symbolic.get_field_token(STR.chars, 'items')[0]

        res = self.execute_operation(rop.NEWSTR, [ConstInt(10)], 'ptr')
        self.execute_operation(rop.STRSETITEM, [res, ConstInt(2), ConstInt(ord('d'))], 'void')
        resbuf = ctypes.cast(res.value.intval, ctypes.POINTER(ctypes.c_char))
        assert resbuf[ofs + ofs_items + 2] == 'd'
        self.execute_operation(rop.STRSETITEM, [res, BoxInt(2), ConstInt(ord('z'))], 'void')
        assert resbuf[ofs + ofs_items + 2] == 'z'
        r = self.execute_operation(rop.STRGETITEM, [res, BoxInt(2)], 'int')
        assert r.value == ord('z')

    def test_arrayitems(self):
        TP = lltype.GcArray(lltype.Signed)
        ofs = symbolic.get_field_token(TP, 'length')[0]
        itemsofs = symbolic.get_field_token(TP, 'items')[0]
        descr = ConstInt(self.cpu.arraydescrof(TP))
        res = self.execute_operation(rop.NEW_ARRAY, [descr, ConstInt(10)],
                                     'ptr')
        resbuf = ctypes.cast(res.value.intval, ctypes.POINTER(ctypes.c_int))
        assert resbuf[ofs/WORD] == 10
        self.execute_operation(rop.SETARRAYITEM_GC, [res, descr,
                                                     ConstInt(2), BoxInt(38)],
                               'void')
        assert resbuf[itemsofs/WORD + 2] == 38
        
        self.execute_operation(rop.SETARRAYITEM_GC, [res, descr,
                                                     BoxInt(3), BoxInt(42)],
                               'void')
        assert resbuf[itemsofs/WORD + 3] == 42

        r = self.execute_operation(rop.GETARRAYITEM_GC, [res, descr,
                                                         ConstInt(2)], 'int')
        assert r.value == 38
        r = self.execute_operation(rop.GETARRAYITEM_GC, [res, descr,
                                                         BoxInt(3)], 'int')
        assert r.value == 42

    def test_getfield_setfield(self):
        TP = lltype.GcStruct('x', ('s', lltype.Signed),
                             ('f', lltype.Float),
                             ('u', rffi.USHORT),
                             ('c1', lltype.Char),
                             ('c2', lltype.Char),
                             ('c3', lltype.Char))
        res = self.execute_operation(rop.NEW, [ConstInt(self.cpu.sizeof(TP))],
                                     'ptr')
        ofs_s = ConstInt(self.cpu.fielddescrof(TP, 's'))
        ofs_f = ConstInt(self.cpu.fielddescrof(TP, 'f'))
        ofs_u = ConstInt(self.cpu.fielddescrof(TP, 'u'))
        ofsc1 = ConstInt(self.cpu.fielddescrof(TP, 'c1'))
        ofsc2 = ConstInt(self.cpu.fielddescrof(TP, 'c2'))
        ofsc3 = ConstInt(self.cpu.fielddescrof(TP, 'c3'))
        self.execute_operation(rop.SETFIELD_GC, [res, ofs_s, ConstInt(3)], 'void')
        # XXX ConstFloat
        #self.execute_operation(rop.SETFIELD_GC, [res, ofs_f, 1e100], 'void')
        # XXX we don't support shorts (at all)
        #self.execute_operation(rop.SETFIELD_GC, [res, ofs_u, ConstInt(5)], 'void')
        s = self.execute_operation(rop.GETFIELD_GC, [res, ofs_s], 'int')
        assert s.value == 3
        self.execute_operation(rop.SETFIELD_GC, [res, ofs_s, BoxInt(3)], 'void')
        s = self.execute_operation(rop.GETFIELD_GC, [res, ofs_s], 'int')
        assert s.value == 3
        #u = self.execute_operation(rop.GETFIELD_GC, [res, ofs_u], 'int')
        #assert u.value == 5
        self.execute_operation(rop.SETFIELD_GC, [res, ofsc1, ConstInt(1)], 'void')
        self.execute_operation(rop.SETFIELD_GC, [res, ofsc2, ConstInt(2)], 'void')
        self.execute_operation(rop.SETFIELD_GC, [res, ofsc3, ConstInt(3)], 'void')
        c = self.execute_operation(rop.GETFIELD_GC, [res, ofsc1], 'int')
        assert c.value == 1
        c = self.execute_operation(rop.GETFIELD_GC, [res, ofsc2], 'int')
        assert c.value == 2
        c = self.execute_operation(rop.GETFIELD_GC, [res, ofsc3], 'int')
        assert c.value == 3
        
    def test_ovf_ops(self):
        py.test.skip("Cannot run like this, rewrite me")
        arg0 = BoxInt(12)
        arg1 = BoxInt(13)
        res = self.execute_operation(rop.INT_MUL_OVF, [arg0, arg1], 'int')
        assert res.value == 12*13
        arg0 = BoxInt(sys.maxint/2)
        arg1 = BoxInt(2222)
        self.execute_operation(rop.INT_MUL_OVF, [arg0, arg1], 'int')
        assert self.cpu.assembler._exception_data[0] == 1
        self.cpu.assembler._exception_data[0] = 0

    def test_uint_ops(self):
        from pypy.rlib.rarithmetic import r_uint, intmask

        arg0 = BoxInt(intmask(r_uint(sys.maxint + 3)))
        arg1 = BoxInt(intmask(r_uint(4)))
        res = self.execute_operation(rop.UINT_ADD, [arg0, arg1], 'int')
        assert res.value == intmask(r_uint(sys.maxint + 3) + r_uint(4))

        arg0 = BoxInt(intmask(sys.maxint + 10))
        arg1 = BoxInt(10)
        res = self.execute_operation(rop.UINT_MUL, [arg0, arg1], 'int')
        assert res.value == intmask((sys.maxint + 10) * 10)

        arg0 = BoxInt(intmask(r_uint(sys.maxint + 3)))
        arg1 = BoxInt(intmask(r_uint(4)))

        res = self.execute_operation(rop.UINT_GT, [arg0, arg1], 'int')
        assert res.value == 1
