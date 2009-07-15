import py

from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.lltypesystem.rclass import OBJECT, OBJECT_VTABLE

from pypy.jit.backend.llgraph import runner
from pypy.jit.metainterp import resoperation, history
from pypy.jit.metainterp.resoperation import rop
from pypy.jit.metainterp.history import (BoxInt, BoxPtr, ConstInt, ConstPtr,
                                         Const, ConstAddr, TreeLoop)
from pypy.jit.metainterp.optimize import perfect_specialization_finder
from pypy.jit.metainterp.specnode import (FixedClassSpecNode,
                                          NotSpecNode,
                                          VirtualInstanceSpecNode)

cpu = runner.LLtypeCPU(None)

NODE = lltype.GcForwardReference()
NODE.become(lltype.GcStruct('NODE', ('parent', OBJECT),
                                    ('value', lltype.Signed),
                                    ('next', lltype.Ptr(NODE))))

node_vtable = lltype.malloc(OBJECT_VTABLE, immortal=True)
node_vtable_adr = llmemory.cast_ptr_to_adr(node_vtable)

NODE2 = lltype.GcStruct('NODE2', ('parent', NODE),
                                 ('one_more_field', lltype.Signed))

node2_vtable = lltype.malloc(OBJECT_VTABLE, immortal=True)
node2_vtable_adr = llmemory.cast_ptr_to_adr(node2_vtable)

cpu.class_sizes = {cpu.cast_adr_to_int(node_vtable_adr): cpu.sizeof(NODE)}


# ____________________________________________________________

def Loop(inputargs, operations):
    loop = TreeLoop("test")
    loop.inputargs = inputargs
    loop.operations = operations
    return loop

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
        assert op1.opnum == op2.opnum
        assert len(op1.args) == len(op2.args)
        for x, y in zip(op1.args, op2.args):
            assert x == y or y == x     # for ANY object :-(
        assert op1.result == op2.result
        assert op1.descr == op2.descr
    assert len(oplist1) == len(oplist2)
    print '-'*57
    #finally:
    #    Box._extended_display = saved
    return True

def ResOperation(opname, args, result, descr=None):
    if opname == 'escape':
        opnum = -123       # random number not in the list
    else:
        opnum = getattr(rop, opname.upper())
    return resoperation.ResOperation(opnum, args, result, descr)

# ____________________________________________________________

class A:
    ofs_next = runner.LLtypeCPU.fielddescrof(NODE, 'next')
    ofs_value = runner.LLtypeCPU.fielddescrof(NODE, 'value')
    size_of_node = runner.LLtypeCPU.sizeof(NODE)
    #
    startnode = lltype.malloc(NODE)
    startnode.value = 20
    sum = BoxInt(0)
    n1 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, startnode))
    nextnode = lltype.malloc(NODE)
    nextnode.value = 19
    n2 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, nextnode))
    n1nz = BoxInt(1)    # True
    v = BoxInt(startnode.value)
    v2 = BoxInt(startnode.value-1)
    sum2 = BoxInt(0 + startnode.value)
    inputargs = [sum, n1]
    ops = [
        ResOperation('guard_class', [n1, ConstAddr(node_vtable, cpu)], None),
        ResOperation('getfield_gc', [n1], v, ofs_value),
        ResOperation('int_sub', [v, ConstInt(1)], v2),
        ResOperation('int_add', [sum, v], sum2),
        ResOperation('new_with_vtable', [ConstAddr(node_vtable, cpu)], n2,
                     size_of_node),
        ResOperation('setfield_gc', [n2, v2], None, ofs_value),
        ResOperation('setfield_gc', [n2, n2], None, ofs_next),
        ResOperation('jump', [sum2, n2], None),
        ]

    def set_guard(op, args):
        assert op.is_guard(), op
        op.suboperations = [ResOperation('fail', args, None)]

    set_guard(ops[0], [])

def test_A_find_nodes():
    perfect_specialization_finder.find_nodes(Loop(A.inputargs, A.ops))
    nodes = perfect_specialization_finder.nodes
    assert A.sum in nodes
    assert A.sum2 not in nodes
    assert nodes[A.n1] is not nodes[A.n2]
    assert not nodes[A.n1].escaped
    assert not nodes[A.n2].escaped

    assert not nodes[A.n1].curfields
    assert nodes[A.n1].origfields[A.ofs_value] is nodes[A.v]
    assert not nodes[A.n2].origfields
    assert nodes[A.n2].curfields[A.ofs_next] is nodes[A.n2]
