from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.jit.metainterp.resume import *
from pypy.jit.metainterp.history import BoxInt, BoxPtr, ConstInt, ConstAddr
from pypy.jit.metainterp.test.test_optimizefindnode import LLtypeMixin
from pypy.jit.metainterp import executor


class Storage:
    pass

def make_demo_storage():
    b1, b2, b3 = [BoxInt(), BoxPtr(), BoxInt()]
    c1, c2, c3 = [ConstInt(1), ConstInt(2), ConstInt(3)]
    storage = Storage()
    builder = ResumeDataBuilder()
    builder.generate_boxes([b1, c1, b1, b2])
    builder.generate_boxes([c2, c3])
    builder.generate_boxes([b1, b2, b3])
    liveboxes = builder.finish(storage)
    assert liveboxes == [b1, b2, b3]
    return storage

# ____________________________________________________________


def test_simple():
    storage = make_demo_storage()
    b1s, b2s, b3s = [BoxInt(), BoxPtr(), BoxInt()]
    assert b1s != b3s
    reader = ResumeDataReader(storage, [b1s, b2s, b3s])
    lst = reader.consume_boxes()
    assert lst == [b1s, ConstInt(1), b1s, b2s]
    lst = reader.consume_boxes()
    assert lst == [ConstInt(2), ConstInt(3)]
    lst = reader.consume_boxes()
    assert lst == [b1s, b2s, b3s]


def test_frame_info():
    storage = Storage()
    #
    builder = ResumeDataBuilder()
    builder.generate_frame_info(1, 2)
    builder.generate_frame_info(3, 4)
    liveboxes = builder.finish(storage)
    assert liveboxes == []
    #
    reader = ResumeDataReader(storage, liveboxes)
    assert reader.has_more_frame_infos()
    fi = reader.consume_frame_info()
    assert fi == (1, 2)
    assert reader.has_more_frame_infos()
    fi = reader.consume_frame_info()
    assert fi == (3, 4)
    assert not reader.has_more_frame_infos()


class MyMetaInterp:
    def execute_and_record(self, opnum, argboxes, descr=None):
        return executor.execute(LLtypeMixin.cpu, opnum, argboxes, descr)


def test_virtual_adder():
    storage = make_demo_storage()
    b1s, b2s, b3s, b4s, b5s = [BoxInt(1), BoxPtr(), BoxInt(3),
                               BoxPtr(), BoxPtr()]
    c1s = ConstInt(111)
    modifier = ResumeDataVirtualAdder(storage, [b1s, b2s, b3s])
    modifier.make_virtual(b2s,
                          ConstAddr(LLtypeMixin.node_vtable_adr,
                                    LLtypeMixin.cpu),
                          LLtypeMixin.nodesize,
                          [LLtypeMixin.nextdescr, LLtypeMixin.valuedescr],
                          [b4s, c1s])   # new fields
    modifier.make_virtual(b4s,
                          ConstAddr(LLtypeMixin.node_vtable_adr2,
                                    LLtypeMixin.cpu),
                          LLtypeMixin.nodesize2,
                          [LLtypeMixin.nextdescr, LLtypeMixin.valuedescr,
                                                  LLtypeMixin.otherdescr],
                          [b2s, b3s, b5s])  # new fields
    # done
    liveboxes = modifier.finish()
    # we get 'liveboxes' in an unspecified order
    sortedliveboxes = liveboxes[:]
    sortedliveboxes.sort(key=lambda box: box.value)
    assert sortedliveboxes == [b1s,
                               #b2s -- virtual
                               b3s,
                               #b4s -- virtual
                               #b2s -- again, shared
                               #b3s -- again, shared
                               b5s]
    #
    demo55 = lltype.malloc(LLtypeMixin.NODE)
    demo55o = lltype.cast_opaque_ptr(llmemory.GCREF, demo55)
    b1t, b3t, b5t = [BoxInt(11), BoxInt(33), BoxPtr(demo55o)]
    newliveboxes = [{b1s:b1t, b3s:b3t, b5s:b5t}[bs] for bs in liveboxes]
    reader = ResumeDataReader(storage, newliveboxes, MyMetaInterp())
    lst = reader.consume_boxes()
    b2t = lst[-1]
    assert lst == [b1t, ConstInt(1), b1t, b2t]
    lst = reader.consume_boxes()
    assert lst == [ConstInt(2), ConstInt(3)]
    lst = reader.consume_boxes()
    assert lst == [b1t, b2t, b3t]
    #
    ptr = b2t.value._obj.container._as_ptr()
    assert lltype.typeOf(ptr) == lltype.Ptr(LLtypeMixin.NODE)
    assert ptr.value == 111
    ptr2 = ptr.next
    ptr2 = lltype.cast_pointer(lltype.Ptr(LLtypeMixin.NODE2), ptr2)
    assert ptr2.other == demo55
    assert ptr2.parent.value == 33
    assert ptr2.parent.next == ptr
