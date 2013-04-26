from rpython.rtyper.lltypesystem import lltype
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.memory.gc.minimark import WORD

from rpython.memory.test import test_minimark_gc

class TestMiniMarkGCCardMarking(test_minimark_gc.TestMiniMarkGC):
    GC_PARAMS = {'card_page_indices': 4}

    def test_finalizer_with_card_marks_array(self):
        class B(object):
            pass
        b = B()
        b.num_finalized = 0
        class A(object):
            def __init__(self, id, next):
                self.id = id
                self.next = next
                rgc.register_finalizer(self.finalizer)
            def finalizer(self):
                assert b.num_finalized == self.id
                b.num_finalized += 1
        def allocate(x):
            lst = [None] * 10
            a0 = A(0, lst)
            a1 = A(1, None)
            lst[6] = a1
            keepalive_until_here(a0)
        def f(x):
            allocate(x)
            llop.gc__collect(lltype.Void)
            llop.gc__collect(lltype.Void)
            return b.num_finalized
        res = self.interpret(f, [2])
        assert res == 2


class TestMiniMarkGCLargeNursery(test_minimark_gc.TestMiniMarkGC):
    GC_PARAMS = {'nursery_size': 16384*WORD}
    def setup_class(cls):
        py.test.skip("takes a lot of extra time to run")
    def teardown_class(cls):
        pass
