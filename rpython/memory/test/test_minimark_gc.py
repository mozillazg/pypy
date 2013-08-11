from rpython.rlib import rgc
from rpython.rlib.debug import ll_assert
from rpython.rlib.objectmodel import keepalive_until_here
from rpython.rlib.rarithmetic import LONG_BIT

from rpython.memory.test import test_semispace_gc

WORD = LONG_BIT // 8

class TestMiniMarkGC(test_semispace_gc.TestSemiSpaceGC):
    from rpython.memory.gc.minimark import MiniMarkGC as GCClass
    GC_CAN_SHRINK_BIG_ARRAY = False
    GC_CAN_MALLOC_NONMOVABLE = True
    BUT_HOW_BIG_IS_A_BIG_STRING = 11*WORD

    def test_finalizer_young_obj(self):
        class A:
            def __del__(self):
                state.seen += 1
        class State:
            pass
        state = State()

        def f():
            state.seen = 0
            A(); A()
            rgc.collect(0)    # minor collection only
            return state.seen

        assert self.interpret(f, []) == 2

    def test_finalizer_chain_minor_collect(self):
        class A:
            def __init__(self, n, next):
                self.n = n
                self.next = next
            def __del__(self):
                state.freed.append(self.n)
        class State:
            pass
        state = State()

        def make(n):
            a = None
            i = 0
            while i < n:
                a = A(i, a)
                i += 1

        def f(n):
            state.freed = []
            make(n)
            ll_assert(len(state.freed) == 0, "should be empty before collect")
            i = 0
            while i < n:
                rgc.collect(0)    # minor collection only
                i += 1
                ll_assert(len(state.freed) == i, "every collect should grow 1")
            i = 0
            while i < n:
                ll_assert(state.freed[i] == n - i - 1, "bogus ordering")
                i += 1

        self.interpret(f, [4])

    def test_finalizer_chain_minor_collect_old(self):
        class A:
            def __init__(self, n, next):
                self.n = n
                self.next = next
            def __del__(self):
                state.freed.append(self.n)
        class State:
            pass
        state = State()

        def make(n):
            a = None
            i = 0
            while i < n:
                a = A(i, a)
                i += 1
            rgc.collect()     # make all objects old
            keepalive_until_here(a)

        def f(n):
            state.freed = []
            make(n)
            ll_assert(len(state.freed) == 0, "should be empty before collect")
            rgc.collect()       # need a full collection to initiate deletion
            ll_assert(len(state.freed) == 1, "should be 1 after first collect")
            i = 1
            while i < n:
                rgc.collect(0)    # minor collection only
                i += 1
                ll_assert(len(state.freed) == i, "every collect should grow 1")
            i = 0
            while i < n:
                ll_assert(state.freed[i] == n - i - 1, "bogus ordering")
                i += 1

        self.interpret(f, [4])
