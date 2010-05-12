
from pypy.rpython.lltypesystem import rlist as ll_rlist
from pypy.rpython.rlist import ADTIList
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rpython.lltypesystem.lltype import GcStruct, Signed, Ptr, GcArray

class TestRListDirect(object):
    def setup_class(cls):
        cls.MIN_CHUNKED_SIZE = ll_rlist.MIN_CHUNKED_SIZE
        cls.CHUNK_SIZE = ll_rlist.CHUNK_SIZE
        ll_rlist.MIN_CHUNKED_SIZE = 100
        ll_rlist.CHUNK_SIZE = 100

        ITEM = lltype.Signed
        ITEMARRAY = lltype.GcArray(ITEM)

        cls.LISTTP = GcStruct("list", ("length", Signed),
                              ("items", Ptr(ITEMARRAY)),
                              adtmeths = ADTIList({
                                  "ll_newlist": ll_rlist.ll_newlist,
                                  "ll_newemptylist": ll_rlist.ll_newemptylist,
                                  "ll_length": ll_rlist.ll_length,
                                  "ll_items": ll_rlist.ll_items,
                                  "ll_chunks": ll_rlist.ll_chunks,
                                  "ITEM": ITEM,
                                  "ll_getitem_fast": ll_rlist.ll_getitem_fast,
                                  "ll_setitem_fast": ll_rlist.ll_setitem_fast,
                                  "_ll_resize_ge": ll_rlist._ll_list_resize_ge,
                                  "_ll_resize_le": ll_rlist._ll_list_resize_le,
                                  "_ll_resize": ll_rlist._ll_list_resize,
                                  }),
                              hints = {'list': True})

    def teardown_class(cls):
        ll_rlist.MIN_CHUNKED_SIZE = cls.MIN_CHUNKED_SIZE
        ll_rlist.CHUNK_SIZE = cls.CHUNK_SIZE
    
    def test_resize_unchunked_chunked(self):
        l = self.LISTTP.ll_newlist(ll_rlist.MIN_CHUNKED_SIZE - 3)
        for i in range(l.length):
            l.ll_setitem_fast(i, i)
        l._ll_resize(ll_rlist.MIN_CHUNKED_SIZE + 10)
        for i in range(ll_rlist.MIN_CHUNKED_SIZE - 3,
                       ll_rlist.MIN_CHUNKED_SIZE + 10):
            l.ll_setitem_fast(i, 10*i)
        # this should resize above the chunked threshold
        CHUNK_TP = Ptr(GcArray(Ptr(GcArray(Signed))))
        chunked_items = rffi.cast(CHUNK_TP, l.items)
        CHUNK_SIZE = ll_rlist.CHUNK_SIZE
        assert chunked_items[0][10] == 10
        assert chunked_items[0][CHUNK_SIZE - 1] == (CHUNK_SIZE - 1) * 10
        assert chunked_items[1][0] == CHUNK_SIZE * 10
        assert chunked_items[1][9] == (CHUNK_SIZE + 9) * 10
