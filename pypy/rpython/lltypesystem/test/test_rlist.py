
from pypy.rpython.lltypesystem import rlist as ll_rlist
from pypy.rpython.rlist import ADTIList
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.lltypesystem.lltype import GcStruct, Signed, Ptr

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
        l = self.LISTTP.ll_newlist(self.CHUNK_SIZE - 3)
