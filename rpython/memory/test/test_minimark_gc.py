from rpython.rlib.rarithmetic import LONG_BIT

from rpython.memory.test.test_semispace_gc import TestSemiSpaceGC

WORD = LONG_BIT // 8

class TestMiniMarkGC(TestSemiSpaceGC):
    from rpython.memory.gc.minimark import MiniMarkGC as GCClass
    GC_CAN_SHRINK_BIG_ARRAY = False
    GC_CAN_MALLOC_NONMOVABLE = True
    BUT_HOW_BIG_IS_A_BIG_STRING = 11*WORD

    def test_finalizer_called_by_minor_collection(self):
        class B(object):
            pass
        b = B()
        b.num_finalized = 0
        class A(object):
            def finalizer(self):
                b.num_finalized += 1
        def allocate(x):
            i = 0
            while i < x:
                i += 1
                a = A()
                a.foobar = i     # every A is at least two word long
                rgc.register_finalizer(a.finalizer)
        def f(x):
            allocate(x)
            return b.num_finalized
        res = self.interpret(f, [32])
        assert 14 <= res <= 32

    def test_finalizer_on_object_becoming_old(self):
        class B(object):
            pass
        b = B()
        b.num_finalized = 0
        class A(object):
            def finalizer(self):
                b.num_finalized += 1
        def allocate(x):
            a = A()
            rgc.register_finalizer(a.finalizer)
            llop.gc__collect(lltype.Void)
            a.foobar = x
        def f(x):
            allocate(x)
            n = b.num_finalized
            llop.gc__collect(lltype.Void)
            return n * 100 + b.num_finalized
        res = self.interpret(f, [42])
        assert res == 1

    def test_finalizer_registered_on_old_object(self):
        class B(object):
            pass
        b = B()
        b.num_finalized = 0
        class A(object):
            def finalizer(self):
                b.num_finalized += 1
        def allocate():
            a = A()
            llop.gc__collect(lltype.Void)
            rgc.register_finalizer(a.finalizer)
        def f():
            allocate()
            n = b.num_finalized
            llop.gc__collect(lltype.Void)
            return n * 100 + b.num_finalized
        res = self.interpret(f, [])
        assert res == 1
