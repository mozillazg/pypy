import py
from rpython.rtyper.lltypesystem import lltype
from rpython.rlib.rawstorage import alloc_raw_storage, free_raw_storage,\
     raw_storage_setitem, raw_storage_getitem, AlignmentError,\
     raw_storage_setitem_unaligned, raw_storage_getitem_unaligned
from rpython.rtyper.test.tool import BaseRtypingTest

def test_untranslated_storage():
    r = alloc_raw_storage(37)
    raw_storage_setitem(r, 8, 1<<30)
    res = raw_storage_getitem(lltype.Signed, r, 8)
    assert res == 1<<30
    raw_storage_setitem(r, 8, 3.14)
    res = raw_storage_getitem(lltype.Float, r, 8)
    assert res == 3.14
    py.test.raises(AlignmentError, raw_storage_getitem, lltype.Signed, r, 3)
    py.test.raises(AlignmentError, raw_storage_setitem, r, 3, 42.5)
    free_raw_storage(r)

def test_untranslated_storage_unaligned():
    r = alloc_raw_storage(15)
    raw_storage_setitem_unaligned(r, 3, 1<<30)
    res = raw_storage_getitem_unaligned(lltype.Signed, r, 3)
    assert res == 1<<30
    raw_storage_setitem_unaligned(r, 3, 3.14)
    res = raw_storage_getitem_unaligned(lltype.Float, r, 3)
    assert res == 3.14
    free_raw_storage(r)

class TestRawStorage(BaseRtypingTest):
    def test_storage_int(self):
        def f(i):
            r = alloc_raw_storage(24)
            raw_storage_setitem(r, 8, i)
            res = raw_storage_getitem(lltype.Signed, r, 8)
            free_raw_storage(r)
            return res
        x = self.interpret(f, [1<<30])
        assert x == 1 << 30

    def test_storage_float_unaligned(self):
        def f(v):
            r = alloc_raw_storage(24)
            raw_storage_setitem_unaligned(r, 3, v)
            res = raw_storage_getitem_unaligned(lltype.Float, r, 3)
            free_raw_storage(r)
            return res
        x = self.interpret(f, [3.14])
        assert x == 3.14
