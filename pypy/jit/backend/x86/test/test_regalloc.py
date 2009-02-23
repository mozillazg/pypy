
""" Tests for register allocation for common constructs
"""

import py
from pypy.jit.metainterp.history import (ResOperation, MergePoint, Jump,
                                         BoxInt, ConstInt, GuardOp)
from pypy.jit.backend.x86.runner import CPU, GuardFailed
from pypy.rpython.lltypesystem import lltype
from pypy.jit.backend.x86.test.test_runner import FakeMetaInterp, FakeStats

def test_simple_loop():
    meta_interp = FakeMetaInterp()
    cpu = CPU(rtyper=None, stats=FakeStats())
    cpu.set_meta_interp(meta_interp)
    i = BoxInt(0) # a loop variable
    i_0 = BoxInt(0) # another incarnation of loop variable
    flag = BoxInt(1)  # True
    flag_0 = BoxInt(1)  # True
    # this should be more or less:
    # i = 0
    # while i < 5:
    #    i += 1
    operations = [
        MergePoint('merge_point', [i, flag], []),
        GuardOp('guard_true', [flag], []),
        ResOperation('int_add', [i, ConstInt(1)], [i_0]),
        ResOperation('int_lt', [i_0, ConstInt(5)], [flag_0]),
        Jump('jump', [i_0, flag_0], []),
        ]
    startmp = operations[0]
    operations[-1].jump_target = startmp
    operations[1].liveboxes = [i, flag]

    cpu.compile_operations(operations)
    res = cpu.execute_operations_in_new_frame('foo', startmp,
                                              [BoxInt(0), BoxInt(1)], 'int')
    assert res.value == 42
    assert meta_interp.recordedvalues == [5, False]
    # assert stuff
    regalloc = cpu.assembler._regalloc
    # no leakage, args to merge_point
    assert regalloc.current_stack_depth == 2
    longevity = regalloc.longevity
    assert longevity == {i: (0, 2), flag: (0, 1), i_0: (2, 4), flag_0: (3, 4)}

def test_longer_loop():
    """ This test checks whether register allocation can
    reclaim back unused registers
    """
    meta_interp = FakeMetaInterp()
    cpu = CPU(rtyper=None, stats=FakeStats())
    cpu.set_meta_interp(meta_interp)
    x = BoxInt(1)
    x0 = BoxInt(0)
    y = BoxInt(1)
    i = BoxInt(0)
    i0 = BoxInt(0)
    flag = BoxInt(1) # True
    flag0 = BoxInt(0) # False
    v0 = BoxInt(0)
    v1 = BoxInt(0)
    v2 = BoxInt(0)
    v3 = BoxInt(0)
    y0 = BoxInt(0)
    # code for:
    def f():
        i = 0
        x = 1
        y = 1
        while i < 5:
            x = ((y + x) * i) - x
            y = i * y - x * y
            i += 1
        return [x, y, i, i < 5]
    operations = [
        MergePoint('merge_point', [x, y, i, flag], []),
        GuardOp('guard_true', [flag], []),
        ResOperation('int_add', [y, x], [v0]),
        ResOperation('int_mul', [v0, i], [v1]),
        ResOperation('int_sub', [v1, x], [x0]),
        ResOperation('int_mul', [x0, y], [v2]),
        ResOperation('int_mul', [i, y], [v3]),
        ResOperation('int_sub', [v3, v2], [y0]),
        ResOperation('int_add', [i, ConstInt(1)], [i0]),
        ResOperation('int_lt', [i0, ConstInt(5)], [flag0]),
        Jump('jump', [x0, y0, i0, flag0], []),
        ]
    startmp = operations[0]
    operations[-1].jump_target = startmp
    operations[1].liveboxes = [x, y, i, flag]

    cpu.compile_operations(operations)

    res = cpu.execute_operations_in_new_frame('foo', startmp,
                                              [BoxInt(1), BoxInt(1),
                                               BoxInt(0), BoxInt(1)],
                                              'int')
    assert res.value == 42
    assert meta_interp.recordedvalues == f()
