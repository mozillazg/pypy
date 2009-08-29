import random
from pypy.rpython.lltypesystem import lltype, llmemory, rffi, rstr
from pypy.jit.backend.llsupport.descr import *
from pypy.jit.backend.llsupport.gc import *
from pypy.jit.backend.llsupport import symbolic
from pypy.jit.metainterp.gc import get_description


def test_boehm():
    gc_ll_descr = GcLLDescr_boehm(None, None)
    #
    record = []
    prev_funcptr_for_new = gc_ll_descr.funcptr_for_new
    def my_funcptr_for_new(size):
        p = prev_funcptr_for_new(size)
        record.append((size, p))
        return p
    gc_ll_descr.funcptr_for_new = my_funcptr_for_new
    #
    # ---------- gc_malloc ----------
    S = lltype.GcStruct('S', ('x', lltype.Signed))
    sizedescr = get_size_descr(gc_ll_descr, S)
    p = gc_ll_descr.gc_malloc(sizedescr)
    assert record == [(sizedescr.size, p)]
    del record[:]
    # ---------- gc_malloc_array ----------
    A = lltype.GcArray(lltype.Signed)
    arraydescr = get_array_descr(gc_ll_descr, A)
    p = gc_ll_descr.gc_malloc_array(arraydescr, 10)
    assert record == [(arraydescr.get_base_size(False) +
                       10 * arraydescr.get_item_size(False), p)]
    del record[:]
    # ---------- gc_malloc_str ----------
    p = gc_ll_descr.gc_malloc_str(10)
    basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR, False)
    assert record == [(basesize + 10 * itemsize, p)]
    del record[:]
    # ---------- gc_malloc_unicode ----------
    p = gc_ll_descr.gc_malloc_unicode(10)
    basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.UNICODE,
                                                              False)
    assert record == [(basesize + 10 * itemsize, p)]
    del record[:]

# ____________________________________________________________

def test_GcRefList():
    S = lltype.GcStruct('S')
    order = range(50) * 4
    random.shuffle(order)
    allocs = [lltype.cast_opaque_ptr(llmemory.GCREF, lltype.malloc(S))
              for i in range(50)]
    allocs = [allocs[i] for i in order]
    #
    gcrefs = GcRefList()
    addrs = [gcrefs.get_address_of_gcref(ptr) for ptr in allocs]
    for i in range(len(allocs)):
        assert addrs[i].address[0] == llmemory.cast_ptr_to_adr(allocs[i])

def test_GcRootMap_asmgcc():
    def stack_pos(n):
        return -4*(4+n)
    gcrootmap = GcRootMap_asmgcc()
    num1 = stack_pos(1)
    num2 = stack_pos(55)
    shape = gcrootmap._get_callshape([num1, num2])
    assert shape == [6, -2, -6, -10, 2, 0, num1|2, num2|2]
    #
    shapeaddr = gcrootmap.encode_callshape([num1, num2])
    PCALLSHAPE = lltype.Ptr(GcRootMap_asmgcc.CALLSHAPE_ARRAY)
    p = llmemory.cast_adr_to_ptr(shapeaddr, PCALLSHAPE)
    num1a = -2*(num1|2)-1
    num2a = ((-2*(num2|2)-1) >> 7) | 128
    num2b = (-2*(num2|2)-1) & 127
    for i, expected in enumerate([num2a, num2b, num1a, 0, 4, 19, 11, 3, 12]):
        assert p[i] == expected
    #
    retaddr = rffi.cast(llmemory.Address, 1234567890)
    gcrootmap.put(retaddr, shapeaddr)
    assert gcrootmap._gcmap[0] == retaddr
    assert gcrootmap._gcmap[1] == shapeaddr
    assert gcrootmap.gcmapstart().address[0] == retaddr
    #
    # the same as before, but enough times to trigger a few resizes
    expected_shapeaddr = {}
    for i in range(1, 600):
        shapeaddr = gcrootmap.encode_callshape([stack_pos(i)])
        expected_shapeaddr[i] = shapeaddr
        retaddr = rffi.cast(llmemory.Address, 123456789 + i)
        gcrootmap.put(retaddr, shapeaddr)
    for i in range(1, 600):
        expected_retaddr = rffi.cast(llmemory.Address, 123456789 + i)
        assert gcrootmap._gcmap[i*2+0] == expected_retaddr
        assert gcrootmap._gcmap[i*2+1] == expected_shapeaddr[i]


class FakeLLOp:
    def __init__(self):
        self.record = []

    def do_malloc_fixedsize_clear(self, RESTYPE, type_id, size, can_collect,
                                  has_finalizer, contains_weakptr):
        assert can_collect
        assert not contains_weakptr
        p = llmemory.raw_malloc(size)
        p = llmemory.cast_adr_to_ptr(p, RESTYPE)
        self.record.append(("fixedsize", type_id, repr(size),
                            has_finalizer, p))
        return p

    def do_malloc_varsize_clear(self, RESTYPE, type_id, length, size,
                                itemsize, offset_to_length, can_collect,
                                has_finalizer):
        assert can_collect
        assert not has_finalizer
        p = llmemory.raw_malloc(size + itemsize * length)
        (p + offset_to_length).signed[0] = length
        p = llmemory.cast_adr_to_ptr(p, RESTYPE)
        self.record.append(("varsize", type_id, length,
                            repr(size), repr(itemsize),
                            repr(offset_to_length), p))
        return p


def test_framework_malloc():
    class FakeTranslator:
        pass
    class config:
        class translation:
            gc = 'hybrid'
            gcrootfinder = 'asmgcc'
            gctransformer = 'framework'
    gcdescr = get_description(config)
    translator = FakeTranslator()
    llop1 = FakeLLOp()
    gc_ll_descr = GcLLDescr_framework(gcdescr, FakeTranslator(), llop1)
    #
    # ---------- gc_malloc ----------
    S = lltype.GcStruct('S', ('x', lltype.Signed))
    sizedescr = get_size_descr(gc_ll_descr, S)
    p = gc_ll_descr.gc_malloc(sizedescr)
    assert llop1.record == [("fixedsize", sizedescr.type_id,
                             repr(sizedescr.size), False, p)]
    del llop1.record[:]
    # ---------- gc_malloc_array ----------
    A = lltype.GcArray(lltype.Signed)
    arraydescr = get_array_descr(gc_ll_descr, A)
    p = gc_ll_descr.gc_malloc_array(arraydescr, 10)
    assert llop1.record == [("varsize", arraydescr.type_id, 10,
                             repr(arraydescr.get_base_size(True)),
                             repr(arraydescr.get_item_size(True)),
                             repr(arraydescr.get_ofs_length(True)), p)]
    del llop1.record[:]
    # ---------- gc_malloc_str ----------
    p = gc_ll_descr.gc_malloc_str(10)
    type_id = gc_ll_descr.layoutbuilder.get_type_id(rstr.STR)
    basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR, True)
    assert llop1.record == [("varsize", type_id, 10,
                             repr(basesize), repr(itemsize), repr(ofs_length),
                             p)]
    del llop1.record[:]
    # ---------- gc_malloc_unicode ----------
    p = gc_ll_descr.gc_malloc_unicode(10)
    type_id = gc_ll_descr.layoutbuilder.get_type_id(rstr.UNICODE)
    basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.UNICODE,
                                                              True)
    assert llop1.record == [("varsize", type_id, 10,
                             repr(basesize), repr(itemsize), repr(ofs_length),
                             p)]
    del llop1.record[:]
