import py

from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.lltypesystem.rclass import OBJECT, OBJECT_VTABLE

from pypy.jit.backend.llgraph import runner
from pypy.jit.metainterp.history import (BoxInt, BoxPtr, ConstInt, ConstPtr,
                                         Const, ConstAddr, TreeLoop, BoxObj)
from pypy.jit.metainterp.optimize import perfect_specialization_finder
from pypy.jit.metainterp.test.oparser import parse

# ____________________________________________________________

def equaloplists(oplist1, oplist2):
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
            assert x == y
        assert op1.result == op2.result
        assert op1.descr == op2.descr
        if op1.suboperations:
            assert equaloplists(op1.suboperations, op2.suboperations)
    assert len(oplist1) == len(oplist2)
    print '-'*57
    return True

def test_equaloplists():
    ops = """
    [i0]
    i1 = int_add(i0, 1)
    guard_true(i1)
        i2 = int_add(i1, 1)
        fail(i2)
    jump(i1)
    """
    loop1 = parse(ops)
    loop2 = parse(ops)
    loop3 = parse(ops.replace("i2 = int_add", "i2 = int_sub"))
    assert equaloplists(loop1.operations, loop2.operations)
    py.test.raises(AssertionError,
                   "equaloplists(loop1.operations, loop3.operations)")

# ____________________________________________________________

class LLtypeMixin(object):
    type_system = 'lltype'

    node_vtable = lltype.malloc(OBJECT_VTABLE, immortal=True)
    node_vtable_adr = llmemory.cast_ptr_to_adr(node_vtable)
    cpu = runner.LLtypeCPU(None)

    NODE = lltype.GcForwardReference()
    NODE.become(lltype.GcStruct('NODE', ('parent', OBJECT),
                                        ('value', lltype.Signed),
                                        ('next', lltype.Ptr(NODE))))
    node = lltype.malloc(NODE)
    nodebox = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, node))
    nodebox2 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, node))
    nodesize = cpu.sizeof(NODE)
    valuedescr = cpu.fielddescrof(NODE, 'value')
    nextdescr = cpu.fielddescrof(NODE, 'next')

    cpu.class_sizes = {cpu.cast_adr_to_int(node_vtable_adr): cpu.sizeof(NODE)}
    namespace = locals()

class OOtypeMixin(object):
    type_system = 'ootype'
    
    cpu = runner.OOtypeCPU(None)

    NODE = ootype.Instance('NODE', ootype.ROOT, {})
    NODE._add_fields({'value': ootype.Signed,
                      'next': NODE})

    node_vtable = ootype.runtimeClass(NODE)
    node_vtable_adr = ootype.cast_to_object(node_vtable)

    node = ootype.new(NODE)
    nodebox = BoxObj(ootype.cast_to_object(node))
    nodebox2 = BoxObj(ootype.cast_to_object(node))
    valuedescr = cpu.fielddescrof(NODE, 'value')
    nextdescr = cpu.fielddescrof(NODE, 'next')
    nodesize = cpu.typedescrof(NODE)

    cpu.class_sizes = {node_vtable_adr: cpu.typedescrof(NODE)}
    namespace = locals()

# ____________________________________________________________

class BaseTestOptimize(object):

    def parse(self, s, boxkinds=None):
        return parse(s, self.cpu, self.namespace,
                     type_system=self.type_system,
                     boxkinds=boxkinds)

    def assert_equal(self, optimized, expected):
        equaloplists(optimized.operations,
                     self.parse(expected).operations)

    def find_nodes(self, ops, boxkinds=None):
        loop = self.parse(ops, boxkinds=boxkinds)
        perfect_specialization_finder.find_nodes(loop)
        return loop.getboxes(), perfect_specialization_finder.getnode

    def test_find_nodes_simple(self):
        ops = """
        [i]
        i0 = int_sub(i, 1)
        guard_value(i0, 0)
          fail(i0)
        jump(i0)
        """
        boxes, getnode = self.find_nodes(ops)
        assert getnode(boxes.i).fromstart
        assert not getnode(boxes.i0).fromstart

    def test_find_nodes_non_escape(self):
        ops = """
        [p0]
        p1 = getfield_gc(p0, descr=nextdescr)
        i0 = getfield_gc(p1, descr=valuedescr)
        i1 = int_sub(i0, 1)
        p2 = getfield_gc(p0, descr=nextdescr)
        setfield_gc(p2, i1, descr=valuedescr)
        jump(p0)
        """
        boxes, getnode = self.find_nodes(ops)
        assert not getnode(boxes.p0).escaped
        assert not getnode(boxes.p1).escaped
        assert not getnode(boxes.p2).escaped
        assert getnode(boxes.p0).fromstart
        assert getnode(boxes.p1).fromstart
        assert getnode(boxes.p2).fromstart

    def test_find_nodes_escape(self):
        ops = """
        [p0]
        p1 = getfield_gc(p0, descr=nextdescr)
        p2 = getfield_gc(p1, descr=nextdescr)
        i0 = getfield_gc(p2, descr=valuedescr)
        i1 = int_sub(i0, 1)
        escape(p1)
        p3 = getfield_gc(p0, descr=nextdescr)
        setfield_gc(p3, i1, descr=valuedescr)
        p4 = getfield_gc(p1, descr=nextdescr)
        setfield_gc(p4, i1, descr=valuedescr)
        jump(p0)
        """
        boxes, getnode = self.find_nodes(ops)
        assert not getnode(boxes.p0).escaped
        assert getnode(boxes.p1).escaped
        assert getnode(boxes.p2).escaped    # forced by p1
        assert getnode(boxes.p3).escaped    # forced because p3 == p1
        assert getnode(boxes.p4).escaped    # forced by p1
        assert getnode(boxes.p0).fromstart
        assert getnode(boxes.p1).fromstart
        assert getnode(boxes.p2).fromstart
        assert getnode(boxes.p3).fromstart
        assert not getnode(boxes.p4).fromstart

    def test_find_nodes_new(self):
        ops = """
        [sum, p1]
        guard_class(p1, ConstClass(node_vtable))
            fail()
        i1 = getfield_gc(p1, descr=valuedescr)
        i2 = int_sub(i1, 1)
        sum2 = int_add(sum, i1)
        p2 = new_with_vtable(ConstClass(node_vtable), descr=nodesize)
        setfield_gc(p2, i2, descr=valuedescr)
        setfield_gc(p2, p2, descr=nextdescr)
        jump(sum2, p2)
        """
        boxes, getnode = self.find_nodes(ops, boxkinds={'sum': BoxInt,
                                                        'sum2': BoxInt})
        assert getnode(boxes.sum) is not getnode(boxes.sum2)
        assert getnode(boxes.p1) is not getnode(boxes.p2)

        boxp1 = getnode(boxes.p1)
        boxp2 = getnode(boxes.p2)
        assert not boxp1.escaped
        assert not boxp2.escaped

        assert not boxp1.curfields
        assert boxp1.origfields[self.valuedescr] is getnode(boxes.i1)
        assert not boxp2.origfields
        assert boxp2.curfields[self.nextdescr] is boxp2

        assert boxp1.fromstart
        assert not boxp2.fromstart


class TestLLtype(BaseTestOptimize, LLtypeMixin):
    pass

class TestOOtype(BaseTestOptimize, OOtypeMixin):
    pass
