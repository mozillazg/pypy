import py
from pypy.conftest import option
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.rpython.lltypesystem.rclass import OBJECT, OBJECTPTR, OBJECT_VTABLE

from llgraph import runner
from history import BoxInt, BoxPtr, ConstInt, ConstPtr, ConstAddr
from history import ResOperation, MergePoint, Jump
from optimize import Specializer
from fixclass import FixedClassSpecializer, FixedClassSpecNode

cpu = runner.CPU(None)

class FakeMetaInterp:
    def __init__(self, specializecls=None):
        self._specializecls = specializecls
        self._can_have_virtualizables = True
        self.cpu = cpu

    def builtins_get(self, addr):
        return None

NODE = lltype.GcForwardReference()
NODE.become(lltype.GcStruct('NODE', ('parent', OBJECT),
                                    ('value', lltype.Signed),
                                    ('next', lltype.Ptr(NODE))))

node_vtable = lltype.malloc(OBJECT_VTABLE, immortal=True)


def make_node_chain(length):
    next = lltype.nullptr(NODE)
    for i in range(length):
        node = lltype.malloc(NODE)
        lltype.cast_pointer(OBJECTPTR, node).typeptr = node_vtable
        node.value = pow(2, i, 93)
        node.next = next
        next = node
    return next

def unguardify(oplist):
    return [op for op in oplist if op.opname != 'guard_class']

class Any(object):
    def __eq__(self, other):
        return True
    def __ne__(self, other):
        return False
    def __repr__(self):
        return '*'
ANY = Any()

def equaloplists(oplist1, oplist2):
    #saved = Box._extended_display
    #try:
    #    Box._extended_display = False
    print '-'*20, 'Comparing lists', '-'*20
    for op1, op2 in zip(oplist1, oplist2):
        txt1 = str(op1)
        txt2 = str(op2)
        while txt1 or txt2:
            print '%-39s| %s' % (txt1[:39], txt2[:39])
            txt1 = txt1[39:]
            txt2 = txt2[39:]
        assert op1.opname == op2.opname
        assert len(op1.args) == len(op2.args)
        for x, y in zip(op1.args, op2.args):
            assert x == y or y == x     # for ANY object :-(
        assert op1.results == op2.results
    assert len(oplist1) == len(oplist2)
    print '-'*57
    #finally:
    #    Box._extended_display = saved
    return True

# ____________________________________________________________

class A:
    x = BoxInt(123)
    y = BoxInt(456)
    z = BoxInt(579)
    t = BoxInt(455)
    u = BoxInt(0)   # False
    o = BoxInt(1)
    unused = BoxInt(-42)
    unused2 = BoxInt(-42)
    ops = [
        MergePoint('merge_point', [x, y, unused, o], []),
        ResOperation('int_add', [x, y], [z]),
        ResOperation('int_sub', [y, o], [t]),
        ResOperation('int_eq', [t, ConstInt(0)], [u]),
        MergePoint('merge_point', [u, t, unused, z], []),
        ResOperation('guard_false', [u], []),
        ResOperation('same_as', [unused], [unused2]),
        Jump('jump', [z, t, unused2, o], []),
        ]
    ops[-1].jump_target = ops[0]

##def test_remove_unused_A():
##    py.test.skip("no unused loop constant detection for now")
##    operations = A.ops[:]
##    sources = DummySourceMapping()
##    sources.content[A.unused] = \
##        sources.content[A.unused2] = DummySource(loop_constant=True,
##                                                 unused=True)
##    specializer = Specializer(operations, sources)
##    specializer.expand_virtuals()
##    assert equaloplists(operations, [
##        MergePoint('merge_point', [A.x, A.y, A.o], []),
##        ResOperation('int_add', [A.x, A.y], [A.z]),
##        ResOperation('int_sub', [A.y, A.o], [A.t]),
##        ResOperation('int_eq', [A.t, newconst(0)], [A.u]),
##        MergePoint('merge_point', [A.u, A.t, A.z], []),
##        ResOperation('guard_false', [A.u], []),
##        Jump('jump', [A.z, A.t, A.o], []),
##        ])

# ____________________________________________________________

class B:
    ofs_value = runner.CPU.offsetof(NODE, 'value')
    ofs_next  = runner.CPU.offsetof(NODE, 'next')
    #
    startnode = make_node_chain(20)
    sum = BoxInt(0)
    n1 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, startnode))
    n2 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, startnode))
    n3 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, startnode))
    n1nz = BoxInt(1)    # True
    v = BoxInt(startnode.value)
    sum2 = BoxInt(0 + startnode.value)
    nxt = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, startnode.next))
    ops = [
        MergePoint('merge_point', [sum, n1], []),
        ResOperation('ptr_nonzero', [n1], [n1nz]),
        ResOperation('guard_true', [n1nz], []),
        ResOperation('guard_class', [n1, ConstAddr(node_vtable, cpu)], [n2]),
        ResOperation('getfield_gc__4', [n2, ConstInt(ofs_value)], [v]),
        ResOperation('int_add', [sum, v], [sum2]),
        ResOperation('guard_class', [n2, ConstAddr(node_vtable, cpu)], [n3]),
        ResOperation('getfield_gc_ptr', [n3, ConstInt(ofs_next)], [nxt]),
        Jump('jump', [sum2, nxt], []),
        ]
    ops[-1].jump_target = ops[0]

def test_remove_class_guards_B():
    specializer = Specializer(FakeMetaInterp(FixedClassSpecializer),
                              B.ops, is_bridge=False)
    count = specializer.expand_virtuals()
    assert count == 0
    assert equaloplists(specializer.operations, B.ops)

def test_expand_virtuals_B():
    specializer = Specializer(FakeMetaInterp(), B.ops, is_bridge=False)
    count = specializer.expand_virtuals()
    assert count == 0
    assert equaloplists(specializer.operations, B.ops)

# ____________________________________________________________

class C:
    startnode = lltype.malloc(NODE)
    lltype.cast_pointer(OBJECTPTR, startnode).typeptr = node_vtable
    startnode.value = 0

    nextnode = lltype.malloc(NODE)
    lltype.cast_pointer(OBJECTPTR, nextnode).typeptr = node_vtable
    nextnode.value = 10

    size = runner.CPU.sizeof(NODE)
    ofs_value = runner.CPU.offsetof(NODE, 'value')
    ofs_next  = runner.CPU.offsetof(NODE, 'next')

    c1 = BoxInt(10)
    n1 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, startnode))
    c2 = BoxInt(c1.value - 1)
    c2nz = BoxInt(1)   # True

    n1v = BoxInt(startnode.value)
    sum2 = BoxInt(c1.value + n1v.value)
    n2 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, nextnode))
    n2a = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, nextnode))

    ops = [
        MergePoint('merge_point', [c1, n1], []),
        ResOperation('guard_class', [n1, ConstAddr(node_vtable, cpu)], []),
        MergePoint('merge_point', [c1, n1], []),
        ResOperation('guard_class', [n1, ConstAddr(node_vtable, cpu)], []),
        ResOperation('int_sub', [c1, ConstInt(1)], [c2]),
        ResOperation('int_ne', [c2, ConstInt(0)], [c2nz]),
        MergePoint('merge_point', [c1, c2nz, c2, n1], []),
        ResOperation('guard_true', [c2nz], []),
        ResOperation('getfield_gc__4', [n1, ConstInt(ofs_value)], [n1v]),
        ResOperation('int_add', [c1, n1v], [sum2]),
        ResOperation('new_with_vtable', [ConstInt(size),
                                         ConstAddr(node_vtable, cpu)], [n2]),
        #ResOperation('same_as', [n2a], [n2]),
        ResOperation('setfield_gc__4', [n2, ConstInt(ofs_value), sum2], []),
        Jump('jump', [c2, n2], []),
        ]
    ops[-1].jump_target = ops[0]

def test_remove_class_guards_C():
    specializer = Specializer(FakeMetaInterp(FixedClassSpecializer),
                              C.ops, is_bridge=False)
    count = specializer.expand_virtuals()
    assert count == 0
    assert equaloplists(specializer.operations, unguardify(C.ops))

def test_expand_virtuals_C():
    specializer = Specializer(FakeMetaInterp(), C.ops, is_bridge=False)
    count = specializer.expand_virtuals()
    assert count == 2
    [_, value_0] = specializer.operations[0].args
    assert isinstance(value_0, BoxInt)
    assert equaloplists(specializer.operations, [
        MergePoint('merge_point', [C.c1, value_0], []),
        MergePoint('merge_point', [C.c1, value_0], []),
        ResOperation('int_sub', [C.c1, ConstInt(1)], [C.c2]),
        ResOperation('same_as', [C.c2], [ANY]),
        MergePoint('merge_point', [C.c1, ANY, C.c2, value_0], []),
        ResOperation('guard_ne', [ANY, ConstInt(0)], []),
        ResOperation('int_add', [C.c1, value_0], [C.sum2]),
        Jump('jump', [C.c2, C.sum2], []),
        ])

### ____________________________________________________________

##class D:
##    a1 = Box(123)
##    a2 = Box(456)
##    n1 = Box(42)
##    n2 = Box(41)
##    ops = [
##        MergePoint('merge_point', [a1, a2, n1], []),
##        ResOperation('guard_false', [n1], []),
##        ResOperation('int_sub', [n1, newconst(1)], [n2]),
##        Jump('jump', [a2, a1, n2], []),    # swap a1 and a2 arguments
##        ]
##    ops[-1].jump_target = ops[0]

### ____________________________________________________________

##class F:
##    ARRAY = ootype.Array(ootype.Signed)
##    a1 = Box(ootype.oonewarray(ARRAY, 3))
##    n1 = Box(42)
##    n2 = Box(42)
##    ops = [
##        MergePoint('merge_point', [n1], []),
##        ResOperation('builtin', [voidconst('newlist'),
##                                 newconst(3)], [a1]),
##        ResOperation('builtin', [voidconst('list.setitem'),
##                                 a1, newconst(1), n1], []),
##        ResOperation('builtin', [voidconst('list.getitem'),
##                                 a1, newconst(1)], [n2]),
##        Jump('jump', [n2], []),
##        ]
##    ops[-1].jump_target = ops[0]

##def test_expand_virtuals_F():
##    specializer = Specializer(F.ops, is_bridge=False)
##    count = specializer.expand_virtuals()
##    assert count == 1
##    assert equaloplists(specializer.operations, [
##        MergePoint('merge_point', [F.n1], []),
##        Jump('jump', [F.n1], []),
##        ])

### ____________________________________________________________

S = lltype.GcStruct('S', ('header', OBJECT),
                         ('value', lltype.Signed))

s_vtable = lltype.malloc(OBJECT_VTABLE, immortal=True)

def new_s(value=0):
    s = lltype.malloc(S)
    s.header.typeptr = s_vtable
    s.value = value
    return s

class G:
    startnode = new_s(0)
    n1 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, startnode))
    v1 = BoxInt(startnode.value)
    v2 = BoxInt(startnode.value+1)
    nextnode = new_s(1)
    n2 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, nextnode))

    c_vtable = ConstAddr(s_vtable, cpu)
    c_size = ConstInt(runner.CPU.sizeof(S))
    c_value = ConstInt(runner.CPU.offsetof(S, 'value'))

    ops = [
        MergePoint('merge_point', [n1], []),
        ResOperation('guard_class', [n1, c_vtable], []),
        MergePoint('merge_point', [n1], []),
        ResOperation('guard_class', [n1, c_vtable], []),
        ResOperation('new_with_vtable', [c_size, c_vtable], [n2]),
        ResOperation('getfield_gc__4', [n1, c_value], [v1]),
        ResOperation('int_add', [v1, ConstInt(1)], [v2]),
        ResOperation('setfield_gc__4', [n2, c_value, v2], []),
        Jump('jump', [n2], []),
        ]
    ops[-1].jump_target = ops[0]

def test_remove_class_guards_G():
    specializer = Specializer(FakeMetaInterp(FixedClassSpecializer),
                              G.ops, is_bridge=False)
    count = specializer.expand_virtuals()
    assert count == 0
    assert equaloplists(specializer.operations, [
        MergePoint('merge_point', [G.n1], []),
        MergePoint('merge_point', [G.n1], []),
        ResOperation('new_with_vtable', [G.c_size, G.c_vtable], [G.n2]),
        ResOperation('getfield_gc__4', [G.n1, G.c_value], [G.v1]),
        ResOperation('int_add', [G.v1, ConstInt(1)], [G.v2]),
        ResOperation('setfield_gc__4', [G.n2, G.c_value, G.v2], []),
        Jump('jump', [G.n2], []),
        ])
    for mp in specializer.operations[:2]:
        assert mp.opname == 'merge_point'
        assert len(mp.spec_nodes) == 1
        assert isinstance(mp.spec_nodes[0], FixedClassSpecNode)
        assert mp.spec_nodes[0].known_class == s_vtable

def test_expand_virtuals_G():
    specializer = Specializer(FakeMetaInterp(), G.ops, is_bridge=False)
    count = specializer.expand_virtuals()
    assert count == 1
    [value_0] = specializer.operations[0].args
    assert isinstance(value_0, BoxInt)
    [value_1] = specializer.operations[-1].args
    assert isinstance(value_1, BoxInt)
    assert equaloplists(specializer.operations, [
        MergePoint('merge_point', [value_0], []),
        MergePoint('merge_point', [value_0], []),
        ResOperation('int_add', [value_0, ConstInt(1)], [value_1]),
        Jump('jump', [value_1], []),
        ])

### ____________________________________________________________

S2 = lltype.GcStruct('S2', ('header', OBJECT))
T2 = lltype.GcStruct('T2', ('parent', S2), ('value', lltype.Signed))

t2_vtable = lltype.malloc(OBJECT_VTABLE, immortal=True)

def new_t2(value=0):
    t = lltype.malloc(T2)
    t.parent.header.typeptr = t2_vtable
    t.value = value
    return t

class H:
    startnode = lltype.cast_pointer(lltype.Ptr(S2), new_t2(13))
    n1 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, startnode))
    v1 = BoxInt(13)

    c_t2_vtable = ConstAddr(t2_vtable, cpu)
    c_t2_value = ConstInt(runner.CPU.offsetof(T2, 'value'))

    ops = [
        MergePoint('merge_point', [n1], []),
        ResOperation('guard_class', [n1, c_t2_vtable], []),
        ResOperation('getfield_gc__4', [n1, c_t2_value], [v1]),
        Jump('jump', [n1], []),
        ]
    ops[-1].jump_target = ops[0]

def test_remove_class_guards_H():
    specializer = Specializer(FakeMetaInterp(FixedClassSpecializer),
                              H.ops, is_bridge=False)
    count = specializer.expand_virtuals()
    assert count == 0
    assert equaloplists(specializer.operations, unguardify(H.ops))
