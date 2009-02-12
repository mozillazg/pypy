from pypy.rpython.lltypesystem import lltype, rclass, llmemory
from pypy.rpython.lltypesystem.rvirtualizable2 import VABLERTIPTR
from pypy.rpython.lltypesystem.rvirtualizable2 import VirtualizableAccessor
from pypy.jit.backend.llgraph import runner
from pypy.jit.metainterp import heaptracker
from pypy.jit.metainterp.history import (ResOperation, MergePoint, Jump,
                                         ConstInt, ConstAddr, BoxInt, BoxPtr)
from pypy.jit.metainterp.optimize import PerfectSpecializer
from pypy.jit.metainterp.virtualizable import VirtualizableDesc
from pypy.jit.metainterp.test.test_optimize import (cpu, NODE, node_vtable)

# ____________________________________________________________

XY = lltype.GcStruct(
    'XY',
    ('parent', rclass.OBJECT),
    ('vable_base', llmemory.Address),
    ('vable_rti', VABLERTIPTR),
    ('x', lltype.Signed),
    ('node', lltype.Ptr(NODE)),
    hints = {'virtualizable2': True},
    adtmeths = {'access': VirtualizableAccessor()})
XY._adtmeths['access'].initialize(XY, ['x', 'node'])

xy_vtable = lltype.malloc(rclass.OBJECT_VTABLE, immortal=True)
xy_vtable.name = lltype.malloc(rclass.OBJECT_VTABLE.name.TO, 3, immortal=True)
xy_vtable.name[0] = 'X'
xy_vtable.name[1] = 'Y'
xy_vtable.name[2] = '\x00'
heaptracker.set_testing_vtable_for_gcstruct(XY, xy_vtable)

XYSUB = lltype.GcStruct(
    'XYSUB',
    ('parent', XY),
    ('z', lltype.Signed),
    hints = {'virtualizable2': True},
    adtmeths = {'access': VirtualizableAccessor()})
XYSUB._adtmeths['access'].initialize(XYSUB, ['z'], PARENT=XY)

xysub_vtable = lltype.malloc(rclass.OBJECT_VTABLE, immortal=True)
xysub_vtable.name = lltype.malloc(rclass.OBJECT_VTABLE.name.TO, 6,
                                  immortal=True)
xysub_vtable.name[0] = 'X'
xysub_vtable.name[1] = 'Y'
xysub_vtable.name[2] = 'S'
xysub_vtable.name[3] = 'U'
xysub_vtable.name[4] = 'B'
xysub_vtable.name[5] = '\x00'
heaptracker.set_testing_vtable_for_gcstruct(XYSUB, xysub_vtable)

# ____________________________________________________________

xy_desc = VirtualizableDesc(cpu, XY)

# ____________________________________________________________

class A:
    ofs_node = runner.CPU.offsetof(XY, 'node')
    ofs_value = runner.CPU.offsetof(NODE, 'value')
    size_of_node = runner.CPU.sizeof(NODE)
    #
    frame = lltype.malloc(XY)
    frame.vable_rti = lltype.nullptr(XY.vable_rti.TO)
    frame.node = lltype.malloc(NODE)
    frame.node.value = 20
    sum = BoxInt(0)
    fr = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, frame))
    n1 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, frame.node))
    nextnode = lltype.malloc(NODE)
    nextnode.value = 19
    n2 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, nextnode))
    v = BoxInt(frame.node.value)
    v2 = BoxInt(nextnode.value)
    sum2 = BoxInt(0 + frame.node.value)
    ops = [
        MergePoint('merge_point', [sum, fr], []),
        ResOperation('guard_nonvirtualized__4', [fr, ConstInt(ofs_node)], []),
        ResOperation('getfield_gc', [fr, ConstInt(ofs_node)], [n1]),
        ResOperation('getfield_gc', [n1, ConstInt(ofs_value)], [v]),
        ResOperation('int_sub', [v, ConstInt(1)], [v2]),
        ResOperation('int_add', [sum, v], [sum2]),
        ResOperation('new_with_vtable', [ConstInt(size_of_node),
                                         ConstAddr(node_vtable, cpu)], [n2]),
        ResOperation('setfield_gc', [n2, ConstInt(ofs_value), v2], []),
        ResOperation('setfield_gc', [fr, ConstInt(ofs_node), n2], []),
        Jump('jump', [sum2, fr], []),
        ]
    ops[1].desc = xy_desc

def test_A_find_nodes():
    spec = PerfectSpecializer(A.ops)
    spec.find_nodes()
    assert spec.nodes[A.fr].virtualized

def test_A_intersect_input_and_output():
    spec = PerfectSpecializer(A.ops)
    spec.find_nodes()
    spec.intersect_input_and_output()
    assert spec.nodes[A.fr].escaped
    assert spec.nodes[A.fr].virtualized
    assert not spec.nodes[A.n1].escaped
    assert not spec.nodes[A.n2].escaped

def test_A_optimize_loop():
    operations = A.ops[:]
    spec = PerfectSpecializer(operations)
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop()
    assert equaloplists(operations, [
            MergePoint('merge_point', [A.sum, A.n1, A.v], []),
            ResOperation('int_sub', [A.v, ConstInt(1)], [A.v2]),
            ResOperation('int_add', [A.sum, A.v], [A.sum2]),
            Jump('jump', [A.sum2, A.n1, A.v2], []),
        ])
