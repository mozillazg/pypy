import py, sys, random, os, struct, operator
from pypy.jit.metainterp.history import (AbstractFailDescr,
                                         AbstractDescr,
                                         BasicFailDescr,
                                         JitCellToken, TargetToken)
from pypy.jit.metainterp.resoperation import rop, create_resop_dispatch,\
     create_resop, ConstInt, ConstPtr, ConstFloat, create_resop_2,\
     create_resop_1, create_resop_0, INT, REF, FLOAT, VOID, example_for_opnum,\
     AbstractResOp
from pypy.jit.metainterp.test.support import boxint, boxfloat,\
     boxlonglong_on_32bit, boxptr, constfloat
from pypy.jit.metainterp.typesystem import deref
from pypy.jit.codewriter.effectinfo import EffectInfo
from pypy.rpython.lltypesystem import lltype, llmemory, rstr, rffi, rclass
from pypy.rpython.annlowlevel import llhelper
from pypy.rpython.llinterp import LLException
from pypy.jit.codewriter import heaptracker, longlong
from pypy.rlib.rarithmetic import intmask, is_valid_int
from pypy.jit.backend.detect_cpu import autodetect_main_model_and_size
from pypy.jit.tool import oparser


class Runner(object):

    add_loop_instruction = ['overload for a specific cpu']
    bridge_loop_instruction = ['overload for a specific cpu']

    def execute_operation(self, opname, valueboxes, result_type, descr=None):
        inputargs, operations = self._get_single_operation_list(opname,
                                                                result_type,
                                                                valueboxes,
                                                                descr)
        oparser.assign_all_varindices(inputargs + operations)
        looptoken = JitCellToken()
        self.cpu.compile_loop(inputargs, operations, looptoken)
        args = []
        for box in inputargs:
            if box.type == INT:
                args.append(box.getint())
            elif box.type == REF:
                args.append(box.getref_base())
            elif box.type == FLOAT:
                args.append(box.getfloatstorage())
            else:
                raise NotImplementedError(box)
        frame = self.cpu.execute_token(looptoken, *args)
        descr = self.cpu.get_latest_descr(frame)
        if descr is operations[-1].getdescr():
            self.guard_failed = False
        else:
            self.guard_failed = True
        if result_type == 'int':
            return self.cpu.get_finish_value_int(frame)
        elif result_type == 'ref':
            return self.cpu.get_finish_value_ref(frame)
        elif result_type == 'float':
            x = self.cpu.get_finish_value_float(frame)
            return longlong.getrealfloat(x)
        elif result_type == 'longlong':
            assert longlong.supports_longlong
            return self.cpu.get_finish_value_float(frame)
        elif result_type == 'void':
            return None
        else:
            assert False

    def _get_single_operation_list(self, opnum, result_type, valueboxes,
                                   descr):
        if result_type == 'void':
            result = None
        elif result_type == 'int':
            result = 0
        elif result_type == 'ref':
            result = lltype.nullptr(llmemory.GCREF.TO)
        elif result_type == 'float' or result_type == 'longlong':
            result = 0.0
        else:
            raise ValueError(result_type)
        op0 = create_resop_dispatch(opnum, result, valueboxes,
                                    mutable=True)
        if result is None:
            results = []
        else:
            results = [op0]
        op1 = create_resop(rop.FINISH, None, results, descr=BasicFailDescr(0),
                           mutable=True)
        if op0.is_guard():
            if not descr:
                descr = BasicFailDescr(1)
        if descr is not None:
            op0.setdescr(descr)
        inputargs = [box for box in valueboxes if not box.is_constant()]
        return inputargs, [op0, op1]

class BaseBackendTest(Runner):

    avoid_instances = False

    def parse(self, s, namespace, invent_varindex=True):
        if namespace is None:
            namespace = {}
        else:
            namespace = namespace.copy()
        if 'targettoken' not in namespace:
            namespace['targettoken'] = TargetToken()
        if 'faildescr' not in namespace:
            namespace['faildescr'] = BasicFailDescr(1)
        if 'faildescr1' not in namespace:
            namespace['faildescr1'] = BasicFailDescr(1)
        if 'faildescr2' not in namespace:
            namespace['faildescr2'] = BasicFailDescr(2)
        if 'faildescr3' not in namespace:
            namespace['faildescr3'] = BasicFailDescr(3)
        if 'faildescr4' not in namespace:
            namespace['faildescr4'] = BasicFailDescr(4)
        loop = oparser.parse(s, namespace=namespace, mutable=True)
        return loop.inputargs, loop.operations, JitCellToken()

    def get_frame_value(self, frame, varname):
        index = int(varname[1:])
        if varname.startswith('i'):
            return self.cpu.get_frame_value_int(frame, index)
        if varname.startswith('p'):
            return self.cpu.get_frame_value_ref(frame, index)
        if varname.startswith('f'):
            return self.cpu.get_frame_value_float(frame, index)
        raise ValueError(varname)

    def test_compile_linear_loop(self):
        faildescr = BasicFailDescr(1)
        inputargs, ops, token = self.parse("""
        [i0]
        i1 = int_add(i0, 1)
        finish(i1, descr=faildescr)
        """, namespace=locals())
        self.cpu.compile_loop(inputargs, ops, token)
        frame = self.cpu.execute_token(token, 2)
        res = self.cpu.get_finish_value_int(frame)
        assert res == 3
        assert self.cpu.get_latest_descr(frame).identifier == 1

    def test_compile_linear_float_loop(self):
        faildescr = BasicFailDescr(1)
        inputargs, ops, token = self.parse("""
        [f0]
        f2 = float_add(f0, 1.)
        finish(f2, descr=faildescr)
        """, namespace=locals())
        self.cpu.compile_loop(inputargs, ops, token)
        frame = self.cpu.execute_token(token, longlong.getfloatstorage(2.8))
        res = self.cpu.get_finish_value_float(frame)
        assert longlong.getrealfloat(res) == 3.8
        assert self.cpu.get_latest_descr(frame).identifier == 1

    def test_compile_loop(self):
        faildescr = BasicFailDescr(2)
        targettoken = TargetToken()
        inputargs, operations, looptoken = self.parse('''
        [i0]
        label(i0, descr=targettoken)
        i1 = int_add(i0, 1)
        i2 = int_le(i1, 9)
        guard_true(i2, descr=faildescr)
        jump(i1, descr=targettoken)
        ''', namespace=locals())
        self.cpu.compile_loop(inputargs, operations, looptoken)
        frame = self.cpu.execute_token(looptoken, 2)
        assert self.cpu.get_latest_descr(frame).identifier == 2
        res = self.get_frame_value(frame, 'i1')
        assert res == 10

    def test_compile_loop_2(self):
        faildescr3 = BasicFailDescr(3)
        targettoken = TargetToken()
        inputargs, operations, looptoken = self.parse("""
        [i3]
        i0 = int_sub(i3, 42)
        label(i0, descr=targettoken)
        i1 = int_add(i0, 1)
        i2 = int_le(i1, 9)
        guard_true(i2, descr=faildescr3)
        jump(i1, descr=targettoken)
        """, namespace=locals())

        self.cpu.compile_loop(inputargs, operations, looptoken)
        frame = self.cpu.execute_token(looptoken, 44)
        assert self.cpu.get_latest_descr(frame).identifier == 3
        res = self.get_frame_value(frame, 'i1')
        assert res == 10

    def test_backends_dont_keep_loops_alive(self):
        import weakref, gc
        self.cpu.dont_keepalive_stuff = True
        inputargs, operations, looptoken = self.parse("""
        [i0]
        label(i0, descr=targettoken)
        i1 = int_add(i0, 1)
        i2 = int_le(i1, 9)
        guard_true(i2, descr=faildescr)
        jump(i1, descr=targettoken)
        """, namespace={'targettoken': TargetToken()})
        i1 = inputargs[0]
        wr_i1 = weakref.ref(i1)
        wr_guard = weakref.ref(operations[2])
        self.cpu.compile_loop(inputargs, operations, looptoken)
        if hasattr(looptoken, '_x86_ops_offset'):
            del looptoken._x86_ops_offset # else it's kept alive
        del i1
        del inputargs
        del operations
        gc.collect()
        assert not wr_i1() and not wr_guard()

    def test_compile_bridge(self):
        self.cpu.total_compiled_loops = 0
        self.cpu.total_compiled_bridges = 0
        faildescr4 = BasicFailDescr(4)
        targettoken =  TargetToken()
        inputargs, operations, looptoken = self.parse("""
        [i0]
        label(i0, descr=targettoken)
        i1 = int_add(i0, 1)
        i2 = int_le(i1, 9)
        guard_true(i2, descr=faildescr)
        jump(i1, descr=targettoken)
        """, namespace={'faildescr': faildescr4,
                        'targettoken': targettoken})
        self.cpu.compile_loop(inputargs, operations, looptoken)

        inputargs, bridge_ops, _ = self.parse("""
        [i1]
        i3 = int_le(i1, 19)
        guard_true(i3, descr=faildescr5)
        jump(i1, descr=targettoken)
        """, namespace={'faildescr5': BasicFailDescr(5),
                        'targettoken': targettoken})
        self.cpu.compile_bridge(faildescr4,
                                inputargs, bridge_ops, looptoken)

        frame = self.cpu.execute_token(looptoken, 2)
        assert self.cpu.get_latest_descr(frame).identifier == 5
        res = self.get_frame_value(frame, 'i1')
        assert res == 20

        assert self.cpu.total_compiled_loops == 1
        assert self.cpu.total_compiled_bridges == 1
        return looptoken

    def test_compile_big_bridge_out_of_small_loop(self):
        faildescr1 = BasicFailDescr(1)
        faildescr2 = BasicFailDescr(2)
        inputargs, operations, looptoken = self.parse("""
        [i0]
        guard_false(i0, descr=faildescr1)
        finish(descr=faildescr3)
        """, namespace=locals())
        self.cpu.compile_loop(inputargs, operations, looptoken)

        bridge_source = ["[i0]"]
        for i in range(1000):
            bridge_source.append("i%d = int_add(i%d, 1)" % (i + 1, i))
        bridge_source.append("guard_false(i0, descr=faildescr2)")
        bridge_source.append("finish(descr=faildescr4)")
        inputargs, bridge, _ = self.parse("\n".join(bridge_source),
                                          namespace=locals())
        self.cpu.compile_bridge(faildescr1, inputargs, bridge, looptoken)

        frame = self.cpu.execute_token(looptoken, 1)
        assert self.cpu.get_latest_descr(frame).identifier == 2
        for i in range(1001):
            res = self.get_frame_value(frame, 'i%d' % i)
            assert res == i or 1

    def test_finish(self):
        class UntouchableFailDescr(AbstractFailDescr):
            def __setattr__(self, name, value):
                if name == 'index':
                    return AbstractFailDescr.__setattr__(self, name, value)
                py.test.fail("finish descrs should not be touched")
        faildescr = UntouchableFailDescr() # to check that is not touched
        namespace = {'faildescr': faildescr}
        inputargs, operations, looptoken = self.parse("""
        [i0]
        finish(i0, descr=faildescr)
        """, namespace=namespace)
        self.cpu.compile_loop(inputargs, operations, looptoken)
        frame = self.cpu.execute_token(looptoken, 99)
        assert self.cpu.get_latest_descr(frame) is faildescr
        res = self.cpu.get_finish_value_int(frame)
        assert res == 99

        inputargs, operations, looptoken = self.parse("""
        []
        finish(42, descr=faildescr)
        """, namespace=namespace)
        self.cpu.compile_loop(inputargs, operations, looptoken)
        frame = self.cpu.execute_token(looptoken)
        assert self.cpu.get_latest_descr(frame) is faildescr
        res = self.cpu.get_finish_value_int(frame)
        assert res == 42

        _, operations, looptoken = self.parse("""
        []
        finish(descr=faildescr)
        """, namespace=namespace)
        self.cpu.compile_loop([], operations, looptoken)
        frame = self.cpu.execute_token(looptoken)
        assert self.cpu.get_latest_descr(frame) is faildescr

        if self.cpu.supports_floats:
            inputargs, operations, looptoken = self.parse("""
            [f0]
            finish(f0, descr=faildescr)
            """, namespace)
            self.cpu.compile_loop(inputargs, operations, looptoken)
            value = longlong.getfloatstorage(-61.25)
            frame = self.cpu.execute_token(looptoken, value)
            assert self.cpu.get_latest_descr(frame) is faildescr
            res = self.cpu.get_finish_value_float(frame)
            assert longlong.getrealfloat(res) == -61.25

            _, operations, looptoken = self.parse("""
            []
            finish(42.5, descr=faildescr)
            """, namespace)
            self.cpu.compile_loop([], operations, looptoken)
            frame = self.cpu.execute_token(looptoken)
            assert self.cpu.get_latest_descr(frame) is faildescr
            res = self.cpu.get_finish_value_float(frame)
            assert longlong.getrealfloat(res) == 42.5

    def test_execute_operations_in_env(self):
        cpu = self.cpu
        inputargs, operations, looptoken = self.parse("""
        [i0, i2]
        label(i2, i0, descr=targettoken)
        i5 = int_add(i0, i2)
        i1 = int_sub(i2, 1)
        i4 = int_eq(i1, 0)
        guard_false(i4, descr=faildescr)
        jump(i1, i5, descr=targettoken)
        """, None)
        cpu.compile_loop(inputargs, operations, looptoken)
        frame = self.cpu.execute_token(looptoken, 0, 10)
        assert self.get_frame_value(frame, 'i1') == 0
        assert self.get_frame_value(frame, 'i5') == 55

    def test_int_operations(self):
        from pypy.jit.metainterp.test.test_executor import get_int_tests
        for opnum, boxargs, retvalue in get_int_tests():
            res = self.execute_operation(opnum, boxargs, 'int')
            assert res == retvalue

    def test_float_operations(self):
        from pypy.jit.metainterp.test.test_executor import get_float_tests
        for opnum, boxargs, rettype, retvalue in get_float_tests(self.cpu):
            res = self.execute_operation(opnum, boxargs, rettype)
            assert res == retvalue

    def test_ovf_operations(self, reversed=False):
        minint = -sys.maxint-1
        boom = 'boom'
        for op, testcases in [
            ('int_add_ovf', [(10, -2, 8),
                               (-1, minint, boom),
                               (sys.maxint//2, sys.maxint//2+2, boom)]),
            ('int_sub_ovf', [(-20, -23, 3),
                               (-2, sys.maxint, boom),
                               (sys.maxint//2, -(sys.maxint//2+2), boom)]),
            ('int_mul_ovf', [(minint/2, 2, minint),
                               (-2, -(minint/2), minint),
                               (minint/2, -2, boom)]),
            ]:
            if not reversed:
                inputargs, operations, looptoken = self.parse("""
                [i1, i2]
                i3 = %s(i1, i2)
                guard_no_overflow(descr=faildescr1)
                finish(i3, descr=faildescr2)
                """ % op, namespace={'faildescr1': BasicFailDescr(1),
                                     'faildescr2': BasicFailDescr(2)})
            else:
                inputargs, operations, looptoken = self.parse("""
                [i1, i2]
                i3 = %s(i1, i2)
                guard_overflow(descr=faildescr1)
                finish(descr=faildescr2)
                """ % op, namespace={'faildescr1': BasicFailDescr(1),
                                     'faildescr2': BasicFailDescr(2)})
            #
            self.cpu.compile_loop(inputargs, operations, looptoken)
            for x, y, z in testcases:
                frame = self.cpu.execute_token(looptoken, x, y)
                if (z == boom) ^ reversed:
                    assert self.cpu.get_latest_descr(frame).identifier == 1
                else:
                    assert self.cpu.get_latest_descr(frame).identifier == 2
                if z != boom:
                    if not reversed:
                        assert self.cpu.get_finish_value_int(frame) == z
                    else:
                        assert self.get_frame_value(frame, 'i3') == z

    def test_ovf_operations_reversed(self):
        self.test_ovf_operations(reversed=True)

    def test_bh_call(self):
        cpu = self.cpu
        #
        def func(c):
            return chr(ord(c) + 1)
        FPTR = self.Ptr(self.FuncType([lltype.Char], lltype.Char))
        func_ptr = llhelper(FPTR, func)
        calldescr = cpu.calldescrof(deref(FPTR), (lltype.Char,), lltype.Char,
                                    EffectInfo.MOST_GENERAL)
        x = cpu.bh_call_i(self.get_funcbox(cpu, func_ptr).value,
                          [ord('A')], None, None, calldescr)
        assert x == ord('B')
        if cpu.supports_floats:
            def func(f, i):
                assert isinstance(f, float)
                assert is_valid_int(i)
                return f - float(i)
            FPTR = self.Ptr(self.FuncType([lltype.Float, lltype.Signed],
                                          lltype.Float))
            func_ptr = llhelper(FPTR, func)
            FTP = deref(FPTR)
            calldescr = cpu.calldescrof(FTP, FTP.ARGS, FTP.RESULT,
                                        EffectInfo.MOST_GENERAL)
            x = cpu.bh_call_f(self.get_funcbox(cpu, func_ptr).value,
                              [42], None, [longlong.getfloatstorage(3.5)],
                              calldescr)
            assert longlong.getrealfloat(x) == 3.5 - 42

    def test_call(self):
        from pypy.rlib.jit_libffi import types

        def func_int(a, b):
            return a + b
        def func_char(c, c1):
            return chr(ord(c) + ord(c1))

        functions = [
            (func_int, lltype.Signed, types.sint, 655360),
            (func_int, rffi.SHORT, types.sint16, 1213),
            (func_char, lltype.Char, types.uchar, 12)
            ]

        cpu = self.cpu
        for func, TP, ffi_type, num in functions:
            #
            FPTR = self.Ptr(self.FuncType([TP, TP], TP))
            func_ptr = llhelper(FPTR, func)
            FUNC = deref(FPTR)
            funcbox = self.get_funcbox(cpu, func_ptr)
            # first, try it with the "normal" calldescr
            calldescr = cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT,
                                        EffectInfo.MOST_GENERAL)
            res = self.execute_operation(rop.CALL_i,
                                         [funcbox, boxint(num), boxint(num)],
                                         'int', descr=calldescr)
            assert res == 2 * num
            # then, try it with the dynamic calldescr
            dyn_calldescr = cpu._calldescr_dynamic_for_tests(
                [ffi_type, ffi_type], ffi_type)
            res = self.execute_operation(rop.CALL_i,
                                         [funcbox, boxint(num), boxint(num)],
                                         'int', descr=dyn_calldescr)
            assert res == 2 * num

            # last, try it with one constant argument
            calldescr = cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT, EffectInfo.MOST_GENERAL)
            res = self.execute_operation(rop.CALL_i,
                                         [funcbox, ConstInt(num), boxint(num)],
                                         'int', descr=calldescr)
            assert res == 2 * num
            

        if cpu.supports_floats:
            def func(f0, f1, f2, f3, f4, f5, f6, i0, f7, i1, f8, f9):
                return f0 + f1 + f2 + f3 + f4 + f5 + f6 + float(i0 + i1) + f7 + f8 + f9
            F = lltype.Float
            I = lltype.Signed
            FUNC = self.FuncType([F] * 7 + [I] + [F] + [I] + [F]* 2, F)
            FPTR = self.Ptr(FUNC)
            func_ptr = llhelper(FPTR, func)
            calldescr = cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT,
                                        EffectInfo.MOST_GENERAL)
            funcbox = self.get_funcbox(cpu, func_ptr)
            args = ([boxfloat(.1) for i in range(7)] +
                    [boxint(1), boxfloat(.2), boxint(2), boxfloat(.3),
                     boxfloat(.4)])
            res = self.execute_operation(rop.CALL_f,
                                         [funcbox] + args,
                                         'float', descr=calldescr)
            assert abs(res - 4.6) < 0.0001

    def test_call_many_arguments(self):
        # Test calling a function with a large number of arguments (more than
        # 6, which will force passing some arguments on the stack on 64-bit)

        def func(*args):
            assert len(args) == 16
            # Try to sum up args in a way that would probably detect a
            # transposed argument
            return sum(arg * (2**i) for i, arg in enumerate(args))

        FUNC = self.FuncType([lltype.Signed]*16, lltype.Signed)
        FPTR = self.Ptr(FUNC)
        calldescr = self.cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT,
                                         EffectInfo.MOST_GENERAL)
        func_ptr = llhelper(FPTR, func)
        args = range(16)
        funcbox = self.get_funcbox(self.cpu, func_ptr)
        res = self.execute_operation(rop.CALL_i, [funcbox] + map(boxint, args), 'int', descr=calldescr)
        assert res == func(*args)

    def test_call_box_func(self):
        def a(a1, a2):
            return a1 + a2
        def b(b1, b2):
            return b1 * b2

        arg1 = 40
        arg2 = 2
        for f in [a, b]:
            TP = lltype.Signed
            FPTR = self.Ptr(self.FuncType([TP, TP], TP))
            func_ptr = llhelper(FPTR, f)
            FUNC = deref(FPTR)
            funcbox = create_resop_0(rop.INPUT_i,
                                     rffi.cast(lltype.Signed, func_ptr))
            calldescr = self.cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT,
                                        EffectInfo.MOST_GENERAL)
            res = self.execute_operation(rop.CALL_i,
                                         [funcbox, boxint(arg1), boxint(arg2)],
                                         'int', descr=calldescr)
            assert res == f(arg1, arg2)

    def test_call_stack_alignment(self):
        # test stack alignment issues, notably for Mac OS/X.
        # also test the ordering of the arguments.

        def func_ints(*ints):
            s = str(ints) + '\n'
            os.write(1, s)   # don't remove -- crash if the stack is misaligned
            return sum([(10+i)*(5+j) for i, j in enumerate(ints)])

        for nb_args in range(0, 35):
            cpu = self.cpu
            TP = lltype.Signed
            #
            FPTR = self.Ptr(self.FuncType([TP] * nb_args, TP))
            func_ptr = llhelper(FPTR, func_ints)
            FUNC = deref(FPTR)
            calldescr = cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT,
                                        EffectInfo.MOST_GENERAL)
            funcbox = self.get_funcbox(cpu, func_ptr)
            args = [280-24*i for i in range(nb_args)]
            res = self.execute_operation(rop.CALL_i,
                                         [funcbox] + map(boxint, args),
                                         'int', descr=calldescr)
            assert res == func_ints(*args)

    def test_call_with_const_floats(self):
        if not self.cpu.supports_floats:
            py.test.skip("requires floats")
        def func(f1, f2):
            return f1 + f2

        FUNC = self.FuncType([lltype.Float, lltype.Float], lltype.Float)
        FPTR = self.Ptr(FUNC)
        calldescr = self.cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT,
                                         EffectInfo.MOST_GENERAL)
        func_ptr = llhelper(FPTR, func)
        funcbox = self.get_funcbox(self.cpu, func_ptr)
        res = self.execute_operation(rop.CALL_f, [funcbox, constfloat(1.5),
                                                constfloat(2.5)], 'float',
                                     descr=calldescr)
        assert res == 4.0


    def test_field_basic(self):
        t_box, T_box = self.alloc_instance(self.T)
        fielddescr = self.cpu.fielddescrof(self.S, 'value')
        assert not fielddescr.is_pointer_field()
        #
        res = self.execute_operation(rop.SETFIELD_GC, [t_box, boxint(39082)],
                                     'void', descr=fielddescr)
        assert res is None
        res = self.execute_operation(rop.GETFIELD_GC_i, [t_box],
                                     'int', descr=fielddescr)
        assert res == 39082
        #
        fielddescr1 = self.cpu.fielddescrof(self.S, 'chr1')
        fielddescr2 = self.cpu.fielddescrof(self.S, 'chr2')
        shortdescr = self.cpu.fielddescrof(self.S, 'short')
        self.execute_operation(rop.SETFIELD_GC, [t_box, boxint(250)],
                               'void', descr=fielddescr2)
        self.execute_operation(rop.SETFIELD_GC, [t_box, boxint(133)],
                               'void', descr=fielddescr1)
        self.execute_operation(rop.SETFIELD_GC, [t_box, boxint(1331)],
                               'void', descr=shortdescr)
        res = self.execute_operation(rop.GETFIELD_GC_i, [t_box],
                                     'int', descr=fielddescr2)
        assert res == 250
        res = self.execute_operation(rop.GETFIELD_GC_i, [t_box],
                                     'int', descr=fielddescr1)
        assert res == 133
        res = self.execute_operation(rop.GETFIELD_GC_i, [t_box],
                                     'int', descr=shortdescr)
        assert res == 1331

        #
        u_box, U_box = self.alloc_instance(self.U)
        fielddescr2 = self.cpu.fielddescrof(self.S, 'next')
        assert fielddescr2.is_pointer_field()
        res = self.execute_operation(rop.SETFIELD_GC, [t_box, u_box],
                                     'void', descr=fielddescr2)
        assert res is None
        res = self.execute_operation(rop.GETFIELD_GC_r, [t_box],
                                     'ref', descr=fielddescr2)
        assert res == u_box.getref_base()
        #
        null_const = self.null_instance().constbox()
        res = self.execute_operation(rop.SETFIELD_GC, [t_box, null_const],
                                     'void', descr=fielddescr2)
        assert res is None
        res = self.execute_operation(rop.GETFIELD_GC_r, [t_box],
                                     'ref', descr=fielddescr2)
        assert res == null_const.value
        if self.cpu.supports_floats:
            floatdescr = self.cpu.fielddescrof(self.S, 'float')
            self.execute_operation(rop.SETFIELD_GC, [t_box, boxfloat(3.4)],
                                   'void', descr=floatdescr)
            res = self.execute_operation(rop.GETFIELD_GC_f, [t_box],
                                         'float', descr=floatdescr)
            assert res == 3.4
            #
            self.execute_operation(rop.SETFIELD_GC, [t_box, constfloat(-3.6)],
                                   'void', descr=floatdescr)
            res = self.execute_operation(rop.GETFIELD_GC_f, [t_box],
                                         'float', descr=floatdescr)
            assert res == -3.6


    def test_passing_guards(self):
        t_box, T_box = self.alloc_instance(self.T)
        nullbox = self.null_instance()
        all = [(rop.GUARD_TRUE, [boxint(1)]),
               (rop.GUARD_FALSE, [boxint(0)]),
               (rop.GUARD_VALUE, [boxint(42), ConstInt(42)]),
               ]
        if not self.avoid_instances:
            all.extend([
               (rop.GUARD_NONNULL, [t_box]),
               (rop.GUARD_ISNULL, [nullbox])
               ])
        if self.cpu.supports_floats:
            all.append((rop.GUARD_VALUE, [boxfloat(3.5), constfloat(3.5)]))
        for (opname, args) in all:
            assert self.execute_operation(opname, args, 'void') == None
            assert not self.guard_failed


    def test_passing_guard_class(self):
        t_box, T_box = self.alloc_instance(self.T)
        #null_box = ConstPtr(lltype.cast_opaque_ptr(llmemory.GCREF, lltype.nullptr(T)))
        self.execute_operation(rop.GUARD_CLASS, [t_box, T_box], 'void')
        assert not self.guard_failed
        self.execute_operation(rop.GUARD_NONNULL_CLASS, [t_box, T_box], 'void')
        assert not self.guard_failed

    def test_failing_guards(self):
        t_box, T_box = self.alloc_instance(self.T)
        nullbox = self.null_instance()
        all = [(rop.GUARD_TRUE, [boxint(0)]),
               (rop.GUARD_FALSE, [boxint(1)]),
               (rop.GUARD_VALUE, [boxint(42), ConstInt(41)]),
               ]
        if not self.avoid_instances:
            all.extend([
               (rop.GUARD_NONNULL, [nullbox]),
               (rop.GUARD_ISNULL, [t_box])])
        if self.cpu.supports_floats:
            all.append((rop.GUARD_VALUE, [boxfloat(-1.0), constfloat(1.0)]))
        for opname, args in all:
            assert self.execute_operation(opname, args, 'void') == None
            assert self.guard_failed

    def test_failing_guard_class(self):
        t_box, T_box = self.alloc_instance(self.T)
        u_box, U_box = self.alloc_instance(self.U)
        null_box = self.null_instance()
        for opname, args in [(rop.GUARD_CLASS, [t_box, U_box]),
                             (rop.GUARD_CLASS, [u_box, T_box]),
                             (rop.GUARD_NONNULL_CLASS, [t_box, U_box]),
                             (rop.GUARD_NONNULL_CLASS, [u_box, T_box]),
                             (rop.GUARD_NONNULL_CLASS, [null_box, T_box]),
                             ]:
            assert self.execute_operation(opname, args, 'void') == None
            assert self.guard_failed

    def test_ooops(self):
        def clone(box):
            return boxptr(box.getref_base())
        
        u1_box, U_box = self.alloc_instance(self.U)
        u2_box, U_box = self.alloc_instance(self.U)
        r = self.execute_operation(rop.PTR_EQ, [u1_box,
                                                clone(u1_box)], 'int')
        assert r == 1
        r = self.execute_operation(rop.PTR_NE, [u2_box,
                                                clone(u2_box)], 'int')
        assert r == 0
        r = self.execute_operation(rop.PTR_EQ, [u1_box, u2_box], 'int')
        assert r == 0
        r = self.execute_operation(rop.PTR_NE, [u2_box, u1_box], 'int')
        assert r == 1
        #
        null_box = self.null_instance()
        r = self.execute_operation(rop.PTR_EQ, [null_box,
                                                clone(null_box)], 'int')
        assert r == 1
        r = self.execute_operation(rop.PTR_EQ, [u1_box, null_box], 'int')
        assert r == 0
        r = self.execute_operation(rop.PTR_EQ, [null_box, u2_box], 'int')
        assert r == 0
        r = self.execute_operation(rop.PTR_NE, [null_box,
                                                clone(null_box)], 'int')
        assert r == 0
        r = self.execute_operation(rop.PTR_NE, [u2_box, null_box], 'int')
        assert r == 1
        r = self.execute_operation(rop.PTR_NE, [null_box, u1_box], 'int')
        assert r == 1

        # These operations are supposed to be the same as PTR_EQ/PTR_NE
        # just checking that the operations are defined in the backend.
        r = self.execute_operation(rop.INSTANCE_PTR_EQ, [u1_box, u2_box], 'int')
        assert r == 0
        r = self.execute_operation(rop.INSTANCE_PTR_NE, [u2_box, u1_box], 'int')
        assert r == 1

    def test_array_basic(self):
        a_box, A = self.alloc_array_of(rffi.SHORT, 342)
        arraydescr = self.cpu.arraydescrof(A)
        assert not arraydescr.is_array_of_pointers()
        #
        r = self.execute_operation(rop.ARRAYLEN_GC, [a_box],
                                   'int', descr=arraydescr)
        assert r == 342
        r = self.execute_operation(rop.SETARRAYITEM_GC, [a_box, boxint(310),
                                                         boxint(744)],
                                   'void', descr=arraydescr)
        assert r is None
        r = self.execute_operation(rop.GETARRAYITEM_GC_i, [a_box, boxint(310)],
                                   'int', descr=arraydescr)
        assert r == 744

        a_box, A = self.alloc_array_of(lltype.Signed, 342)
        arraydescr = self.cpu.arraydescrof(A)
        assert not arraydescr.is_array_of_pointers()
        #
        r = self.execute_operation(rop.ARRAYLEN_GC, [a_box],
                                   'int', descr=arraydescr)
        assert r == 342
        r = self.execute_operation(rop.SETARRAYITEM_GC, [a_box, boxint(310),
                                                         boxint(7441)],
                                   'void', descr=arraydescr)
        assert r is None
        r = self.execute_operation(rop.GETARRAYITEM_GC_i, [a_box, boxint(310)],
                                   'int', descr=arraydescr)
        assert r == 7441
        #
        a_box, A = self.alloc_array_of(lltype.Char, 11)
        arraydescr = self.cpu.arraydescrof(A)
        assert not arraydescr.is_array_of_pointers()
        r = self.execute_operation(rop.ARRAYLEN_GC, [a_box],
                                   'int', descr=arraydescr)
        assert r == 11
        r = self.execute_operation(rop.SETARRAYITEM_GC, [a_box, boxint(4),
                                                         boxint(150)],
                                   'void', descr=arraydescr)
        assert r is None
        r = self.execute_operation(rop.SETARRAYITEM_GC, [a_box, boxint(3),
                                                         boxint(160)],
                                   'void', descr=arraydescr)
        assert r is None
        r = self.execute_operation(rop.GETARRAYITEM_GC_i, [a_box, boxint(4)],
                                   'int', descr=arraydescr)
        assert r == 150
        r = self.execute_operation(rop.GETARRAYITEM_GC_i, [a_box, boxint(3)],
                                   'int', descr=arraydescr)
        assert r == 160

        #
        if isinstance(A, lltype.GcArray):
            A = lltype.Ptr(A)
        b_box, B = self.alloc_array_of(A, 3)
        arraydescr = self.cpu.arraydescrof(B)
        assert arraydescr.is_array_of_pointers()
        r = self.execute_operation(rop.ARRAYLEN_GC, [b_box],
                                   'int', descr=arraydescr)
        assert r == 3
        r = self.execute_operation(rop.SETARRAYITEM_GC, [b_box, boxint(1),
                                                         a_box],
                                   'void', descr=arraydescr)
        assert r is None
        r = self.execute_operation(rop.GETARRAYITEM_GC_r, [b_box, boxint(1)],
                                   'ref', descr=arraydescr)
        assert r == a_box.getref_base()
        #
        # Unsigned should work the same as Signed
        a_box, A = self.alloc_array_of(lltype.Unsigned, 342)
        arraydescr = self.cpu.arraydescrof(A)
        assert not arraydescr.is_array_of_pointers()
        r = self.execute_operation(rop.ARRAYLEN_GC, [a_box],
                                   'int', descr=arraydescr)
        assert r == 342
        r = self.execute_operation(rop.SETARRAYITEM_GC, [a_box, boxint(310),
                                                         boxint(7441)],
                                   'void', descr=arraydescr)
        assert r is None
        r = self.execute_operation(rop.GETARRAYITEM_GC_i, [a_box, boxint(310)],
                                   'int', descr=arraydescr)
        assert r == 7441
        #
        # Bool should work the same as Char
        a_box, A = self.alloc_array_of(lltype.Bool, 311)
        arraydescr = self.cpu.arraydescrof(A)
        assert not arraydescr.is_array_of_pointers()
        r = self.execute_operation(rop.ARRAYLEN_GC, [a_box],
                                   'int', descr=arraydescr)
        assert r == 311
        r = self.execute_operation(rop.SETARRAYITEM_GC, [a_box, boxint(304),
                                                         boxint(1)],
                                   'void', descr=arraydescr)
        assert r is None
        r = self.execute_operation(rop.SETARRAYITEM_GC, [a_box, boxint(303),
                                                         boxint(0)],
                                   'void', descr=arraydescr)
        assert r is None
        r = self.execute_operation(rop.SETARRAYITEM_GC, [a_box, boxint(302),
                                                         boxint(1)],
                                   'void', descr=arraydescr)
        assert r is None
        r = self.execute_operation(rop.GETARRAYITEM_GC_i, [a_box, boxint(304)],
                                   'int', descr=arraydescr)
        assert r == 1
        r = self.execute_operation(rop.GETARRAYITEM_GC_i, [a_box, boxint(303)],
                                   'int', descr=arraydescr)
        assert r == 0
        r = self.execute_operation(rop.GETARRAYITEM_GC_i, [a_box, boxint(302)],
                                   'int', descr=arraydescr)
        assert r == 1

        if self.cpu.supports_floats:
            a_box, A = self.alloc_array_of(lltype.Float, 31)
            arraydescr = self.cpu.arraydescrof(A)
            self.execute_operation(rop.SETARRAYITEM_GC, [a_box, boxint(1),
                                                         boxfloat(3.5)],
                                   'void', descr=arraydescr)
            self.execute_operation(rop.SETARRAYITEM_GC, [a_box, boxint(2),
                                                         constfloat(4.5)],
                                   'void', descr=arraydescr)
            r = self.execute_operation(rop.GETARRAYITEM_GC_f, [a_box, boxint(1)],
                                       'float', descr=arraydescr)
            assert r == 3.5
            r = self.execute_operation(rop.GETARRAYITEM_GC_f, [a_box, boxint(2)],
                                       'float', descr=arraydescr)
            assert r == 4.5

        # For platforms where sizeof(INT) != sizeof(Signed) (ie, x86-64)
        a_box, A = self.alloc_array_of(rffi.INT, 342)
        arraydescr = self.cpu.arraydescrof(A)
        assert not arraydescr.is_array_of_pointers()
        r = self.execute_operation(rop.ARRAYLEN_GC, [a_box],
                                   'int', descr=arraydescr)
        assert r == 342
        r = self.execute_operation(rop.SETARRAYITEM_GC, [a_box, boxint(310),
                                                         boxint(7441)],
                                   'void', descr=arraydescr)
        assert r is None
        r = self.execute_operation(rop.GETARRAYITEM_GC_i, [a_box, boxint(310)],
                                   'int', descr=arraydescr)
        assert r == 7441

    def test_array_of_structs(self):
        TP = lltype.GcStruct('x')
        ITEM = lltype.Struct('x',
                             ('vs', lltype.Signed),
                             ('vu', lltype.Unsigned),
                             ('vsc', rffi.SIGNEDCHAR),
                             ('vuc', rffi.UCHAR),
                             ('vss', rffi.SHORT),
                             ('vus', rffi.USHORT),
                             ('vsi', rffi.INT),
                             ('vui', rffi.UINT),
                             ('k', lltype.Float),
                             ('p', lltype.Ptr(TP)))
        a_box, A = self.alloc_array_of(ITEM, 15)
        s_box, S = self.alloc_instance(TP)
        vsdescr = self.cpu.interiorfielddescrof(A, 'vs')
        kdescr = self.cpu.interiorfielddescrof(A, 'k')
        pdescr = self.cpu.interiorfielddescrof(A, 'p')
        self.execute_operation(rop.SETINTERIORFIELD_GC, [a_box, boxint(3),
                                                         boxfloat(1.5)],
                               'void', descr=kdescr)
        f = self.cpu.bh_getinteriorfield_gc_f(a_box.getref_base(), 3, kdescr)
        assert longlong.getrealfloat(f) == 1.5
        self.cpu.bh_setinteriorfield_gc_f(a_box.getref_base(), 3, longlong.getfloatstorage(2.5), kdescr)
        r = self.execute_operation(rop.GETINTERIORFIELD_GC_f,
                                   [a_box, boxint(3)], 'float', descr=kdescr)
        assert r == 2.5
        #
        NUMBER_FIELDS = [('vs', lltype.Signed),
                         ('vu', lltype.Unsigned),
                         ('vsc', rffi.SIGNEDCHAR),
                         ('vuc', rffi.UCHAR),
                         ('vss', rffi.SHORT),
                         ('vus', rffi.USHORT),
                         ('vsi', rffi.INT),
                         ('vui', rffi.UINT)]
        for name, TYPE in NUMBER_FIELDS[::-1]:
            vdescr = self.cpu.interiorfielddescrof(A, name)
            self.execute_operation(rop.SETINTERIORFIELD_GC, [a_box, boxint(3),
                                                             boxint(-15)],
                                   'void', descr=vdescr)
        for name, TYPE in NUMBER_FIELDS:
            vdescr = self.cpu.interiorfielddescrof(A, name)
            i = self.cpu.bh_getinteriorfield_gc_i(a_box.getref_base(), 3,
                                                  vdescr)
            assert i == rffi.cast(lltype.Signed, rffi.cast(TYPE, -15))
        for name, TYPE in NUMBER_FIELDS[::-1]:
            vdescr = self.cpu.interiorfielddescrof(A, name)
            self.cpu.bh_setinteriorfield_gc_i(a_box.getref_base(), 3,
                                              -25, vdescr)
        for name, TYPE in NUMBER_FIELDS:
            vdescr = self.cpu.interiorfielddescrof(A, name)
            r = self.execute_operation(rop.GETINTERIORFIELD_GC_i,
                                       [a_box, boxint(3)],
                                       'int', descr=vdescr)
            assert r == rffi.cast(lltype.Signed, rffi.cast(TYPE, -25))
        #
        self.execute_operation(rop.SETINTERIORFIELD_GC, [a_box, boxint(4),
                                                         s_box],
                               'void', descr=pdescr)
        r = self.cpu.bh_getinteriorfield_gc_r(a_box.getref_base(), 4, pdescr)
        assert r == s_box.getref_base()
        self.cpu.bh_setinteriorfield_gc_r(a_box.getref_base(), 3,
                                          s_box.getref_base(), pdescr)
        r = self.execute_operation(rop.GETINTERIORFIELD_GC_r,
                                   [a_box, boxint(3)],
                                   'ref', descr=pdescr)
        assert r == s_box.getref_base()
        #
        # test a corner case that used to fail on x86
        i4 = boxint(4)
        self.execute_operation(rop.SETINTERIORFIELD_GC, [a_box, i4, i4],
                               'void', descr=vsdescr)
        r = self.cpu.bh_getinteriorfield_gc_i(a_box.getref_base(), 4, vsdescr)
        assert r == 4

    def test_string_basic(self):
        s_box = self.alloc_string("hello\xfe")
        r = self.execute_operation(rop.STRLEN, [s_box], 'int')
        assert r == 6
        r = self.execute_operation(rop.STRGETITEM, [s_box, boxint(5)], 'int')
        assert r == 254
        r = self.execute_operation(rop.STRSETITEM, [s_box, boxint(4),
                                                    boxint(153)], 'void')
        assert r is None
        r = self.execute_operation(rop.STRGETITEM, [s_box, boxint(5)], 'int')
        assert r == 254
        r = self.execute_operation(rop.STRGETITEM, [s_box, boxint(4)], 'int')
        assert r == 153

    def test_copystrcontent(self):
        s_box = self.alloc_string("abcdef")
        for s_box in [s_box, s_box.constbox()]:
            for srcstart_box in [boxint(2), ConstInt(2)]:
                for dststart_box in [boxint(3), ConstInt(3)]:
                    for length_box in [boxint(4), ConstInt(4)]:
                        for r_box_is_const in [False, True]:
                            r_box = self.alloc_string("!???????!")
                            if r_box_is_const:
                                r_box = r_box.constbox()
                                self.execute_operation(rop.COPYSTRCONTENT,
                                                       [s_box, r_box,
                                                        srcstart_box,
                                                        dststart_box,
                                                        length_box], 'void')
                                assert self.look_string(r_box) == "!??cdef?!"

    def test_copyunicodecontent(self):
        s_box = self.alloc_unicode(u"abcdef")
        for s_box in [s_box, s_box.constbox()]:
            for srcstart_box in [boxint(2), ConstInt(2)]:
                for dststart_box in [boxint(3), ConstInt(3)]:
                    for length_box in [boxint(4), ConstInt(4)]:
                        for r_box_is_const in [False, True]:
                            r_box = self.alloc_unicode(u"!???????!")
                            if r_box_is_const:
                                r_box = r_box.constbox()
                                self.execute_operation(rop.COPYUNICODECONTENT,
                                                       [s_box, r_box,
                                                        srcstart_box,
                                                        dststart_box,
                                                        length_box], 'void')
                                assert self.look_unicode(r_box) == u"!??cdef?!"

    def test_do_unicode_basic(self):
        u = self.cpu.bh_newunicode(5)
        self.cpu.bh_unicodesetitem(u, 4, 123)
        r = self.cpu.bh_unicodegetitem(u, 4)
        assert r == 123

    def test_unicode_basic(self):
        u_box = self.alloc_unicode(u"hello\u1234")
        r = self.execute_operation(rop.UNICODELEN, [u_box], 'int')
        assert r == 6
        r = self.execute_operation(rop.UNICODEGETITEM, [u_box, boxint(5)],
                                   'int')
        assert r == 0x1234
        r = self.execute_operation(rop.UNICODESETITEM, [u_box, boxint(4),
                                                        boxint(31313)], 'void')
        assert r is None
        r = self.execute_operation(rop.UNICODEGETITEM, [u_box, boxint(5)],
                                   'int')
        assert r == 0x1234
        r = self.execute_operation(rop.UNICODEGETITEM, [u_box, boxint(4)],
                                   'int')
        assert r == 31313

    def test_same_as(self):
        r = self.execute_operation(rop.SAME_AS_i, [ConstInt(5)], 'int')
        assert r == 5
        r = self.execute_operation(rop.SAME_AS_i, [boxint(5)], 'int')
        assert r == 5
        u_box = self.alloc_unicode(u"hello\u1234")
        r = self.execute_operation(rop.SAME_AS_r, [u_box.constbox()], 'ref')
        assert r == u_box.getref_base()
        r = self.execute_operation(rop.SAME_AS_r, [u_box], 'ref')
        assert r == u_box.getref_base()

        if self.cpu.supports_floats:
            r = self.execute_operation(rop.SAME_AS_f, [constfloat(5.5)], 'float')
            assert r == 5.5
            r = self.execute_operation(rop.SAME_AS_f, [boxfloat(5.5)], 'float')
            assert r == 5.5

    def test_arguments_to_execute_token(self):
        # this test checks that execute_token() can be called with any
        # variant of ints and floats as arguments
        if self.cpu.supports_floats:
            numkinds = 2
        else:
            numkinds = 1
        seed = random.randrange(0, 10000)
        print 'Seed is', seed    # or choose it by changing the previous line
        r = random.Random()
        r.seed(seed)
        for nb_args in range(50):
            print 'Passing %d arguments to execute_token...' % nb_args
            #
            text2op = {}
            inputargs = []
            values = []
            for k in range(nb_args):
                kind = r.randrange(0, numkinds)
                if kind == 0:
                    inputargs.append(boxint())
                    values.append(r.randrange(-100000, 100000))
                    text2op['ii%d' % k] = inputargs[-1]
                else:
                    inputargs.append(boxfloat())
                    values.append(longlong.getfloatstorage(r.random()))
                    text2op['fi%d' % k] = inputargs[-1]
            #
            looptoken = JitCellToken()
            faildescr = BasicFailDescr(42)
            operations = []
            #
            ks = range(nb_args)
            random.shuffle(ks)
            retvalues = []
            for k in ks:
                if inputargs[k].type == INT:
                    x = r.randrange(-100000, 100000)
                    operations.append(
                        create_resop_2(rop.INT_ADD, 0, inputargs[k],
                                       ConstInt(x))
                        )
                    text2op['io%d' % k] = operations[-1]
                    y = values[k] + x
                else:
                    x = r.random()
                    operations.append(
                        create_resop_2(rop.FLOAT_ADD, 0.0, inputargs[k],
                                       constfloat(x))
                        )
                    text2op['fo%d' % k] = operations[-1]
                    y = longlong.getrealfloat(values[k]) + x
                    y = longlong.getfloatstorage(y)
                retvalues.append(y)
            #
            operations.append(
                create_resop(rop.FINISH, None, [], descr=faildescr,
                             mutable=True)
                )
            self.update_varindexes(text2op)
            print inputargs
            for op in operations:
                print op
            self.cpu.compile_loop(inputargs, operations, looptoken)
            #
            frame = self.cpu.execute_token(looptoken, *values)
            assert self.cpu.get_latest_descr(frame).identifier == 42
            #
            for k, expected in zip(ks, retvalues):
                if 'io%d' % k in text2op:
                    got = self.get_frame_value(frame, 'io%d' % k)
                else:
                    got = self.get_frame_value(frame, 'fo%d' % k)
                assert got == expected

    def test_jump(self):
        # this test generates small loops where the JUMP passes many
        # arguments of various types, shuffling them around.
        if self.cpu.supports_floats:
            numkinds = 3
        else:
            numkinds = 2
        seed = random.randrange(0, 10000)
        print 'Seed is', seed    # or choose it by changing the previous line
        r = random.Random()
        r.seed(seed)
        for nb_args in range(50):
            print 'Passing %d arguments around...' % nb_args
            #
            inputargs = []
            for k in range(nb_args):
                kind = r.randrange(0, numkinds)
                if kind == 0:
                    inputargs.append("i%d" % (k + 10))
                elif kind == 1:
                    inputargs.append("p%d" % k)
                else:
                    inputargs.append("f%d" % k)
            jumpargs = []
            remixing = []
            for srcbox in inputargs:
                n = r.randrange(0, len(inputargs))
                otherbox = inputargs[n]
                if otherbox[0] == srcbox[0]:
                    remixing.append((srcbox, otherbox))
                else:
                    otherbox = srcbox
                jumpargs.append(otherbox)
            #
            index_counter = r.randrange(0, len(inputargs)+1)
            inputargs.insert(index_counter, "i0")
            jumpargs.insert(index_counter, "i1")
            inp = ", ".join(inputargs)
            inpargs, operations, looptoken = self.parse("""
            [%s]
            label(%s, descr=targettoken)
            i1 = int_sub(i0, 1)
            i2 = int_ge(i1, 0)
            guard_true(i2, descr=faildescr)
            jump(%s, descr=targettoken)
            """ % (inp, inp, ", ".join(jumpargs)), None)
            #
            self.cpu.compile_loop(inpargs, operations, looptoken)
            #
            values = []
            S = lltype.GcStruct('S')
            for box in inpargs:
                if box.type == INT:
                    values.append(r.randrange(-10000, 10000))
                elif box.type == REF:
                    p = lltype.malloc(S)
                    values.append(lltype.cast_opaque_ptr(llmemory.GCREF, p))
                elif box.type == FLOAT:
                    values.append(longlong.getfloatstorage(r.random()))
                else:
                    assert 0
            values[index_counter] = 11
            #
            frame = self.cpu.execute_token(looptoken, *values)
            assert self.cpu.get_latest_descr(frame).identifier == 1
            #
            dstvalues = values[:]
            for _ in range(11):
                expected = dstvalues[:]
                for tgtbox, srcbox in remixing:
                    v = dstvalues[inputargs.index(srcbox)]
                    expected[inputargs.index(tgtbox)] = v
                dstvalues = expected
            #
            assert dstvalues[index_counter] == 11
            dstvalues[index_counter] = 0
            assert len(inputargs) == len(inpargs) == len(dstvalues)
            for (name, val) in zip(inputargs, dstvalues):
                got = self.get_frame_value(frame, name)
                assert type(got) == type(val)
                assert got == val

    def test_compile_bridge_float(self):
        if not self.cpu.supports_floats:
            py.test.skip("requires floats")
        fboxes = "f0, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11"
        faildescr1 = BasicFailDescr(1)
        faildescr2 = BasicFailDescr(2)
        targettoken = TargetToken()
        inputargs, operations, looptoken = self.parse("""
        [%(fboxes)s]
        label(%(fboxes)s, descr=targettoken)
        i2 = float_le(f0, 9.2)
        guard_true(i2, descr=faildescr1)
        finish(descr=faildescr2)
        """ % {'fboxes': fboxes}, {'faildescr1': faildescr1,
                                   'faildescr2': faildescr2,
                                   'targettoken': targettoken})
        self.cpu.compile_loop(inputargs, operations, looptoken)

        inputargs, operations, _  = self.parse("""
        [%s]
        f15 = float_sub(f0, 1.0)
        jump(f15, %s, descr=targettoken)
        """ % (fboxes, fboxes[4:]), {'targettoken': targettoken})

        self.cpu.compile_bridge(faildescr1, inputargs, operations, looptoken)

        args = []
        for i in range(len(fboxes.split(","))):
            x = 13.5 + 6.73 * i
            args.append(longlong.getfloatstorage(x))
        frame = self.cpu.execute_token(looptoken, *args)
        assert self.cpu.get_latest_descr(frame).identifier == 2
        res = self.get_frame_value(frame, "f0")
        assert longlong.getrealfloat(res) == 8.5
        fboxeslist = map(str.strip, fboxes.split(","))
        for i in range(1, len(fboxeslist)):
            res = self.get_frame_value(frame, fboxeslist[i])
            got = longlong.getrealfloat(res)
            assert got == 13.5 + 6.73 * i

    def test_compile_bridge_spilled_float(self):
        if not self.cpu.supports_floats:
            py.test.skip("requires floats")
        fboxes = [boxfloat() for i in range(3)]
        loopops = """
        [i0, f1, f2]
        f3 = float_add(f1, f2)
        force_spill(f3)
        force_spill(f1)
        force_spill(f2)
        guard_false(i0, descr=faildescr0)
        finish()"""
        inputargs, operations, looptoken = self.parse(
            loopops, namespace={'faildescr0': BasicFailDescr(1)})
        self.cpu.compile_loop(inputargs, operations, looptoken)
        args = [1]
        args.append(longlong.getfloatstorage(132.25))
        args.append(longlong.getfloatstorage(0.75))
        frame = self.cpu.execute_token(looptoken, *args)
        assert operations[-2].getdescr()== self.cpu.get_latest_descr(frame)
        f1 = self.get_frame_value(frame, "f1")
        f2 = self.get_frame_value(frame, "f2")
        f3 = self.get_frame_value(frame, "f3")
        assert longlong.getrealfloat(f1) == 132.25
        assert longlong.getrealfloat(f2) == 0.75
        assert longlong.getrealfloat(f3) == 133.0

        faildescr1 = BasicFailDescr(100)
        bridgeops = [
            create_resop(rop.FINISH, None, [], descr=faildescr1,
                         mutable=True),
            ]
        self.cpu.compile_bridge(operations[-2].getdescr(), fboxes,
                                bridgeops, looptoken)
        frame = self.cpu.execute_token(looptoken, *args)
        assert self.cpu.get_latest_descr(frame).identifier == 100
        f1 = self.get_frame_value(frame, "f1")
        f2 = self.get_frame_value(frame, "f2")
        f3 = self.get_frame_value(frame, "f3")
        assert longlong.getrealfloat(f1) == 132.25
        assert longlong.getrealfloat(f2) == 0.75
        assert longlong.getrealfloat(f3) == 133.0

    def test_integers_and_guards2(self):
        for opname, compare in [
            (rop.INT_IS_TRUE, lambda x: bool(x)),
            (rop.INT_IS_ZERO, lambda x: not bool(x))]:
            for opguard, guard_case in [
                (rop.GUARD_FALSE, False),
                (rop.GUARD_TRUE,  True),
                ]:
                box = boxint()
                faildescr1 = BasicFailDescr(1)
                faildescr2 = BasicFailDescr(2)
                inputargs = [box]
                op0 = create_resop_1(opname, 0, box)
                op1 = create_resop_1(opguard, None, op0, mutable=True)
                op1.setdescr(faildescr1)
                op1.setfailargs([])
                op2 = create_resop(rop.FINISH, None, [], descr=faildescr2,
                                   mutable=True)
                looptoken = JitCellToken()
                self.cpu.compile_loop(inputargs, [op0, op1, op2], looptoken)
                #
                cpu = self.cpu
                for value in [-42, 0, 1, 10]:
                    frame = cpu.execute_token(looptoken, value)
                    #
                    expected = compare(value)
                    expected ^= guard_case
                    assert self.cpu.get_latest_descr(frame).identifier == (
                        2 - expected)

    def test_integers_and_guards(self):
        for opname, compare in [
            (rop.INT_LT, lambda x, y: x < y),
            (rop.INT_LE, lambda x, y: x <= y),
            (rop.INT_EQ, lambda x, y: x == y),
            (rop.INT_NE, lambda x, y: x != y),
            (rop.INT_GT, lambda x, y: x > y),
            (rop.INT_GE, lambda x, y: x >= y),
            ]:
            for opguard, guard_case in [
                (rop.GUARD_FALSE, False),
                (rop.GUARD_TRUE,  True),
                ]:
                for combinaison in ["bb", "bc", "cb"]:
                    #
                    if combinaison[0] == 'b':
                        ibox1 = boxint()
                    else:
                        ibox1 = ConstInt(-42)
                    if combinaison[1] == 'b':
                        ibox2 = boxint()
                    else:
                        ibox2 = ConstInt(-42)
                    faildescr1 = BasicFailDescr(1)
                    faildescr2 = BasicFailDescr(2)
                    inputargs = [ib for ib in [ibox1, ibox2]
                                 if not ib.is_constant()]
                    op0 = create_resop_2(opname, 0, ibox1, ibox2)
                    op1 = create_resop_1(opguard, None, op0, mutable=True)
                    op1.setdescr(faildescr1)
                    op1.setfailargs([])
                    op2 = create_resop(rop.FINISH, None, [], descr=faildescr2,
                                       mutable=True)
                    operations = [op0, op1, op2]
                    looptoken = JitCellToken()
                    self.cpu.compile_loop(inputargs, operations, looptoken)
                    #
                    cpu = self.cpu
                    for test1 in [-65, -42, -11, 0, 1, 10]:
                        if test1 == -42 or combinaison[0] == 'b':
                            for test2 in [-65, -42, -11, 0, 1, 10]:
                                if test2 == -42 or combinaison[1] == 'b':
                                    args = []
                                    if combinaison[0] == 'b':
                                        args.append(test1)
                                    if combinaison[1] == 'b':
                                        args.append(test2)
                                    frame = cpu.execute_token(looptoken, *args)
                                    #
                                    expected = compare(test1, test2)
                                    expected ^= guard_case
                                    descr = self.cpu.get_latest_descr(frame)
                                    assert descr.identifier == 2 - expected

    def test_integers_and_guards_uint(self):
        for opname, compare in [
            (rop.UINT_LE, lambda x, y: (x) <= (y)),
            (rop.UINT_GT, lambda x, y: (x) >  (y)),
            (rop.UINT_LT, lambda x, y: (x) <  (y)),
            (rop.UINT_GE, lambda x, y: (x) >= (y)),
            ]:
            for opguard, guard_case in [
                (rop.GUARD_FALSE, False),
                (rop.GUARD_TRUE,  True),
                ]:
                for combinaison in ["bb", "bc", "cb"]:
                    #
                    if combinaison[0] == 'b':
                        ibox1 = boxint()
                    else:
                        ibox1 = ConstInt(42)
                    if combinaison[1] == 'b':
                        ibox2 = boxint()
                    else:
                        ibox2 = ConstInt(42)
                    faildescr1 = BasicFailDescr(1)
                    faildescr2 = BasicFailDescr(2)
                    inputargs = [ib for ib in [ibox1, ibox2]
                                 if not ib.is_constant()]
                    op0 = create_resop_2(opname, 0, ibox1, ibox2)
                    op1 = create_resop_1(opguard, None, op0, descr=faildescr1,
                                         mutable=True)
                    op1.setfailargs([])
                    op2 = create_resop(rop.FINISH, None, [], descr=faildescr2,
                                       mutable=True)
                    looptoken = JitCellToken()
                    self.cpu.compile_loop(inputargs, [op0, op1, op2], looptoken)
                    #
                    cpu = self.cpu
                    for test1 in [65, 42, 11, 0, 1]:
                        if test1 == 42 or combinaison[0] == 'b':
                            for test2 in [65, 42, 11, 0, 1]:
                                if test2 == 42 or combinaison[1] == 'b':
                                    args = []
                                    if combinaison[0] == 'b':
                                        args.append(test1)
                                    if combinaison[1] == 'b':
                                        args.append(test2)
                                    frame = cpu.execute_token(looptoken, *args)
                                    #
                                    expected = compare(test1, test2)
                                    expected ^= guard_case
                                    descr = self.cpu.get_latest_descr(frame)
                                    assert descr.identifier == 2 - expected

    def test_floats_and_guards(self):
        if not self.cpu.supports_floats:
            py.test.skip("requires floats")
        for opname, compare in [
            (rop.FLOAT_LT, lambda x, y: x < y),
            (rop.FLOAT_LE, lambda x, y: x <= y),
            (rop.FLOAT_EQ, lambda x, y: x == y),
            (rop.FLOAT_NE, lambda x, y: x != y),
            (rop.FLOAT_GT, lambda x, y: x > y),
            (rop.FLOAT_GE, lambda x, y: x >= y),
            ]:
            for opguard, guard_case in [
                (rop.GUARD_FALSE, False),
                (rop.GUARD_TRUE,  True),
                ]:
                for combinaison in ["bb", "bc", "cb"]:
                    #
                    if combinaison[0] == 'b':
                        fbox1 = boxfloat()
                    else:
                        fbox1 = constfloat(-4.5)
                    if combinaison[1] == 'b':
                        fbox2 = boxfloat()
                    else:
                        fbox2 = constfloat(-4.5)
                    faildescr1 = BasicFailDescr(1)
                    faildescr2 = BasicFailDescr(2)
                    inputargs = [fb for fb in [fbox1, fbox2]
                                    if not fb.is_constant()]
                    op0 = create_resop_2(opname, 0, fbox1, fbox2)
                    op1 = create_resop_1(opguard, None, op0, mutable=True)
                    op1.setdescr(faildescr1)
                    op1.setfailargs([])
                    op2 = create_resop(rop.FINISH, None, [], descr=faildescr2,
                                       mutable=True)
                    operations = [op0, op1, op2]
                    looptoken = JitCellToken()
                    self.cpu.compile_loop(inputargs, operations, looptoken)
                    #
                    cpu = self.cpu
                    nan = 1e200 * 1e200
                    nan /= nan
                    for test1 in [-6.5, -4.5, -2.5, nan]:
                        if test1 == -4.5 or combinaison[0] == 'b':
                            for test2 in [-6.5, -4.5, -2.5, nan]:
                                if test2 == -4.5 or combinaison[1] == 'b':
                                    args = []
                                    if combinaison[0] == 'b':
                                        args.append(
                                            longlong.getfloatstorage(test1))
                                    if combinaison[1] == 'b':
                                        args.append(
                                            longlong.getfloatstorage(test2))
                                    frame = cpu.execute_token(looptoken, *args)
                                    #
                                    expected = compare(test1, test2)
                                    expected ^= guard_case
                                    descr = self.cpu.get_latest_descr(frame)
                                    assert descr.identifier == 2 - expected

    def test_unused_result_int(self):
        # test pure operations on integers whose result is not used
        from pypy.jit.metainterp.test.test_executor import get_int_tests
        int_tests = list(get_int_tests())
        int_tests = [(opnum, boxargs, 'int', retvalue)
                     for opnum, boxargs, retvalue in int_tests]
        self._test_unused_result(int_tests)

    def test_unused_result_float(self):
        # same as test_unused_result_int, for float operations
        from pypy.jit.metainterp.test.test_executor import get_float_tests
        float_tests = list(get_float_tests(self.cpu))
        self._test_unused_result(float_tests)

    def _test_unused_result(self, tests):
        while len(tests) > 50:     # only up to 50 tests at once
            self._test_unused_result(tests[:50])
            tests = tests[50:]
        inputargs = []
        operations = []
        for opnum, boxargs, rettype, retvalue in tests:
            inputargs += [box for box in boxargs if not box.is_constant()]
            if rettype == 'int':
                res = 0
            elif rettype == 'float':
                res = 0.0
            else:
                assert 0
            operations.append(create_resop_dispatch(opnum, res, boxargs,
                                                    mutable=True))
        # Unique-ify inputargs
        inputargs = list(set(inputargs))
        faildescr = BasicFailDescr(1)
        operations.append(create_resop(rop.FINISH, None, [],
                                       descr=faildescr, mutable=True))
        looptoken = JitCellToken()
        #
        self.cpu.compile_loop(inputargs, operations, looptoken)
        #
        args = []
        for box in inputargs:
            if box.type == INT:
                args.append(box.getint())
            elif box.type == FLOAT:
                args.append(box.getfloatstorage())
            else:
                assert 0
        #
        frame = self.cpu.execute_token(looptoken, *args)
        assert self.cpu.get_latest_descr(frame).identifier == 1

    def test_nan_and_infinity(self):
        if not self.cpu.supports_floats:
            py.test.skip("requires floats")

        from pypy.rlib.rfloat import INFINITY, NAN, isinf, isnan
        from pypy.jit.metainterp.resoperation import opname

        fzer = boxfloat(0.0)
        fone = boxfloat(1.0)
        fmqr = boxfloat(-0.25)
        finf = boxfloat(INFINITY)
        fmnf = boxfloat(-INFINITY)
        fnan = boxfloat(NAN)

        all_cases_unary =  [(a,)   for a in [fzer,fone,fmqr,finf,fmnf,fnan]]
        all_cases_binary = [(a, b) for a in [fzer,fone,fmqr,finf,fmnf,fnan]
                                   for b in [fzer,fone,fmqr,finf,fmnf,fnan]]
        no_zero_divison  = [(a, b) for a in [fzer,fone,fmqr,finf,fmnf,fnan]
                                   for b in [     fone,fmqr,finf,fmnf,fnan]]

        def nan_and_infinity(opnum, realoperation, testcases):
            for testcase in testcases:
                realvalues = [b.getfloat() for b in testcase]
                expected = realoperation(*realvalues)
                if isinstance(expected, float):
                    expectedtype = 'float'
                else:
                    expectedtype = 'int'
                got = self.execute_operation(opnum, list(testcase),
                                             expectedtype)
                if isnan(expected):
                    ok = isnan(got)
                elif isinf(expected):
                    ok = isinf(got)
                else:
                    ok = got == expected
                if not ok:
                    raise AssertionError("%s(%s): got %r, expected %r" % (
                        opname[opnum], ', '.join(map(repr, realvalues)),
                        got.getfloat(), expected))
                # if we expect a boolean, also check the combination with
                # a GUARD_TRUE or GUARD_FALSE
                if isinstance(expected, bool):
                    for guard_opnum, expected_id in [(rop.GUARD_TRUE, 1),
                                                     (rop.GUARD_FALSE, 0)]:
                        op0 = create_resop_2(opnum, 0, *testcase)
                        op1 = create_resop_1(guard_opnum, None, op0,
                                             mutable=True)
                        op1.setfailargs([])
                        op1.setdescr(BasicFailDescr(4))
                        op2 = create_resop(rop.FINISH, None, [],
                                           descr=BasicFailDescr(5),
                                           mutable=True)
                        operations = [op0, op1, op2]
                        looptoken = JitCellToken()
                        # Use "set" to unique-ify inputargs
                        unique_testcase_list = list(set(testcase))
                        self.cpu.compile_loop(unique_testcase_list, operations,
                                              looptoken)
                        args = [box.getfloatstorage()
                                for box in unique_testcase_list]
                        frame = self.cpu.execute_token(looptoken, *args)
                        descr = self.cpu.get_latest_descr(frame)
                        if descr.identifier != 5 - (expected_id^expected):
                            if descr.identifier == 4:
                                msg = "was taken"
                            else:
                                msg = "was not taken"
                            raise AssertionError(
                                "%s(%s)/%s took the wrong path: "
                                "the failure path of the guard %s" % (
                                    opname[opnum],
                                    ', '.join(map(repr, realvalues)),
                                    opname[guard_opnum], msg))

        yield nan_and_infinity, rop.FLOAT_ADD, operator.add, all_cases_binary
        yield nan_and_infinity, rop.FLOAT_SUB, operator.sub, all_cases_binary
        yield nan_and_infinity, rop.FLOAT_MUL, operator.mul, all_cases_binary
        yield nan_and_infinity, rop.FLOAT_TRUEDIV, \
                                           operator.truediv, no_zero_divison
        yield nan_and_infinity, rop.FLOAT_NEG, operator.neg, all_cases_unary
        yield nan_and_infinity, rop.FLOAT_ABS, abs,          all_cases_unary
        yield nan_and_infinity, rop.FLOAT_LT,  operator.lt,  all_cases_binary
        yield nan_and_infinity, rop.FLOAT_LE,  operator.le,  all_cases_binary
        yield nan_and_infinity, rop.FLOAT_EQ,  operator.eq,  all_cases_binary
        yield nan_and_infinity, rop.FLOAT_NE,  operator.ne,  all_cases_binary
        yield nan_and_infinity, rop.FLOAT_GT,  operator.gt,  all_cases_binary
        yield nan_and_infinity, rop.FLOAT_GE,  operator.ge,  all_cases_binary

    def test_noops(self):
        c_box = self.alloc_string("hi there").constbox()
        c_nest = ConstInt(0)
        c_id = ConstInt(0)
        self.execute_operation(rop.DEBUG_MERGE_POINT, [c_box, c_nest, c_id], 'void')
        self.execute_operation(rop.JIT_DEBUG, [c_box, c_nest, c_nest,
                                               c_nest, c_nest], 'void')

    def test_read_timestamp(self):
        if not self.cpu.supports_longlong:
            py.test.skip("longlong test")
        if sys.platform == 'win32':
            # windows quite often is very inexact (like the old Intel 8259 PIC),
            # so we stretch the time a little bit.
            # On my virtual Parallels machine in a 2GHz Core i7 Mac Mini,
            # the test starts working at delay == 21670 and stops at 20600000.
            # We take the geometric mean value.
            from math import log, exp
            delay_min = 21670
            delay_max = 20600000
            delay = int(exp((log(delay_min)+log(delay_max))/2))
            def wait_a_bit():
                for i in xrange(delay): pass
        else:
            def wait_a_bit():
                pass
        if longlong.is_64_bit:
            restype = 'int'
        else:
            restype = 'float'
        res1 = self.execute_operation(rop.READ_TIMESTAMP, [], restype)
        wait_a_bit()
        res2 = self.execute_operation(rop.READ_TIMESTAMP, [], restype)
        assert res1 < res2 < res1 + 2**32


class LLtypeBackendTest(BaseBackendTest):

    type_system = 'lltype'
    Ptr = lltype.Ptr
    FuncType = lltype.FuncType
    malloc = staticmethod(lltype.malloc)
    nullptr = staticmethod(lltype.nullptr)

    @classmethod
    def get_funcbox(cls, cpu, func_ptr):
        addr = llmemory.cast_ptr_to_adr(func_ptr)
        return ConstInt(heaptracker.adr2int(addr))


    MY_VTABLE = rclass.OBJECT_VTABLE    # for tests only

    S = lltype.GcForwardReference()
    S.become(lltype.GcStruct('S', ('parent', rclass.OBJECT),
                                  ('value', lltype.Signed),
                                  ('chr1', lltype.Char),
                                  ('chr2', lltype.Char),
                                  ('short', rffi.SHORT),
                                  ('next', lltype.Ptr(S)),
                                  ('float', lltype.Float)))
    T = lltype.GcStruct('T', ('parent', S),
                             ('next', lltype.Ptr(S)))
    U = lltype.GcStruct('U', ('parent', T),
                             ('next', lltype.Ptr(S)))


    def alloc_instance(self, T):
        vtable_for_T = lltype.malloc(self.MY_VTABLE, immortal=True)
        vtable_for_T_addr = llmemory.cast_ptr_to_adr(vtable_for_T)
        cpu = self.cpu
        if not hasattr(cpu, '_cache_gcstruct2vtable'):
            cpu._cache_gcstruct2vtable = {}
        cpu._cache_gcstruct2vtable.update({T: vtable_for_T})
        t = lltype.malloc(T)
        if T == self.T:
            t.parent.parent.typeptr = vtable_for_T
        elif T == self.U:
            t.parent.parent.parent.typeptr = vtable_for_T
        t_box = boxptr(lltype.cast_opaque_ptr(llmemory.GCREF, t))
        T_box = ConstInt(heaptracker.adr2int(vtable_for_T_addr))
        return t_box, T_box

    def null_instance(self):
        return boxptr(lltype.nullptr(llmemory.GCREF.TO))

    def alloc_array_of(self, ITEM, length):
        A = lltype.GcArray(ITEM)
        a = lltype.malloc(A, length)
        a_box = boxptr(lltype.cast_opaque_ptr(llmemory.GCREF, a))
        return a_box, A

    def alloc_string(self, string):
        s = rstr.mallocstr(len(string))
        for i in range(len(string)):
            s.chars[i] = string[i]
        s_box = boxptr(lltype.cast_opaque_ptr(llmemory.GCREF, s))
        return s_box

    def look_string(self, string_box):
        s = string_box.getref(lltype.Ptr(rstr.STR))
        return ''.join(s.chars)

    def alloc_unicode(self, unicode):
        u = rstr.mallocunicode(len(unicode))
        for i in range(len(unicode)):
            u.chars[i] = unicode[i]
        u_box = boxptr(lltype.cast_opaque_ptr(llmemory.GCREF, u))
        return u_box

    def look_unicode(self, unicode_box):
        u = unicode_box.getref(lltype.Ptr(rstr.UNICODE))
        return u''.join(u.chars)


    def test_cast_int_to_ptr(self):
        res = self.execute_operation(rop.CAST_INT_TO_PTR,
                                     [boxint(-17)],  'ref')
        assert lltype.cast_ptr_to_int(res) == -17

    def test_cast_ptr_to_int(self):
        x = lltype.cast_int_to_ptr(llmemory.GCREF, -19)
        res = self.execute_operation(rop.CAST_PTR_TO_INT,
                                     [boxptr(x)], 'int')
        assert res == -19

    def test_convert_float_bytes(self):
        if not self.cpu.supports_floats:
            py.test.skip("requires floats")
        box = boxfloat(2.5)
        t = 'int' if longlong.is_64_bit else 'float'
        res = self.execute_operation(rop.CONVERT_FLOAT_BYTES_TO_LONGLONG,
                                     [box], t)
        assert longlong.longlong2floatstorage(res) == 2.5

        if longlong.is_64_bit:
            box = boxint(res)
        else:
            box = boxfloat(res)
        res = self.execute_operation(rop.CONVERT_LONGLONG_BYTES_TO_FLOAT,
                                     [box], 'float')
        assert res == 2.5

    def test_ooops_non_gc(self):
        x = lltype.malloc(lltype.Struct('x'), flavor='raw')
        v = heaptracker.adr2int(llmemory.cast_ptr_to_adr(x))
        r = self.execute_operation(rop.PTR_EQ, [boxint(v), boxint(v)], 'int')
        assert r == 1
        r = self.execute_operation(rop.PTR_NE, [boxint(v), boxint(v)], 'int')
        assert r == 0
        lltype.free(x, flavor='raw')

    def test_new_plain_struct(self):
        cpu = self.cpu
        S = lltype.GcStruct('S', ('x', lltype.Char), ('y', lltype.Char))
        sizedescr = cpu.sizeof(S)
        r1 = self.execute_operation(rop.NEW, [], 'ref', descr=sizedescr)
        r2 = self.execute_operation(rop.NEW, [], 'ref', descr=sizedescr)
        assert r1 != r2
        xdescr = cpu.fielddescrof(S, 'x')
        ydescr = cpu.fielddescrof(S, 'y')
        self.execute_operation(rop.SETFIELD_GC, [boxptr(r1), boxint(150)],
                               'void', descr=ydescr)
        self.execute_operation(rop.SETFIELD_GC, [boxptr(r1), boxint(190)],
                               'void', descr=xdescr)
        s = lltype.cast_opaque_ptr(lltype.Ptr(S), r1)
        assert s.x == chr(190)
        assert s.y == chr(150)

    def test_new_with_vtable(self):
        cpu = self.cpu
        t_box, T_box = self.alloc_instance(self.T)
        vtable = llmemory.cast_adr_to_ptr(
            llmemory.cast_int_to_adr(T_box.value), heaptracker.VTABLETYPE)
        heaptracker.register_known_gctype(cpu, vtable, self.T)
        r1 = self.execute_operation(rop.NEW_WITH_VTABLE, [T_box], 'ref')
        r2 = self.execute_operation(rop.NEW_WITH_VTABLE, [T_box], 'ref')
        assert r1 != r2
        descr1 = cpu.fielddescrof(self.S, 'chr1')
        descr2 = cpu.fielddescrof(self.S, 'chr2')
        descrshort = cpu.fielddescrof(self.S, 'short')
        self.execute_operation(rop.SETFIELD_GC, [boxptr(r1), boxint(150)],
                               'void', descr=descr2)
        self.execute_operation(rop.SETFIELD_GC, [boxptr(r1), boxint(190)],
                               'void', descr=descr1)
        self.execute_operation(rop.SETFIELD_GC, [boxptr(r1), boxint(1313)],
                               'void', descr=descrshort)
        s = lltype.cast_opaque_ptr(lltype.Ptr(self.T), r1)
        assert s.parent.chr1 == chr(190)
        assert s.parent.chr2 == chr(150)
        r = self.cpu.bh_getfield_gc_i(r1, descrshort)
        assert r == 1313
        self.cpu.bh_setfield_gc_i(r1, 1333, descrshort)
        r = self.cpu.bh_getfield_gc_i(r1, descrshort)
        assert r == 1333
        r = self.execute_operation(rop.GETFIELD_GC_i, [boxptr(r1)], 'int',
                                   descr=descrshort)
        assert r == 1333
        t = lltype.cast_opaque_ptr(lltype.Ptr(self.T), t_box.getref_base())
        assert s.parent.parent.typeptr == t.parent.parent.typeptr

    def test_new_array(self):
        A = lltype.GcArray(lltype.Signed)
        arraydescr = self.cpu.arraydescrof(A)
        r1 = self.execute_operation(rop.NEW_ARRAY, [boxint(342)],
                                    'ref', descr=arraydescr)
        r2 = self.execute_operation(rop.NEW_ARRAY, [boxint(342)],
                                    'ref', descr=arraydescr)
        assert r1 != r2
        a = lltype.cast_opaque_ptr(lltype.Ptr(A), r1)
        assert a[0] == 0
        assert len(a) == 342

    def test_new_string(self):
        r1 = self.execute_operation(rop.NEWSTR, [boxint(342)], 'ref')
        r2 = self.execute_operation(rop.NEWSTR, [boxint(342)], 'ref')
        assert r1 != r2
        a = lltype.cast_opaque_ptr(lltype.Ptr(rstr.STR), r1)
        assert len(a.chars) == 342

    def test_new_unicode(self):
        r1 = self.execute_operation(rop.NEWUNICODE, [boxint(342)], 'ref')
        r2 = self.execute_operation(rop.NEWUNICODE, [boxint(342)], 'ref')
        assert r1 != r2
        a = lltype.cast_opaque_ptr(lltype.Ptr(rstr.UNICODE), r1)
        assert len(a.chars) == 342

    def test_exceptions(self):
        exc_tp = None
        exc_ptr = None
        def func(i):
            if i:
                raise LLException(exc_tp, exc_ptr)

        ops = '''
        [i0]
        i1 = same_as_i(1)
        call_v(ConstClass(fptr), i0, descr=calldescr)
        p0 = guard_exception(ConstClass(xtp), descr=faildescr2) [i1]
        finish(p0, descr=faildescr1) []
        '''
        FPTR = lltype.Ptr(lltype.FuncType([lltype.Signed], lltype.Void))
        fptr = llhelper(FPTR, func)
        calldescr = self.cpu.calldescrof(FPTR.TO, FPTR.TO.ARGS, FPTR.TO.RESULT,
                                         EffectInfo.MOST_GENERAL)

        xtp = lltype.malloc(rclass.OBJECT_VTABLE, immortal=True)
        xtp.subclassrange_min = 1
        xtp.subclassrange_max = 3
        X = lltype.GcStruct('X', ('parent', rclass.OBJECT),
                            hints={'vtable':  xtp._obj})
        xptr = lltype.cast_opaque_ptr(llmemory.GCREF, lltype.malloc(X))


        exc_tp = xtp
        exc_ptr = xptr
        faildescr1 = BasicFailDescr(1)
        faildescr2 = BasicFailDescr(2)
        inputargs, operations, looptoken = self.parse(ops, namespace=locals())
        self.cpu.compile_loop(inputargs, operations, looptoken)
        frame = self.cpu.execute_token(looptoken, 1)
        assert self.cpu.get_finish_value_ref(frame) == xptr
        frame = self.cpu.execute_token(looptoken, 0)
        assert self.cpu.get_latest_value_int(frame, 0) == 1
        excvalue = self.cpu.grab_exc_value(frame)
        assert not excvalue

        ytp = lltype.malloc(rclass.OBJECT_VTABLE, immortal=True)
        ytp.subclassrange_min = 2
        ytp.subclassrange_max = 2
        assert rclass.ll_issubclass(ytp, xtp)
        Y = lltype.GcStruct('Y', ('parent', rclass.OBJECT),
                            hints={'vtable':  ytp._obj})
        yptr = lltype.cast_opaque_ptr(llmemory.GCREF, lltype.malloc(Y))

        # guard_exception uses an exact match
        exc_tp = ytp
        exc_ptr = yptr
        inputargs, operations, looptoken = self.parse(ops, namespace=locals())
        self.cpu.compile_loop(inputargs, operations, looptoken)
        frame = self.cpu.execute_token(looptoken, 1)
        assert self.cpu.get_latest_value_int(frame, 0) == 1
        excvalue = self.cpu.grab_exc_value(frame)
        assert excvalue == yptr

        exc_tp = xtp
        exc_ptr = xptr
        ops = '''
        [i0]
        i1 = same_as_i(1)
        call_v(ConstClass(fptr), i0, descr=calldescr)
        guard_no_exception(descr=faildescr1) [i1]
        finish(-100, descr=faildescr2) []
        '''
        inputargs, operations, looptoken = self.parse(ops, namespace=locals())
        self.cpu.compile_loop(inputargs, operations, looptoken)
        frame = self.cpu.execute_token(looptoken, 1)
        assert self.cpu.get_latest_value_int(frame, 0) == 1
        excvalue = self.cpu.grab_exc_value(frame)
        assert excvalue == xptr
        frame = self.cpu.execute_token(looptoken, 0)
        assert self.cpu.get_finish_value_int(frame) == -100

    def test_cond_call_gc_wb(self):
        def func_void(a):
            record.append(a)
        record = []
        #
        S = lltype.GcStruct('S', ('tid', lltype.Signed))
        FUNC = self.FuncType([lltype.Ptr(S)], lltype.Void)
        func_ptr = llhelper(lltype.Ptr(FUNC), func_void)
        funcbox = self.get_funcbox(self.cpu, func_ptr)
        class WriteBarrierDescr(AbstractDescr):
            jit_wb_if_flag = 4096
            jit_wb_if_flag_byteofs = struct.pack("i", 4096).index('\x10')
            jit_wb_if_flag_singlebyte = 0x10
            def get_write_barrier_fn(self, cpu):
                return funcbox.getint()
        #
        for cond in [False, True]:
            value = random.randrange(-sys.maxint, sys.maxint)
            if cond:
                value |= 4096
            else:
                value &= ~4096
            s = lltype.malloc(S)
            s.tid = value
            sgcref = lltype.cast_opaque_ptr(llmemory.GCREF, s)
            t = lltype.malloc(S)
            tgcref = lltype.cast_opaque_ptr(llmemory.GCREF, t)
            del record[:]
            self.execute_operation(rop.COND_CALL_GC_WB,
                                   [boxptr(sgcref), ConstPtr(tgcref)],
                                   'void', descr=WriteBarrierDescr())
            if cond:
                assert record == [s]
            else:
                assert record == []

    def test_cond_call_gc_wb_array(self):
        def func_void(a):
            record.append(a)
        record = []
        #
        S = lltype.GcStruct('S', ('tid', lltype.Signed))
        FUNC = self.FuncType([lltype.Ptr(S)], lltype.Void)
        func_ptr = llhelper(lltype.Ptr(FUNC), func_void)
        funcbox = self.get_funcbox(self.cpu, func_ptr)
        class WriteBarrierDescr(AbstractDescr):
            jit_wb_if_flag = 4096
            jit_wb_if_flag_byteofs = struct.pack("i", 4096).index('\x10')
            jit_wb_if_flag_singlebyte = 0x10
            jit_wb_cards_set = 0       # <= without card marking
            def get_write_barrier_fn(self, cpu):
                return funcbox.getint()
        #
        for cond in [False, True]:
            value = random.randrange(-sys.maxint, sys.maxint)
            if cond:
                value |= 4096
            else:
                value &= ~4096
            s = lltype.malloc(S)
            s.tid = value
            sgcref = lltype.cast_opaque_ptr(llmemory.GCREF, s)
            del record[:]
            self.execute_operation(rop.COND_CALL_GC_WB_ARRAY,
                       [boxptr(sgcref), ConstInt(123), boxptr(sgcref)],
                       'void', descr=WriteBarrierDescr())
            if cond:
                assert record == [s]
            else:
                assert record == []

    def test_cond_call_gc_wb_array_card_marking_fast_path(self):
        def func_void(a):
            record.append(a)
            if cond == 1:      # the write barrier sets the flag
                s.data.tid |= 32768
        record = []
        #
        S = lltype.Struct('S', ('tid', lltype.Signed))
        S_WITH_CARDS = lltype.Struct('S_WITH_CARDS',
                                     ('card0', lltype.Char),
                                     ('card1', lltype.Char),
                                     ('card2', lltype.Char),
                                     ('card3', lltype.Char),
                                     ('card4', lltype.Char),
                                     ('card5', lltype.Char),
                                     ('card6', lltype.Char),
                                     ('card7', lltype.Char),
                                     ('data',  S))
        FUNC = self.FuncType([lltype.Ptr(S)], lltype.Void)
        func_ptr = llhelper(lltype.Ptr(FUNC), func_void)
        funcbox = self.get_funcbox(self.cpu, func_ptr)
        class WriteBarrierDescr(AbstractDescr):
            jit_wb_if_flag = 4096
            jit_wb_if_flag_byteofs = struct.pack("i", 4096).index('\x10')
            jit_wb_if_flag_singlebyte = 0x10
            jit_wb_cards_set = 32768
            jit_wb_cards_set_byteofs = struct.pack("i", 32768).index('\x80')
            jit_wb_cards_set_singlebyte = -0x80
            jit_wb_card_page_shift = 7
            def get_write_barrier_from_array_fn(self, cpu):
                return funcbox.getint()
        #
        for BoxIndexCls in [boxint, ConstInt]*3:
            for cond in [-1, 0, 1, 2]:
                # cond=-1:GCFLAG_TRACK_YOUNG_PTRS, GCFLAG_CARDS_SET are not set
                # cond=0: GCFLAG_CARDS_SET is never set
                # cond=1: GCFLAG_CARDS_SET is not set, but the wb sets it
                # cond=2: GCFLAG_CARDS_SET is already set
                print
                print '_'*79
                print 'BoxIndexCls =', BoxIndexCls
                print 'testing cond =', cond
                print
                value = random.randrange(-sys.maxint, sys.maxint)
                if cond >= 0:
                    value |= 4096
                else:
                    value &= ~4096
                if cond == 2:
                    value |= 32768
                else:
                    value &= ~32768
                s = lltype.malloc(S_WITH_CARDS, immortal=True, zero=True)
                s.data.tid = value
                sgcref = rffi.cast(llmemory.GCREF, s.data)
                del record[:]
                box_index = BoxIndexCls((9<<7) + 17)
                self.execute_operation(rop.COND_CALL_GC_WB_ARRAY,
                           [boxptr(sgcref), box_index, boxptr(sgcref)],
                           'void', descr=WriteBarrierDescr())
                if cond in [0, 1]:
                    assert record == [s.data]
                else:
                    assert record == []
                if cond in [1, 2]:
                    assert s.card6 == '\x02'
                else:
                    assert s.card6 == '\x00'
                assert s.card0 == '\x00'
                assert s.card1 == '\x00'
                assert s.card2 == '\x00'
                assert s.card3 == '\x00'
                assert s.card4 == '\x00'
                assert s.card5 == '\x00'
                assert s.card7 == '\x00'
                if cond == 1:
                    value |= 32768
                assert s.data.tid == value

    def test_force_operations_returning_void(self):
        values = []
        def maybe_force(token, flag):
            assert lltype.typeOf(token) == cpu.JITFRAMEPTR
            if flag:
                descr = self.cpu.get_latest_descr(token)
                values.append(descr)
                x = self.cpu.force(token)
                assert x is None
                values.append(self.cpu.get_latest_value_int(token, 0))
                values.append(self.cpu.get_latest_value_int(token, 1))
                values.append(token)

        FUNC = self.FuncType([self.cpu.JITFRAMEPTR, lltype.Signed], lltype.Void)
        func_ptr = llhelper(lltype.Ptr(FUNC), maybe_force)
        #funcbox = self.get_funcbox(self.cpu, func_ptr).constbox()
        calldescr = self.cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT,
                                         EffectInfo.MOST_GENERAL)
        cpu = self.cpu
        faildescr = BasicFailDescr(1)
        faildescr0 = BasicFailDescr(0)
        inputargs, operations, looptoken = self.parse("""
        [i0, i1]
        ptok = jit_frame()
        call_may_force_v(ConstClass(func_ptr), ptok, i1, descr=calldescr)
        guard_not_forced(descr=faildescr) [i1, i0]
        finish(i0, descr=faildescr0)
        """, locals())
        self.cpu.compile_loop(inputargs, operations, looptoken)
        frame = self.cpu.execute_token(looptoken, 20, 0)
        assert self.cpu.get_latest_descr(frame).identifier == 0
        assert self.cpu.get_finish_value_int(frame) == 20
        assert values == []

        frame = self.cpu.execute_token(looptoken, 10, 1)
        assert self.cpu.get_latest_descr(frame).identifier == 1
        assert self.cpu.get_latest_value_int(frame, 0) == 1
        assert self.cpu.get_latest_value_int(frame, 1) == 10
        assert values == [faildescr, 1, 10, frame]

    def test_force_operations_returning_int(self):
        values = []
        def maybe_force(token, flag):
            if flag:
               self.cpu.force(token)
               values.append(self.cpu.get_latest_value_int(token, 0))
               values.append(self.cpu.get_latest_value_int(token, 2))
               values.append(token)
            return 42

        FUNC = self.FuncType([self.cpu.JITFRAMEPTR, lltype.Signed],
                             lltype.Signed)
        func_ptr = llhelper(lltype.Ptr(FUNC), maybe_force)
        calldescr = self.cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT,
                                         EffectInfo.MOST_GENERAL)
        cpu = self.cpu
        faildescr0 = BasicFailDescr(0)
        inputargs, ops, looptoken = self.parse("""
        [i0, i1]
        ptok = jit_frame()
        i2 = call_may_force_i(ConstClass(func_ptr), ptok, i1, descr=calldescr)
        guard_not_forced(descr=faildescr) [i1, i2, i0]
        finish(i2, descr=faildescr0)
        """, locals())
        self.cpu.compile_loop(inputargs, ops, looptoken)
        frame = self.cpu.execute_token(looptoken, 20, 0)
        assert self.cpu.get_latest_descr(frame).identifier == 0
        assert self.cpu.get_finish_value_int(frame) == 42
        assert values == []

        frame = self.cpu.execute_token(looptoken, 10, 1)
        assert self.cpu.get_latest_descr(frame).identifier == 1
        assert self.cpu.get_latest_value_int(frame, 0) == 1
        assert self.cpu.get_latest_value_int(frame, 1) == 42
        assert self.cpu.get_latest_value_int(frame, 2) == 10
        assert values == [1, 10, frame]

    def test_force_operations_returning_float(self):
        if not self.cpu.supports_floats:
            py.test.skip("requires floats")
        values = []
        def maybe_force(token, flag):
            if flag:
               self.cpu.force(token)
               values.append(self.cpu.get_latest_value_int(token, 0))
               values.append(self.cpu.get_latest_value_int(token, 2))
               values.append(token)
            return 42.5

        FUNC = self.FuncType([self.cpu.JITFRAMEPTR, lltype.Signed], lltype.Float)
        func_ptr = llhelper(lltype.Ptr(FUNC), maybe_force)
        calldescr = self.cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT,
                                         EffectInfo.MOST_GENERAL)
        cpu = self.cpu
        faildescr = BasicFailDescr(1)
        faildescr0 = BasicFailDescr(0)
        inputargs, ops, looptoken = self.parse("""
        [i0, i1]
        ptok = jit_frame()
        f0 = call_may_force_f(ConstClass(func_ptr), ptok, i1, descr=calldescr)
        guard_not_forced(descr=faildescr) [i1, f0, i0]
        finish(f0, descr=faildescr0) []
        """, locals())
        self.cpu.compile_loop(inputargs, ops, looptoken)
        frame = self.cpu.execute_token(looptoken, 20, 0)
        assert self.cpu.get_latest_descr(frame).identifier == 0
        x = self.cpu.get_finish_value_float(frame)
        assert longlong.getrealfloat(x) == 42.5
        assert values == []

        frame = self.cpu.execute_token(looptoken, 10, 1)
        assert self.cpu.get_latest_descr(frame).identifier == 1
        assert self.cpu.get_latest_value_int(frame, 0) == 1
        x = self.cpu.get_latest_value_float(frame, 1)
        assert longlong.getrealfloat(x) == 42.5
        assert self.cpu.get_latest_value_int(frame, 2) == 10
        assert values == [1, 10, frame]

    def test_force_from_finish(self):
        finishdescr = BasicFailDescr(1)
        inputargs, operations, looptoken = self.parse('''
        [i1, i2]
        p0 = jit_frame()
        finish(p0, descr=faildescr1) [i1, i2]
        ''', namespace={'faildescr1': finishdescr})
        self.cpu.compile_loop(inputargs, operations, looptoken)
        frame = self.cpu.execute_token(looptoken, 20, 0)
        self.cpu.force(frame)
        assert self.cpu.get_latest_descr(frame) is finishdescr
        assert self.cpu.get_latest_value_int(frame, 0) == 20
        assert self.cpu.get_latest_value_int(frame, 1) == 0

    def test_call_to_c_function(self):
        from pypy.rlib.libffi import CDLL, types, ArgChain, FUNCFLAG_CDECL
        from pypy.rpython.lltypesystem.ll2ctypes import libc_name
        libc = CDLL(libc_name)
        c_tolower = libc.getpointer('tolower', [types.uchar], types.sint)
        argchain = ArgChain().arg(ord('A'))
        assert c_tolower.call(argchain, rffi.INT) == ord('a')

        cpu = self.cpu
        func_adr = c_tolower.funcsym
        calldescr = cpu._calldescr_dynamic_for_tests([types.uchar], types.sint)
        faildescr = BasicFailDescr(1)
        faildescr0 = BasicFailDescr(0)
        inputargs, operations, looptoken = self.parse("""
        [i1]
        i2 = call_release_gil_i(ConstClass(func_adr), i1, descr=calldescr)
        guard_not_forced(descr=faildescr) [i1, i2]
        finish(i2, descr=faildescr0) []
        """, locals())
        self.cpu.compile_loop(inputargs, operations, looptoken)
        frame = self.cpu.execute_token(looptoken, ord('G'))
        assert self.cpu.get_latest_descr(frame).identifier == 0
        assert self.cpu.get_finish_value_int(frame) == ord('g')

    def test_call_to_c_function_with_callback(self):
        from pypy.rlib.libffi import CDLL, types, ArgChain, clibffi
        from pypy.rpython.lltypesystem.ll2ctypes import libc_name
        libc = CDLL(libc_name)
        types_size_t = clibffi.cast_type_to_ffitype(rffi.SIZE_T)
        c_qsort = libc.getpointer('qsort', [types.pointer, types_size_t,
                                            types_size_t, types.pointer],
                                  types.void)
        class Glob(object):
            pass
        glob = Glob()
        class X(object):
            pass
        #
        def callback(p1, p2):
            glob.lst.append(X())
            return rffi.cast(rffi.INT, 1)
        CALLBACK = lltype.Ptr(lltype.FuncType([lltype.Signed,
                                               lltype.Signed], rffi.INT))
        fn = llhelper(CALLBACK, callback)
        S = lltype.Struct('S', ('x', rffi.INT), ('y', rffi.INT))
        raw = lltype.malloc(S, flavor='raw')
        argchain = ArgChain()
        argchain = argchain.arg(rffi.cast(lltype.Signed, raw))
        argchain = argchain.arg(rffi.cast(rffi.SIZE_T, 2))
        argchain = argchain.arg(rffi.cast(rffi.SIZE_T, 4))
        argchain = argchain.arg(rffi.cast(lltype.Signed, fn))
        glob.lst = []
        c_qsort.call(argchain, lltype.Void)
        assert len(glob.lst) > 0
        del glob.lst[:]

        cpu = self.cpu
        func_ptr = c_qsort.funcsym
        calldescr = cpu._calldescr_dynamic_for_tests(
            [types.pointer, types_size_t, types_size_t, types.pointer],
            types.void)
        faildescr = BasicFailDescr(1)
        faildescr0 = BasicFailDescr(0)
        inputargs, ops, looptoken = self.parse("""
        [i0, i1, i2, i3]
        call_release_gil_v(ConstClass(func_ptr), i0, i1, i2, i3, descr=calldescr)
        guard_not_forced(descr=faildescr) []
        finish(descr=faildescr0)
        """, locals())
        self.cpu.compile_loop(inputargs, ops, looptoken)
        args = [rffi.cast(lltype.Signed, raw),
                2,
                4,
                rffi.cast(lltype.Signed, fn)]
        assert glob.lst == []
        frame = self.cpu.execute_token(looptoken, *args)
        assert self.cpu.get_latest_descr(frame).identifier == 0
        assert len(glob.lst) > 0
        lltype.free(raw, flavor='raw')

    def test_call_to_winapi_function(self):
        from pypy.rlib.clibffi import _WIN32, FUNCFLAG_STDCALL
        if not _WIN32:
            py.test.skip("Windows test only")
        from pypy.rlib.libffi import CDLL, types, ArgChain
        from pypy.rlib.rwin32 import DWORD
        libc = CDLL('KERNEL32')
        c_GetCurrentDir = libc.getpointer('GetCurrentDirectoryA',
                                          [types.ulong, types.pointer],
                                          types.ulong)

        cwd = os.getcwd()
        buflen = len(cwd) + 10
        buffer = lltype.malloc(rffi.CCHARP.TO, buflen, flavor='raw')
        argchain = ArgChain().arg(rffi.cast(DWORD, buflen)).arg(buffer)
        res = c_GetCurrentDir.call(argchain, DWORD)
        assert rffi.cast(lltype.Signed, res) == len(cwd)
        assert rffi.charp2strn(buffer, buflen) == cwd
        lltype.free(buffer, flavor='raw')

        cpu = self.cpu
        func_adr = llmemory.cast_ptr_to_adr(c_GetCurrentDir.funcsym)
        funcbox = ConstInt(heaptracker.adr2int(func_adr))
        calldescr = cpu._calldescr_dynamic_for_tests(
            [types.ulong, types.pointer],
            types.ulong,
            abiname='FFI_STDCALL')
        i1 = boxint()
        i2 = boxint()
        faildescr = BasicFailDescr(1)
        # if the stdcall convention is ignored, then ESP is wrong after the
        # call: 8 bytes too much.  If we repeat the call often enough, crash.
        ops = []
        for i in range(50):
            i3 = boxint()
            ops += [
                ResOperation(rop.CALL_RELEASE_GIL, [funcbox, i1, i2], i3,
                             descr=calldescr),
                ResOperation(rop.GUARD_NOT_FORCED, [], None, descr=faildescr),
                ]
            ops[-1].setfailargs([])
        ops += [
            ResOperation(rop.FINISH, [i3], None, descr=BasicFailDescr(0))
        ]
        looptoken = JitCellToken()
        self.cpu.compile_loop([i1, i2], ops, looptoken)

        buffer = lltype.malloc(rffi.CCHARP.TO, buflen, flavor='raw')
        args = [buflen, rffi.cast(lltype.Signed, buffer)]
        frame = self.cpu.execute_token(looptoken, *args)
        assert self.cpu.get_latest_descr(frame).identifier == 0
        assert self.cpu.get_finish_value_int(frame) == len(cwd)
        assert rffi.charp2strn(buffer, buflen) == cwd
        lltype.free(buffer, flavor='raw')

    def test_guard_not_invalidated(self):
        cpu = self.cpu
        faildescr = BasicFailDescr(1)
        faildescr0 = BasicFailDescr(0)
        inputargs, ops, looptoken = self.parse("""
        [i0, i1]
        guard_not_invalidated(descr=faildescr) [i1]
        finish(i0, descr=faildescr0)
        """, locals())
        self.cpu.compile_loop(inputargs, ops, looptoken)

        frame = self.cpu.execute_token(looptoken, -42, 9)
        assert self.cpu.get_latest_descr(frame).identifier == 0
        assert self.cpu.get_finish_value_int(frame) == -42
        print 'step 1 ok'
        print '-'*79

        # mark as failing
        self.cpu.invalidate_loop(looptoken)

        frame = self.cpu.execute_token(looptoken, -42, 9)
        assert self.cpu.get_latest_descr(frame) is faildescr
        assert self.cpu.get_latest_value_int(frame, 0) == 9
        print 'step 2 ok'
        print '-'*79

        # attach a bridge
        faildescr2 = BasicFailDescr(2)
        faildescr3 = BasicFailDescr(3)
        inputargs, ops, _ = self.parse("""
        [i2]
        guard_not_invalidated(descr=faildescr2) []
        finish(i2, descr=faildescr3)
        """, locals())
        self.cpu.compile_bridge(faildescr, inputargs, ops, looptoken)

        frame = self.cpu.execute_token(looptoken, -42, 9)
        assert self.cpu.get_latest_descr(frame).identifier == 3
        assert self.cpu.get_finish_value_int(frame) == 9
        print 'step 3 ok'
        print '-'*79

        # mark as failing again
        self.cpu.invalidate_loop(looptoken)

        frame = self.cpu.execute_token(looptoken, -42, 9)
        assert self.cpu.get_latest_descr(frame) is faildescr2
        print 'step 4 ok'
        print '-'*79

    def test_guard_not_invalidated_and_label(self):
        # test that the guard_not_invalidated reserves enough room before
        # the label.  If it doesn't, then in this example after we invalidate
        # the guard, jumping to the label will hit the invalidation code too
        faildescr = BasicFailDescr(1)
        labeldescr = TargetToken()
        faildescr3 = BasicFailDescr(3)
        inputargs, ops, looptoken = self.parse("""
        [i0]
        guard_not_invalidated(descr=faildescr) []
        label(i0, descr=labeldescr)
        finish(i0, descr=faildescr3)
        """, locals())
        self.cpu.compile_loop(inputargs, ops, looptoken)
        # mark as failing
        self.cpu.invalidate_loop(looptoken)
        # attach a bridge
        ops = [
            create_resop(rop.JUMP, None, [ConstInt(333)], descr=labeldescr),
        ]
        self.cpu.compile_bridge(faildescr, [], ops, looptoken)
        # run: must not be caught in an infinite loop
        frame = self.cpu.execute_token(looptoken, 16)
        assert self.cpu.get_latest_descr(frame).identifier == 3
        assert self.cpu.get_finish_value_int(frame) == 333

    # pure do_ / descr features

    def test_do_operations(self):
        cpu = self.cpu
        #
        A = lltype.GcArray(lltype.Char)
        descr_A = cpu.arraydescrof(A)
        a = lltype.malloc(A, 5)
        x = cpu.bh_arraylen_gc(lltype.cast_opaque_ptr(llmemory.GCREF, a),
                               descr_A)
        assert x == 5
        #
        a[2] = 'Y'
        x = cpu.bh_getarrayitem_gc_i(
            lltype.cast_opaque_ptr(llmemory.GCREF, a), 2, descr_A)
        assert x == ord('Y')
        #
        B = lltype.GcArray(lltype.Ptr(A))
        descr_B = cpu.arraydescrof(B)
        b = lltype.malloc(B, 4)
        b[3] = a
        x = cpu.bh_getarrayitem_gc_r(
            lltype.cast_opaque_ptr(llmemory.GCREF, b), 3, descr_B)
        assert lltype.cast_opaque_ptr(lltype.Ptr(A), x) == a
        if self.cpu.supports_floats:
            C = lltype.GcArray(lltype.Float)
            c = lltype.malloc(C, 6)
            c[3] = 3.5
            descr_C = cpu.arraydescrof(C)
            x = cpu.bh_getarrayitem_gc_f(
                lltype.cast_opaque_ptr(llmemory.GCREF, c), 3, descr_C)
            assert longlong.getrealfloat(x) == 3.5
            cpu.bh_setarrayitem_gc_f(
                lltype.cast_opaque_ptr(llmemory.GCREF, c), 4,
                longlong.getfloatstorage(4.5), descr_C)
            assert c[4] == 4.5
        s = rstr.mallocstr(6)
        x = cpu.bh_strlen(lltype.cast_opaque_ptr(llmemory.GCREF, s))
        assert x == 6
        #
        s.chars[3] = 'X'
        x = cpu.bh_strgetitem(lltype.cast_opaque_ptr(llmemory.GCREF, s), 3)
        assert x == ord('X')
        #
        S = lltype.GcStruct('S', ('x', lltype.Char), ('y', lltype.Ptr(A)),
                            ('z', lltype.Float))
        descrfld_x = cpu.fielddescrof(S, 'x')
        s = lltype.malloc(S)
        s.x = 'Z'
        x = cpu.bh_getfield_gc_i(lltype.cast_opaque_ptr(llmemory.GCREF, s),
                                 descrfld_x)
        assert x == ord('Z')
        #
        cpu.bh_setfield_gc_i(lltype.cast_opaque_ptr(llmemory.GCREF, s),
                             ord('4'), descrfld_x)
        assert s.x == '4'
        #
        descrfld_y = cpu.fielddescrof(S, 'y')
        s.y = a
        x = cpu.bh_getfield_gc_r(lltype.cast_opaque_ptr(llmemory.GCREF, s),
                                 descrfld_y)
        assert lltype.cast_opaque_ptr(lltype.Ptr(A), x) == a
        #
        s.y = lltype.nullptr(A)
        cpu.bh_setfield_gc_r(lltype.cast_opaque_ptr(llmemory.GCREF, s),
                             x, descrfld_y)
        assert s.y == a
        #
        RS = lltype.Struct('S', ('x', lltype.Char))  #, ('y', lltype.Ptr(A)))
        descrfld_rx = cpu.fielddescrof(RS, 'x')
        rs = lltype.malloc(RS, immortal=True)
        rs.x = '?'
        x = cpu.bh_getfield_raw_i(
            heaptracker.adr2int(llmemory.cast_ptr_to_adr(rs)),
            descrfld_rx)
        assert x == ord('?')
        #
        cpu.bh_setfield_raw_i(
            heaptracker.adr2int(llmemory.cast_ptr_to_adr(rs)),
            ord('!'), descrfld_rx)
        assert rs.x == '!'
        #
        if self.cpu.supports_floats:
            descrfld_z = cpu.fielddescrof(S, 'z')
            cpu.bh_setfield_gc_f(
                lltype.cast_opaque_ptr(llmemory.GCREF, s),
                longlong.getfloatstorage(3.5), descrfld_z)
            assert s.z == 3.5
            s.z = 3.2
            x = cpu.bh_getfield_gc_f(
                lltype.cast_opaque_ptr(llmemory.GCREF, s),
                descrfld_z)
            assert longlong.getrealfloat(x) == 3.2
        ### we don't support in the JIT for now GC pointers
        ### stored inside non-GC structs.
        #descrfld_ry = cpu.fielddescrof(RS, 'y')
        #rs.y = a
        #x = cpu.do_getfield_raw(
        #    boxint(cpu.cast_adr_to_int(llmemory.cast_ptr_to_adr(rs))),
        #    descrfld_ry)
        #assert isinstance(x, boxptr)
        #assert x.getref(lltype.Ptr(A)) == a
        #
        #rs.y = lltype.nullptr(A)
        #cpu.do_setfield_raw(
        #    boxint(cpu.cast_adr_to_int(llmemory.cast_ptr_to_adr(rs))), x,
        #    descrfld_ry)
        #assert rs.y == a
        #
        descrsize = cpu.sizeof(S)
        x = cpu.bh_new(descrsize)
        lltype.cast_opaque_ptr(lltype.Ptr(S), x)    # type check
        #
        descrsize2 = cpu.sizeof(rclass.OBJECT)
        vtable2 = lltype.malloc(rclass.OBJECT_VTABLE, immortal=True)
        vtable2_int = heaptracker.adr2int(llmemory.cast_ptr_to_adr(vtable2))
        heaptracker.register_known_gctype(cpu, vtable2, rclass.OBJECT)
        x = cpu.bh_new_with_vtable(vtable2_int, descrsize2)
        lltype.cast_opaque_ptr(lltype.Ptr(rclass.OBJECT), x)    # type check
        # well...
        #assert x.getref(rclass.OBJECTPTR).typeptr == vtable2
        #
        arraydescr = cpu.arraydescrof(A)
        x = cpu.bh_new_array(7, arraydescr)
        array = lltype.cast_opaque_ptr(lltype.Ptr(A), x)
        assert len(array) == 7
        #
        cpu.bh_setarrayitem_gc_i(x, 5, ord('*'), descr_A)
        assert array[5] == '*'
        #
        cpu.bh_setarrayitem_gc_r(
            lltype.cast_opaque_ptr(llmemory.GCREF, b), 1, x, descr_B)
        assert b[1] == array
        #
        x = cpu.bh_newstr(5)
        str = lltype.cast_opaque_ptr(lltype.Ptr(rstr.STR), x)
        assert len(str.chars) == 5
        #
        cpu.bh_strsetitem(x, 4, ord('/'))
        assert str.chars[4] == '/'

    def test_sorting_of_fields(self):
        S = lltype.GcStruct('S', ('parent', rclass.OBJECT),
                                  ('value', lltype.Signed),
                                  ('chr1', lltype.Char),
                                  ('chr2', lltype.Char))
        chr1 = self.cpu.fielddescrof(S, 'chr1').sort_key()
        value = self.cpu.fielddescrof(S, 'value').sort_key()
        chr2 = self.cpu.fielddescrof(S, 'chr2').sort_key()
        assert len(set([value, chr1, chr2])) == 3

    def test_guards_nongc(self):
        x = lltype.malloc(lltype.Struct('x'), flavor='raw')
        v = heaptracker.adr2int(llmemory.cast_ptr_to_adr(x))
        vbox = boxint(v)
        ops = [
            (rop.GUARD_NONNULL, vbox, False),
            (rop.GUARD_ISNULL, vbox, True),
            (rop.GUARD_NONNULL, boxint(0), True),
            (rop.GUARD_ISNULL, boxint(0), False),
            ]
        for opname, arg, res in ops:
            self.execute_operation(opname, [arg], 'void')
            assert self.guard_failed == res

        lltype.free(x, flavor='raw')

    def test_assembler_call(self):
        called = []
        def assembler_helper(jitframe):
            faildescr = self.cpu.get_latest_descr(jitframe)
            failindex = self.cpu.get_fail_descr_number(faildescr)
            called.append(failindex)
            return 4 + 9

        FUNCPTR = lltype.Ptr(lltype.FuncType([llmemory.GCREF],
                                             lltype.Signed))
        class FakeJitDriverSD:
            _assembler_helper_ptr = llhelper(FUNCPTR, assembler_helper)
            assembler_helper_adr = llmemory.cast_ptr_to_adr(
                _assembler_helper_ptr)

        # ensure the fail_descr_number is not zero
        for _ in range(10):
            self.cpu.reserve_some_free_fail_descr_number()
        ops = '''
        [i0, i1, i2, i3, i4, i5, i6, i7, i8, i9]
        i10 = int_add_ovf(i0, i1)
        guard_no_overflow(descr=faildescr2) []
        i11 = int_add(i10, i2)
        i12 = int_add(i11, i3)
        i13 = int_add(i12, i4)
        i14 = int_add(i13, i5)
        i15 = int_add(i14, i6)
        i16 = int_add(i15, i7)
        i17 = int_add(i16, i8)
        i18 = int_add(i17, i9)
        finish(i18, descr=faildescr1) []'''
        inputargs, operations, looptoken = self.parse(
            ops, namespace={'faildescr1': BasicFailDescr(1)})
        operations[-1].getdescr().fast_path_done = True
        looptoken.outermost_jitdriver_sd = FakeJitDriverSD()
        fail_number = self.cpu.get_fail_descr_number(
            operations[1].getdescr())
        self.cpu.compile_loop(inputargs, operations, looptoken)
        ARGS = [lltype.Signed] * 10
        RES = lltype.Signed
        FakeJitDriverSD.portal_calldescr = self.cpu.calldescrof(
            lltype.Ptr(lltype.FuncType(ARGS, RES)), ARGS, RES,
            EffectInfo.MOST_GENERAL)
        args = [i+1 for i in range(10)]
        frame = self.cpu.execute_token(looptoken, *args)
        assert self.cpu.get_finish_value_int(frame) == 55
        ops = '''
        [i0, i1, i2, i3, i4, i5, i6, i7, i8, i9]
        i10 = int_add(i0, 42)
        i11 = call_assembler_i(i10, i1, i2, i3, i4, i5, i6, i7, i8, i9, descr=looptoken)
        guard_not_forced(descr=faildescr1)[]
        finish(i11, descr=faildescr2) []
        '''
        faildescr1 = BasicFailDescr(1)
        faildescr2 = BasicFailDescr(2)
        otherargs, otheroperations, othertoken = self.parse(
            ops, namespace=locals())

        # test the fast path, which should not call assembler_helper()
        self.cpu.compile_loop(otherargs, otheroperations, othertoken)
        args = [i+1 for i in range(10)]
        frame = self.cpu.execute_token(othertoken, *args)
        res = self.cpu.get_finish_value_int(frame)
        assert res == 97
        assert called == []

        # test the slow path, going via assembler_helper()
        args[1] = sys.maxint
        frame = self.cpu.execute_token(othertoken, *args)
        assert self.cpu.get_finish_value_int(frame) == 13
        assert called == [fail_number]

    def test_assembler_call_float(self):
        if not self.cpu.supports_floats:
            py.test.skip("requires floats")
        called = []
        def assembler_helper(jitframe):
            faildescr = self.cpu.get_latest_descr(jitframe)
            failindex = self.cpu.get_fail_descr_number(faildescr)
            called.append(failindex)
            return 13.5

        FUNCPTR = lltype.Ptr(lltype.FuncType([llmemory.GCREF],
                                             lltype.Float))
        class FakeJitDriverSD:
            _assembler_helper_ptr = llhelper(FUNCPTR, assembler_helper)
            assembler_helper_adr = llmemory.cast_ptr_to_adr(
                _assembler_helper_ptr)

        ARGS = [lltype.Float, lltype.Float]
        RES = lltype.Float
        FakeJitDriverSD.portal_calldescr = self.cpu.calldescrof(
            lltype.Ptr(lltype.FuncType(ARGS, RES)), ARGS, RES,
            EffectInfo.MOST_GENERAL)
        for _ in range(10):
            self.cpu.reserve_some_free_fail_descr_number()
        ops = '''
        [f0, f1]
        i0 = float_eq(f0, -1.0)
        guard_false(i0, descr=faildescr3) []
        f2 = float_add(f0, f1)
        finish(f2, descr=faildescr) []'''
        inputargs, operations, looptoken = self.parse(
            ops, namespace={'faildescr': BasicFailDescr(1)})
        operations[-1].getdescr().fast_path_done = True
        fail_number = self.cpu.get_fail_descr_number(
            operations[1].getdescr())
        looptoken.outermost_jitdriver_sd = FakeJitDriverSD()
        self.cpu.compile_loop(inputargs, operations, looptoken)
        args = [longlong.getfloatstorage(1.2),
                longlong.getfloatstorage(2.3)]
        frame = self.cpu.execute_token(looptoken, *args)
        x = self.cpu.get_finish_value_float(frame)
        assert longlong.getrealfloat(x) == 1.2 + 2.3
        ops = '''
        [f4, f5]
        f3 = call_assembler_f(f4, f5, descr=looptoken)
        guard_not_forced(descr=faildescr1)[]
        finish(f3, descr=faildescr2) []
        '''
        faildescr1 = BasicFailDescr(1)
        faildescr2 = BasicFailDescr(2)
        inputargs, operations, othertoken = self.parse(ops, namespace=locals())
        self.cpu.compile_loop(inputargs, operations, othertoken)

        # test the fast path, which should not call assembler_helper()
        args = [longlong.getfloatstorage(1.2),
                longlong.getfloatstorage(3.2)]
        frame = self.cpu.execute_token(othertoken, *args)
        x = self.cpu.get_finish_value_float(frame)
        assert longlong.getrealfloat(x) == 1.2 + 3.2
        assert called == []

        # test the slow path, going via assembler_helper()
        args[0] = longlong.getfloatstorage(-1.0)
        frame = self.cpu.execute_token(othertoken, *args)
        x = self.cpu.get_finish_value_float(frame)
        assert longlong.getrealfloat(x) == 13.5
        assert called == [fail_number]

    def test_assembler_call_get_latest_descr(self):
        called = []
        def assembler_helper(jitframe):
            jitframe1 = self.cpu.get_finish_value_ref(jitframe)
            called.append(self.cpu.get_latest_descr(jitframe1))
            return lltype.nullptr(llmemory.GCREF.TO)

        FUNCPTR = lltype.Ptr(lltype.FuncType([llmemory.GCREF],
                                             llmemory.GCREF))

        def func2(jitframe1):
            called.append(self.cpu.get_latest_descr(jitframe1))
        FPTR2 = lltype.Ptr(lltype.FuncType([llmemory.GCREF], lltype.Void))
        fptr2 = llhelper(FPTR2, func2)
        calldescr2 = self.cpu.calldescrof(FPTR2.TO, FPTR2.TO.ARGS,
                                          FPTR2.TO.RESULT,
                                          EffectInfo.MOST_GENERAL)

        class FakeJitDriverSD:
            _assembler_helper_ptr = llhelper(FUNCPTR, assembler_helper)
            assembler_helper_adr = llmemory.cast_ptr_to_adr(
                _assembler_helper_ptr)

        ops = '''
        [p0]
        call_v(ConstClass(fptr2), p0, descr=calldescr2)
        finish(p0, descr=faildescr1) []'''
        inputargs, operations, looptoken = self.parse(ops, namespace=locals())
        # not a fast_path finish!
        looptoken.outermost_jitdriver_sd = FakeJitDriverSD()
        self.cpu.compile_loop(inputargs, operations, looptoken)
        ARGS = [llmemory.GCREF]
        RES = llmemory.GCREF
        FakeJitDriverSD.portal_calldescr = self.cpu.calldescrof(
            lltype.Ptr(lltype.FuncType(ARGS, RES)), ARGS, RES,
            EffectInfo.MOST_GENERAL)

        foodescr = BasicFailDescr(66)
        ops = '''
        []
        p0 = jit_frame()
        p1 = call_assembler_r(p0, descr=looptoken)
        guard_not_forced(descr=foodescr) []
        finish(descr=faildescr2) []
        '''
        inputargs, operations, othertoken = self.parse(ops, namespace=locals())
        self.cpu.compile_loop(inputargs, operations, othertoken)
        
        frame = self.cpu.execute_token(othertoken)
        assert not self.cpu.get_finish_value_ref(frame)
        assert called == [foodescr] * 2

    def test_raw_malloced_getarrayitem(self):
        ARRAY = rffi.CArray(lltype.Signed)
        descr = self.cpu.arraydescrof(ARRAY)
        a = lltype.malloc(ARRAY, 10, flavor='raw')
        a[7] = -4242
        addr = llmemory.cast_ptr_to_adr(a)
        abox = boxint(heaptracker.adr2int(addr))
        r1 = self.execute_operation(rop.GETARRAYITEM_RAW_i, [abox, boxint(7)],
                                    'int', descr=descr)
        assert r1 == -4242
        lltype.free(a, flavor='raw')

    def test_raw_malloced_setarrayitem(self):
        ARRAY = rffi.CArray(lltype.Signed)
        descr = self.cpu.arraydescrof(ARRAY)
        a = lltype.malloc(ARRAY, 10, flavor='raw')
        addr = llmemory.cast_ptr_to_adr(a)
        abox = boxint(heaptracker.adr2int(addr))
        self.execute_operation(rop.SETARRAYITEM_RAW, [abox, boxint(5),
                                                      boxint(12345)],
                               'void', descr=descr)
        assert a[5] == 12345
        lltype.free(a, flavor='raw')

    def test_redirect_call_assembler(self):
        if not self.cpu.supports_floats:
            py.test.skip("requires floats")
        called = []
        def assembler_helper(jitframe):
            faildescr =self.cpu.get_latest_descr(jitframe)
            failindex = self.cpu.get_fail_descr_number(faildescr)
            called.append(failindex)
            return 13.5

        FUNCPTR = lltype.Ptr(lltype.FuncType([llmemory.GCREF],
                                             lltype.Float))
        class FakeJitDriverSD:
            _assembler_helper_ptr = llhelper(FUNCPTR, assembler_helper)
            assembler_helper_adr = llmemory.cast_ptr_to_adr(
                _assembler_helper_ptr)

        ARGS = [lltype.Float, lltype.Float]
        RES = lltype.Float
        FakeJitDriverSD.portal_calldescr = self.cpu.calldescrof(
            lltype.Ptr(lltype.FuncType(ARGS, RES)), ARGS, RES,
            EffectInfo.MOST_GENERAL)
        for _ in range(10):
            self.cpu.reserve_some_free_fail_descr_number()
        ops = '''
        [f0, f1]
        i0 = float_eq(f0, -1.0)
        guard_false(i0, descr=faildescr2) []
        f2 = float_add(f0, f1)
        finish(f2, descr=faildescr1) []'''
        inputargs, operations, looptoken = self.parse(
            ops, namespace={'faildescr1': BasicFailDescr(1)})
        operations[-1].getdescr().fast_path_done = True
        looptoken.outermost_jitdriver_sd = FakeJitDriverSD()
        self.cpu.compile_loop(inputargs, operations, looptoken)
        fail_number = self.cpu.get_fail_descr_number(
            operations[1].getdescr())
        args = [longlong.getfloatstorage(1.25),
                longlong.getfloatstorage(2.35)]
        frame = self.cpu.execute_token(looptoken, *args)
        x = self.cpu.get_finish_value_float(frame)
        assert longlong.getrealfloat(x) == 1.25 + 2.35
        assert not called

        ops = '''
        [f4, f5]
        f3 = call_assembler_f(f4, f5, descr=looptoken)
        guard_not_forced(descr=faildescr1)[]
        finish(f3, descr=faildescr2) []
        '''
        faildescr2 = BasicFailDescr(2)
        faildescr1 = BasicFailDescr(1)
        inputargs, operations, othertoken = self.parse(ops, namespace=locals())
        self.cpu.compile_loop(inputargs, operations, othertoken)

        # normal call_assembler: goes to looptoken
        args = [longlong.getfloatstorage(1.25),
                longlong.getfloatstorage(3.25)]
        frame = self.cpu.execute_token(othertoken, *args)
        x = self.cpu.get_finish_value_float(frame)
        assert longlong.getrealfloat(x) == 1.25 + 3.25
        assert called == []

        args[0] = longlong.getfloatstorage(-1.0)
        frame = self.cpu.execute_token(othertoken, *args)
        x = self.cpu.get_finish_value_float(frame)
        assert longlong.getrealfloat(x) == 13.5
        assert called == [fail_number]
        del called[:]

        # compile a replacement
        ops2 = '''
        [f0, f1]
        i0 = float_eq(f0, -2.0)
        guard_false(i0, descr=faildescr3) []
        f2 = float_sub(f0, f1)
        finish(f2, descr=faildescr) []'''
        inputargs2, operations2, looptoken2 = self.parse(
            ops2, namespace={'faildescr': BasicFailDescr(1)})
        operations2[-1].getdescr().fast_path_done = True
        looptoken2.outermost_jitdriver_sd = FakeJitDriverSD()
        self.cpu.compile_loop(inputargs2, operations2, looptoken2)
        fail_number = self.cpu.get_fail_descr_number(
            operations2[1].getdescr())

        # install it
        self.cpu.redirect_call_assembler(looptoken, looptoken2)

        # now, our call_assembler should go to looptoken2
        args = [longlong.getfloatstorage(116.0),
                longlong.getfloatstorage(1.5)]
        frame = self.cpu.execute_token(othertoken, *args)
        x = self.cpu.get_finish_value_float(frame)
        assert longlong.getrealfloat(x) == 116.0 - 1.5
        assert called == []

        args[0] = longlong.getfloatstorage(-2.0)
        frame = self.cpu.execute_token(othertoken, *args)
        x = self.cpu.get_finish_value_float(frame)
        assert longlong.getrealfloat(x) == 13.5
        assert called == [fail_number]

    def test_short_result_of_getfield_direct(self):
        # Test that a getfield that returns a CHAR, SHORT or INT, signed
        # or unsigned, properly gets zero-extended or sign-extended.
        # Direct bh_xxx test.
        cpu = self.cpu
        for RESTYPE in [rffi.SIGNEDCHAR, rffi.UCHAR,
                        rffi.SHORT, rffi.USHORT,
                        rffi.INT, rffi.UINT,
                        rffi.LONG, rffi.ULONG]:
            S = lltype.GcStruct('S', ('x', RESTYPE))
            descrfld_x = cpu.fielddescrof(S, 'x')
            s = lltype.malloc(S)
            value = intmask(0xFFEEDDCCBBAA9988)
            expected = rffi.cast(lltype.Signed, rffi.cast(RESTYPE, value))
            s.x = rffi.cast(RESTYPE, value)
            x = cpu.bh_getfield_gc_i(lltype.cast_opaque_ptr(llmemory.GCREF, s),
                                     descrfld_x)
            assert x == expected, (
                "%r: got %r, expected %r" % (RESTYPE, x, expected))

    def test_short_result_of_getfield_compiled(self):
        # Test that a getfield that returns a CHAR, SHORT or INT, signed
        # or unsigned, properly gets zero-extended or sign-extended.
        # Machine code compilation test.
        cpu = self.cpu
        for RESTYPE in [rffi.SIGNEDCHAR, rffi.UCHAR,
                        rffi.SHORT, rffi.USHORT,
                        rffi.INT, rffi.UINT,
                        rffi.LONG, rffi.ULONG]:
            S = lltype.GcStruct('S', ('x', RESTYPE))
            descrfld_x = cpu.fielddescrof(S, 'x')
            s = lltype.malloc(S)
            value = intmask(0xFFEEDDCCBBAA9988)
            expected = rffi.cast(lltype.Signed, rffi.cast(RESTYPE, value))
            s.x = rffi.cast(RESTYPE, value)
            s_gcref = lltype.cast_opaque_ptr(llmemory.GCREF, s)
            res = self.execute_operation(rop.GETFIELD_GC_i, [boxptr(s_gcref)],
                                         'int', descr=descrfld_x)
            assert res == expected, (
                "%r: got %r, expected %r" % (RESTYPE, res.value, expected))

    def test_short_result_of_getarrayitem_direct(self):
        # Test that a getarrayitem that returns a CHAR, SHORT or INT, signed
        # or unsigned, properly gets zero-extended or sign-extended.
        # Direct bh_xxx test.
        cpu = self.cpu
        for RESTYPE in [rffi.SIGNEDCHAR, rffi.UCHAR,
                        rffi.SHORT, rffi.USHORT,
                        rffi.INT, rffi.UINT,
                        rffi.LONG, rffi.ULONG]:
            A = lltype.GcArray(RESTYPE)
            descrarray = cpu.arraydescrof(A)
            a = lltype.malloc(A, 5)
            value = intmask(0xFFEEDDCCBBAA9988)
            expected = rffi.cast(lltype.Signed, rffi.cast(RESTYPE, value))
            a[3] = rffi.cast(RESTYPE, value)
            x = cpu.bh_getarrayitem_gc_i(
                lltype.cast_opaque_ptr(llmemory.GCREF, a), 3, descrarray)
            assert x == expected, (
                "%r: got %r, expected %r" % (RESTYPE, x, expected))

    def test_short_result_of_getarrayitem_compiled(self):
        # Test that a getarrayitem that returns a CHAR, SHORT or INT, signed
        # or unsigned, properly gets zero-extended or sign-extended.
        # Machine code compilation test.
        cpu = self.cpu
        for RESTYPE in [rffi.SIGNEDCHAR, rffi.UCHAR,
                        rffi.SHORT, rffi.USHORT,
                        rffi.INT, rffi.UINT,
                        rffi.LONG, rffi.ULONG]:
            A = lltype.GcArray(RESTYPE)
            descrarray = cpu.arraydescrof(A)
            a = lltype.malloc(A, 5)
            value = intmask(0xFFEEDDCCBBAA9988)
            expected = rffi.cast(lltype.Signed, rffi.cast(RESTYPE, value))
            a[3] = rffi.cast(RESTYPE, value)
            a_gcref = lltype.cast_opaque_ptr(llmemory.GCREF, a)
            res = self.execute_operation(rop.GETARRAYITEM_GC_i,
                                         [boxptr(a_gcref), boxint(3)],
                                         'int', descr=descrarray)
            assert res == expected, (
                "%r: got %r, expected %r" % (RESTYPE, res.value, expected))

    def test_short_result_of_getarrayitem_raw_direct(self):
        # Test that a getarrayitem that returns a CHAR, SHORT or INT, signed
        # or unsigned, properly gets zero-extended or sign-extended.
        # Direct bh_xxx test.
        cpu = self.cpu
        for RESTYPE in [rffi.SIGNEDCHAR, rffi.UCHAR,
                        rffi.SHORT, rffi.USHORT,
                        rffi.INT, rffi.UINT,
                        rffi.LONG, rffi.ULONG]:
            A = rffi.CArray(RESTYPE)
            descrarray = cpu.arraydescrof(A)
            a = lltype.malloc(A, 5, flavor='raw')
            value = intmask(0xFFEEDDCCBBAA9988)
            expected = rffi.cast(lltype.Signed, rffi.cast(RESTYPE, value))
            a[3] = rffi.cast(RESTYPE, value)
            a_rawint = heaptracker.adr2int(llmemory.cast_ptr_to_adr(a))
            x = cpu.bh_getarrayitem_raw_i(a_rawint, 3, descrarray)
            assert x == expected, (
                "%r: got %r, expected %r" % (RESTYPE, x, expected))
            lltype.free(a, flavor='raw')

    def test_short_result_of_getarrayitem_raw_compiled(self):
        # Test that a getarrayitem that returns a CHAR, SHORT or INT, signed
        # or unsigned, properly gets zero-extended or sign-extended.
        # Machine code compilation test.
        cpu = self.cpu
        for RESTYPE in [rffi.SIGNEDCHAR, rffi.UCHAR,
                        rffi.SHORT, rffi.USHORT,
                        rffi.INT, rffi.UINT,
                        rffi.LONG, rffi.ULONG]:
            A = rffi.CArray(RESTYPE)
            descrarray = cpu.arraydescrof(A)
            a = lltype.malloc(A, 5, flavor='raw')
            value = intmask(0xFFEEDDCCBBAA9988)
            expected = rffi.cast(lltype.Signed, rffi.cast(RESTYPE, value))
            a[3] = rffi.cast(RESTYPE, value)
            a_rawint = heaptracker.adr2int(llmemory.cast_ptr_to_adr(a))
            res = self.execute_operation(rop.GETARRAYITEM_RAW_i,
                                         [boxint(a_rawint), boxint(3)],
                                         'int', descr=descrarray)
            assert res == expected, (
                "%r: got %r, expected %r" % (RESTYPE, res.value, expected))
            lltype.free(a, flavor='raw')

    def test_short_result_of_call_direct(self):
        # Test that calling a function that returns a CHAR, SHORT or INT,
        # signed or unsigned, properly gets zero-extended or sign-extended.
        from pypy.translator.tool.cbuild import ExternalCompilationInfo
        for RESTYPE in [rffi.SIGNEDCHAR, rffi.UCHAR,
                        rffi.SHORT, rffi.USHORT,
                        rffi.INT, rffi.UINT,
                        rffi.LONG, rffi.ULONG]:
            # Tested with a function that intentionally does not cast the
            # result to RESTYPE, but makes sure that we return the whole
            # value in eax or rax.
            eci = ExternalCompilationInfo(
                separate_module_sources=["""
                long fn_test_result_of_call(long x)
                {
                    return x + 1;
                }
                """],
                export_symbols=['fn_test_result_of_call'])
            f = rffi.llexternal('fn_test_result_of_call', [lltype.Signed],
                                RESTYPE, compilation_info=eci, _nowrapper=True)
            value = intmask(0xFFEEDDCCBBAA9988)
            expected = rffi.cast(lltype.Signed, rffi.cast(RESTYPE, value + 1))
            assert intmask(f(value)) == expected
            #
            FUNC = self.FuncType([lltype.Signed], RESTYPE)
            FPTR = self.Ptr(FUNC)
            calldescr = self.cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT,
                                             EffectInfo.MOST_GENERAL)
            x = self.cpu.bh_call_i(self.get_funcbox(self.cpu, f).value,
                                   [value], None, None, calldescr)
            assert x == expected, (
                "%r: got %r, expected %r" % (RESTYPE, x, expected))

    def test_short_result_of_call_compiled(self):
        # Test that calling a function that returns a CHAR, SHORT or INT,
        # signed or unsigned, properly gets zero-extended or sign-extended.
        from pypy.translator.tool.cbuild import ExternalCompilationInfo
        for RESTYPE in [rffi.SIGNEDCHAR, rffi.UCHAR,
                        rffi.SHORT, rffi.USHORT,
                        rffi.INT, rffi.UINT,
                        rffi.LONG, rffi.ULONG]:
            # Tested with a function that intentionally does not cast the
            # result to RESTYPE, but makes sure that we return the whole
            # value in eax or rax.
            eci = ExternalCompilationInfo(
                separate_module_sources=["""
                long fn_test_result_of_call(long x)
                {
                    return x + 1;
                }
                """],
                export_symbols=['fn_test_result_of_call'])
            f = rffi.llexternal('fn_test_result_of_call', [lltype.Signed],
                                RESTYPE, compilation_info=eci, _nowrapper=True)
            value = intmask(0xFFEEDDCCBBAA9988)
            expected = rffi.cast(lltype.Signed, rffi.cast(RESTYPE, value + 1))
            assert intmask(f(value)) == expected
            #
            FUNC = self.FuncType([lltype.Signed], RESTYPE)
            FPTR = self.Ptr(FUNC)
            calldescr = self.cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT,
                                             EffectInfo.MOST_GENERAL)
            funcbox = self.get_funcbox(self.cpu, f)
            res = self.execute_operation(rop.CALL_i, [funcbox, boxint(value)],
                                         'int', descr=calldescr)
            assert res == expected, (
                "%r: got %r, expected %r" % (RESTYPE, res.value, expected))

    def test_supports_longlong(self):
        if sys.maxint > 2147483647:
            assert not self.cpu.supports_longlong, (
                "supports_longlong should be False on 64-bit platforms")

    def test_longlong_result_of_call_direct(self):
        if not self.cpu.supports_longlong:
            py.test.skip("longlong test")
        from pypy.translator.tool.cbuild import ExternalCompilationInfo
        from pypy.rlib.rarithmetic import r_longlong
        eci = ExternalCompilationInfo(
            separate_module_sources=["""
            long long fn_test_result_of_call(long long x)
            {
                return x - 100000000000000;
            }
            """],
            export_symbols=['fn_test_result_of_call'])
        f = rffi.llexternal('fn_test_result_of_call', [lltype.SignedLongLong],
                            lltype.SignedLongLong,
                            compilation_info=eci, _nowrapper=True)
        value = r_longlong(0x7ff05af3307a3fff)
        expected = r_longlong(0x7ff000001fffffff)
        assert f(value) == expected
        #
        FUNC = self.FuncType([lltype.SignedLongLong], lltype.SignedLongLong)
        FPTR = self.Ptr(FUNC)
        calldescr = self.cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT,
                                         EffectInfo.MOST_GENERAL)
        x = self.cpu.bh_call_f(self.get_funcbox(self.cpu, f).value,
                               None, None, [value], calldescr)
        assert x == expected

    def test_longlong_result_of_call_compiled(self):
        if not self.cpu.supports_longlong:
            py.test.skip("test of longlong result")
        from pypy.translator.tool.cbuild import ExternalCompilationInfo
        from pypy.rlib.rarithmetic import r_longlong
        eci = ExternalCompilationInfo(
            separate_module_sources=["""
            long long fn_test_result_of_call(long long x)
            {
                return x - 100000000000000;
            }
            """],
            export_symbols=['fn_test_result_of_call'])
        f = rffi.llexternal('fn_test_result_of_call', [lltype.SignedLongLong],
                            lltype.SignedLongLong,
                            compilation_info=eci, _nowrapper=True)
        value = r_longlong(0x7ff05af3307a3fff)
        expected = r_longlong(0x7ff000001fffffff)
        assert f(value) == expected
        #
        FUNC = self.FuncType([lltype.SignedLongLong], lltype.SignedLongLong)
        FPTR = self.Ptr(FUNC)
        calldescr = self.cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT,
                                         EffectInfo.MOST_GENERAL)
        funcbox = self.get_funcbox(self.cpu, f)
        res = self.execute_operation(rop.CALL_f, [funcbox,
                                                  boxlonglong_on_32bit(value)],
                                     'longlong', descr=calldescr)
        assert res == expected

    def test_singlefloat_result_of_call_direct(self):
        if not self.cpu.supports_singlefloats:
            py.test.skip("singlefloat test")
        from pypy.translator.tool.cbuild import ExternalCompilationInfo
        from pypy.rlib.rarithmetic import r_singlefloat
        eci = ExternalCompilationInfo(
            separate_module_sources=["""
            float fn_test_result_of_call(float x)
            {
                return x / 2.0f;
            }
            """],
            export_symbols=['fn_test_result_of_call'])
        f = rffi.llexternal('fn_test_result_of_call', [lltype.SingleFloat],
                            lltype.SingleFloat,
                            compilation_info=eci, _nowrapper=True)
        value = r_singlefloat(-42.5)
        expected = r_singlefloat(-21.25)
        assert f(value) == expected
        #
        FUNC = self.FuncType([lltype.SingleFloat], lltype.SingleFloat)
        FPTR = self.Ptr(FUNC)
        calldescr = self.cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT,
                                         EffectInfo.MOST_GENERAL)
        ivalue = longlong.singlefloat2int(value)
        iexpected = longlong.singlefloat2int(expected)
        x = self.cpu.bh_call_i(self.get_funcbox(self.cpu, f).value,
                               [ivalue], None, None, calldescr)
        assert x == iexpected

    def test_singlefloat_result_of_call_compiled(self):
        if not self.cpu.supports_singlefloats:
            py.test.skip("test of singlefloat result")
        from pypy.translator.tool.cbuild import ExternalCompilationInfo
        from pypy.rlib.rarithmetic import r_singlefloat
        eci = ExternalCompilationInfo(
            separate_module_sources=["""
            float fn_test_result_of_call(float x)
            {
                return x / 2.0f;
            }
            """],
            export_symbols=['fn_test_result_of_call'])
        f = rffi.llexternal('fn_test_result_of_call', [lltype.SingleFloat],
                            lltype.SingleFloat,
                            compilation_info=eci, _nowrapper=True)
        value = r_singlefloat(-42.5)
        expected = r_singlefloat(-21.25)
        assert f(value) == expected
        #
        FUNC = self.FuncType([lltype.SingleFloat], lltype.SingleFloat)
        FPTR = self.Ptr(FUNC)
        calldescr = self.cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT,
                                         EffectInfo.MOST_GENERAL)
        funcbox = self.get_funcbox(self.cpu, f)
        ivalue = longlong.singlefloat2int(value)
        iexpected = longlong.singlefloat2int(expected)
        res = self.execute_operation(rop.CALL_i, [funcbox, boxint(ivalue)],
                                     'int', descr=calldescr)
        assert res == iexpected

    def test_free_loop_and_bridges(self):
        from pypy.jit.backend.llsupport.llmodel import AbstractLLCPU
        if not isinstance(self.cpu, AbstractLLCPU):
            py.test.skip("not a subclass of llmodel.AbstractLLCPU")
        if hasattr(self.cpu, 'setup_once'):
            self.cpu.setup_once()
        mem0 = self.cpu.asmmemmgr.total_mallocs
        looptoken = self.test_compile_bridge()
        mem1 = self.cpu.asmmemmgr.total_mallocs
        self.cpu.free_loop_and_bridges(looptoken.compiled_loop_token)
        mem2 = self.cpu.asmmemmgr.total_mallocs
        assert mem2 < mem1
        assert mem2 == mem0

    def test_memoryerror(self):
        excdescr = BasicFailDescr(666)
        self.cpu.propagate_exception_v = self.cpu.get_fail_descr_number(
            excdescr)
        self.cpu.setup_once()    # xxx redo it, because we added
                                 # propagate_exception_v
        i0 = boxint()
        p0 = boxptr()
        operations = [
            ResOperation(rop.NEWUNICODE, [i0], p0),
            ResOperation(rop.FINISH, [p0], None, descr=BasicFailDescr(1))
            ]
        inputargs = [i0]
        looptoken = JitCellToken()
        self.cpu.compile_loop(inputargs, operations, looptoken)
        # overflowing value:
        frame = self.cpu.execute_token(looptoken, sys.maxint // 4 + 1)
        assert self.cpu.get_latest_descr(frame).identifier ==excdescr.identifier
        exc = self.cpu.grab_exc_value()
        assert exc == "memoryerror!"

    def test_math_sqrt(self):
        if not self.cpu.supports_floats:
            py.test.skip("requires floats")

        def math_sqrt(a):
            assert False, 'should not be called'
        from pypy.jit.codewriter.effectinfo import EffectInfo

        effectinfo = EffectInfo([], [], [], [], EffectInfo.EF_CANNOT_RAISE, EffectInfo.OS_MATH_SQRT)
        FPTR = self.Ptr(self.FuncType([lltype.Float], lltype.Float))
        func_ptr = llhelper(FPTR, math_sqrt)
        FUNC = deref(FPTR)
        funcbox = self.get_funcbox(self.cpu, func_ptr)

        calldescr = self.cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT, effectinfo)
        testcases = [(4.0, 2.0), (6.25, 2.5)]
        for arg, expected in testcases:
            res = self.execute_operation(rop.CALL_f,
                        [funcbox, boxfloat(arg)],
                         'float', descr=calldescr)
            assert res == expected

    def test_compile_loop_with_target(self):
        looptoken = JitCellToken()
        targettoken1 = TargetToken()
        targettoken2 = TargetToken()
        faildescr = BasicFailDescr(2)
        faildescr3 = BasicFailDescr(3)
        inputargs, operations, looptoken = self.parse("""
        [i0]
        label(i0, descr=targettoken1)
        i1 = int_add(i0, 1)
        i2 = int_le(i1, 9)
        guard_true(i2, descr=faildescr) [i1]
        label(i1, descr=targettoken2)
        i3 = int_ge(i1, 0)
        guard_true(i3, descr=faildescr3) [i1]
        jump(i1, descr=targettoken1)
        """, locals())
        self.cpu.compile_loop(inputargs, operations, looptoken)
        frame = self.cpu.execute_token(looptoken, 2)
        assert self.cpu.get_latest_descr(frame).identifier == 2
        res = self.cpu.get_latest_value_int(frame, 0)
        assert res == 10

        inputargs, operations, _ = self.parse("""
        [i0]
        i2 = int_sub(i0, 20)
        jump(i2, descr=targettoken2)
        """, locals())
        self.cpu.compile_bridge(faildescr, inputargs, operations, looptoken)

        frame = self.cpu.execute_token(looptoken, 2)
        assert self.cpu.get_latest_descr(frame).identifier == 3
        res = self.cpu.get_latest_value_int(frame, 0)
        assert res == -10

    def test_int_force_ge_zero(self):
        ops = """
        [i0]
        i1 = int_force_ge_zero(i0)    # but forced to be in a register
        finish(i1, descr=faildescr1) []
        """
        faildescr1 = BasicFailDescr(1)
        inputargs, operations, looptoken = self.parse(
            ops, namespace=locals())
        descr = operations[-1].getdescr()
        self.cpu.compile_loop(inputargs, operations, looptoken)
        for inp, outp in [(2,2), (-3, 0)]:
            frame = self.cpu.execute_token(looptoken, inp)
            assert outp == self.cpu.get_finish_value_int(frame)

    def test_compile_asmlen(self):
        from pypy.jit.backend.llsupport.llmodel import AbstractLLCPU
        if not isinstance(self.cpu, AbstractLLCPU):
            py.test.skip("pointless test on non-asm")
        from pypy.jit.backend.tool.viewcode import machine_code_dump
        import ctypes
        ops = """
        [i2]
        i0 = same_as(i2)    # but forced to be in a register
        label(i0, descr=1)
        i1 = int_add(i0, i0)
        guard_true(i1, descr=faildesr) [i1]
        jump(i1, descr=1)
        """
        faildescr = BasicFailDescr(2)
        loop = parse(ops, self.cpu, namespace=locals())
        faildescr = loop.operations[-2].getdescr()
        jumpdescr = loop.operations[-1].getdescr()
        bridge_ops = """
        [i0]
        jump(i0, descr=jumpdescr)
        """
        bridge = parse(bridge_ops, self.cpu, namespace=locals())
        looptoken = JitCellToken()
        self.cpu.assembler.set_debug(False)
        info = self.cpu.compile_loop(loop.inputargs, loop.operations, looptoken)
        bridge_info = self.cpu.compile_bridge(faildescr, bridge.inputargs,
                                              bridge.operations,
                                              looptoken)
        self.cpu.assembler.set_debug(True) # always on untranslated
        assert info.asmlen != 0
        cpuname = autodetect_main_model_and_size()
        # XXX we have to check the precise assembler, otherwise
        # we don't quite know if borders are correct

        def checkops(mc, ops):
            assert len(mc) == len(ops)
            for i in range(len(mc)):
                assert mc[i].split("\t")[2].startswith(ops[i])

        data = ctypes.string_at(info.asmaddr, info.asmlen)
        mc = list(machine_code_dump(data, info.asmaddr, cpuname))
        lines = [line for line in mc if line.count('\t') >= 2]
        checkops(lines, self.add_loop_instructions)
        data = ctypes.string_at(bridge_info.asmaddr, bridge_info.asmlen)
        mc = list(machine_code_dump(data, bridge_info.asmaddr, cpuname))
        lines = [line for line in mc if line.count('\t') >= 2]
        checkops(lines, self.bridge_loop_instructions)


    def test_compile_bridge_with_target(self):
        # This test creates a loopy piece of code in a bridge, and builds another
        # unrelated loop that ends in a jump directly to this loopy bit of code.
        # It catches a case in which we underestimate the needed frame_depth across
        # the cross-loop JUMP, because we estimate it based on the frame_depth stored
        # in the original loop.
        looptoken1 = JitCellToken()
        targettoken1 = TargetToken()
        faildescr1 = BasicFailDescr(2)
        faildescr2 = BasicFailDescr(1234)
        inputargs, operations, looptoken = self.parse("""
        [i0]
        i1 = int_le(i0, 1)
        guard_true(i1, descr=faildescr1) [i0]
        finish(i0, descr=faildescr2)
        """, locals())
        self.cpu.compile_loop(inputargs, operations, looptoken1)

        def func(a, b, c, d, e, f, g, h, i):
            assert a + 2 == b
            assert a + 4 == c
            assert a + 6 == d
            assert a + 8 == e
            assert a + 10 == f
            assert a + 12 == g
            assert a + 14 == h
            assert a + 16 == i
        FPTR = self.Ptr(self.FuncType([lltype.Signed]*9, lltype.Void))
        func_ptr = llhelper(FPTR, func)
        cpu = self.cpu
        calldescr = cpu.calldescrof(deref(FPTR), (lltype.Signed,)*9, lltype.Void,
                                    EffectInfo.MOST_GENERAL)
        faildescr42 = BasicFailDescr(42)
        inputargs, operations, looptoken = self.parse("""
        [i0]
        label(i0, descr=targettoken1)
        i1 = int_add(i0, 1)
        i2 = int_add(i1, 1)
        i3 = int_add(i2, 1)
        i4 = int_add(i3, 1)
        i5 = int_add(i4, 1)
        i6 = int_add(i5, 1)
        i7 = int_add(i6, 1)
        i8 = int_add(i7, 1)
        i9 = int_add(i8, 1)
        i10 = int_add(i9, 1)
        i11 = int_add(i10, 1)
        i12 = int_add(i11, 1)
        i13 = int_add(i12, 1)
        i14 = int_add(i13, 1)
        i15 = int_add(i14, 1)
        i16 = int_add(i15, 1)
        i17 = int_add(i16, 1)
        i18 = int_add(i17, 1)
        i19 = int_add(i18, 1)
        call_v(ConstClass(func_ptr), i2, i4, i6, i8, i10, i12, i14, i16, i18, descr=calldescr)
        call_v(ConstClass(func_ptr), i2, i4, i6, i8, i10, i12, i14, i16, i18, descr=calldescr)
        i20 = int_lt(i19, 100)
        guard_true(i20, descr=faildescr42) []
        jump(i19, descr=targettoken1)
        """, locals())
        self.cpu.compile_bridge(faildescr1, inputargs, operations, looptoken1)

        inputargs, operations, looptoken2 = self.parse("""
        [i0]
        jump(0, descr=targettoken1)
        """, locals())
        self.cpu.compile_loop(inputargs, operations, looptoken2)
        frame = self.cpu.execute_token(looptoken2, -9)
        assert self.cpu.get_latest_descr(frame).identifier == 42

    def test_wrong_guard_nonnull_class(self):
        t_box, T_box = self.alloc_instance(self.T)
        the_class = T_box.getint()
        faildescr = BasicFailDescr(42)
        faildescr99 = BasicFailDescr(99)
        inputargs, operations, looptoken = self.parse("""
        [p0]
        guard_nonnull_class(p0, ConstClass(the_class), descr=faildescr) []
        finish(descr=faildescr1) []
        """, namespace=locals())
        self.cpu.compile_loop(inputargs, operations, looptoken)
        _, operations, _ = self.parse("""
        []
        finish(descr=faildescr99) []
        """, namespace=locals())
        self.cpu.compile_bridge(faildescr, [], operations, looptoken)
        frame = self.cpu.execute_token(looptoken,
                                       lltype.nullptr(llmemory.GCREF.TO))
        assert self.cpu.get_latest_descr(frame).identifier == 99

    def test_raw_load_int(self):
        from pypy.rlib import rawstorage
        for T in [rffi.UCHAR, rffi.SIGNEDCHAR,
                  rffi.USHORT, rffi.SHORT,
                  rffi.UINT, rffi.INT,
                  rffi.ULONG, rffi.LONG]:
            ops = """
            [i0, i1]
            i2 = raw_load_i(i0, i1, descr=arraydescr)
            finish(i2, descr=faildescr1) []
            """
            arraydescr = self.cpu.arraydescrof(rffi.CArray(T))
            p = rawstorage.alloc_raw_storage(31)
            for i in range(31):
                p[i] = '\xDD'
            value = rffi.cast(T, 0x4243444546474849)
            rawstorage.raw_storage_setitem(p, 16, value)
            faildescr1 = BasicFailDescr(1)
            inputargs, operations, looptoken = self.parse(
                ops, namespace=locals())
            self.cpu.compile_loop(inputargs, operations, looptoken)
            frame = self.cpu.execute_token(looptoken,
                                           rffi.cast(lltype.Signed, p), 16)
            result = self.cpu.get_finish_value_int(frame)
            assert result == rffi.cast(lltype.Signed, value)
            rawstorage.free_raw_storage(p)

    def test_raw_load_float(self):
        if not self.cpu.supports_floats:
            py.test.skip("requires floats")
        from pypy.rlib import rawstorage
        for T in [rffi.DOUBLE]:
            ops = """
            [i0, i1]
            f2 = raw_load_f(i0, i1, descr=arraydescr)
            finish(f2, descr=faildescr1) []
            """
            arraydescr = self.cpu.arraydescrof(rffi.CArray(T))
            p = rawstorage.alloc_raw_storage(31)
            for i in range(31):
                p[i] = '\xDD'
            value = rffi.cast(T, 1.12e20)
            rawstorage.raw_storage_setitem(p, 16, value)
            faildescr1 = BasicFailDescr(1)
            inputargs, operations, looptoken = self.parse(
                ops, namespace=locals())
            self.cpu.compile_loop(inputargs, operations, looptoken)
            frame = self.cpu.execute_token(looptoken,
                                           rffi.cast(lltype.Signed, p), 16)
            result = self.cpu.get_finish_value_float(frame)
            result = longlong.getrealfloat(result)
            assert result == rffi.cast(lltype.Float, value)
            rawstorage.free_raw_storage(p)

    def test_raw_store_int(self):
        from pypy.rlib import rawstorage
        for T in [rffi.UCHAR, rffi.SIGNEDCHAR,
                  rffi.USHORT, rffi.SHORT,
                  rffi.UINT, rffi.INT,
                  rffi.ULONG, rffi.LONG]:
            ops = """
            [i0, i1, i2]
            raw_store(i0, i1, i2, descr=arraydescr)
            finish(descr=faildescr1) []
            """
            arraydescr = self.cpu.arraydescrof(rffi.CArray(T))
            p = rawstorage.alloc_raw_storage(31)
            for i in range(31):
                p[i] = '\xDD'
            value = 0x4243444546474849 & sys.maxint
            faildescr1 = BasicFailDescr(1)
            inputargs, operations, looptoken = self.parse(
                ops, namespace=locals())
            self.cpu.compile_loop(inputargs, operations, looptoken)
            frame = self.cpu.execute_token(looptoken,
                                        rffi.cast(lltype.Signed, p), 16, value)
            result = rawstorage.raw_storage_getitem(T, p, 16)
            assert result == rffi.cast(T, value)
            rawstorage.free_raw_storage(p)

    def test_raw_store_float(self):
        if not self.cpu.supports_floats:
            py.test.skip("requires floats")
        from pypy.rlib import rawstorage
        for T in [rffi.DOUBLE]:
            ops = """
            [i0, i1, f2]
            raw_store(i0, i1, f2, descr=arraydescr)
            finish(descr=faildescr1) []
            """
            arraydescr = self.cpu.arraydescrof(rffi.CArray(T))
            p = rawstorage.alloc_raw_storage(31)
            for i in range(31):
                p[i] = '\xDD'
            value = 1.23e20
            faildescr1 = BasicFailDescr(1)
            inputargs, operations, looptoken = self.parse(
                ops, namespace=locals())
            self.cpu.compile_loop(inputargs, operations, looptoken)
            frame = self.cpu.execute_token(looptoken,
                                           rffi.cast(lltype.Signed, p), 16,
                                           longlong.getfloatstorage(value))
            result = rawstorage.raw_storage_getitem(T, p, 16)
            assert result == rffi.cast(T, value)
            rawstorage.free_raw_storage(p)

    def test_forcing_op_with_fail_arg_in_reg(self):
        values = []
        def maybe_force(token, flag):
            self.cpu.force(token)
            values.append(self.cpu.get_latest_value_int(token, 0))
            values.append(token)
            return 42

        FUNC = self.FuncType([self.cpu.JITFRAMEPTR, lltype.Signed], lltype.Signed)
        func_ptr = llhelper(lltype.Ptr(FUNC), maybe_force)
        calldescr = self.cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT,
                                         EffectInfo.MOST_GENERAL)
        faildescr = BasicFailDescr(23)
        inputargs, operations, looptoken = self.parse('''
        [i0, i1]
        ptok = jit_frame()
        i2 = call_may_force_i(ConstClass(func_ptr), ptok, i1, descr=calldescr)
        guard_not_forced(descr=faildescr) [i2]
        finish(i2, descr=faildescr2) []
        ''', namespace=locals())
        self.cpu.compile_loop(inputargs, operations, looptoken)
        frame = self.cpu.execute_token(looptoken, 20, 0)
        assert self.cpu.get_latest_descr(frame).identifier == 23
        assert self.cpu.get_latest_value_int(frame, 0) == 42
        # make sure that force reads the registers from a zeroed piece of
        # memory
        assert values[0] == 0
        assert values[1] == frame
