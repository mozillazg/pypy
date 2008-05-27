
from pypy.module.thread.ll_thread import *
from pypy.translator.c.test.test_boehm import AbstractGCTestClass
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rlib.objectmodel import free_non_gc_object
import py

def test_lock():
    l = allocate_lock()
    ok1 = l.acquire(True)
    ok2 = l.acquire(False)
    l.release()
    ok3 = l.acquire(False)
    res = ok1 and not ok2 and ok3
    assert res == 1

def test_thread_error():
    l = allocate_lock()
    try:
        l.release()
    except error:
        pass
    else:
        py.test.fail("Did not raise")

def test_fused():
    l = allocate_lock_NOAUTO()
    l.acquire(True)
    l.fused_release_acquire()
    could_acquire_again = l.acquire(False)
    assert not could_acquire_again
    l.release()
    could_acquire_again = l.acquire(False)
    assert could_acquire_again


class TestUsingBoehm(AbstractGCTestClass):
    gcpolicy = 'boehm'

    def test_start_new_thread(self):
        import time

        class State:
            pass
        state = State()

        class Z:
            def __init__(self, value):
                self.value = value
            def __del__(self):
                state.freed_counter += 1

        class Y:
            _alloc_flavor_ = 'raw'

            def bootstrap(self):
                state.my_thread_ident = get_ident()
                assert state.my_thread_ident == get_ident()
                state.seen_value = self.z.value
                self.z = None
                free_non_gc_object(self)
                state.done = 1

        def g(i):
            y = Y()
            y.z = Z(i)
            start_new_thread(Y.bootstrap, (y,))
        g._dont_inline_ = True

        def f():
            main_ident = get_ident()
            assert main_ident == get_ident()
            state.freed_counter = 0
            for i in range(50):
                state.done = 0
                state.seen_value = 0
                g(i)
                willing_to_wait_more = 1000
                while not state.done:
                    willing_to_wait_more -= 1
                    if not willing_to_wait_more:
                        raise Exception("thread didn't start?")
                    time.sleep(0.01)
                assert state.my_thread_ident != main_ident
                assert state.seen_value == i
            # try to force Boehm to do some freeing
            for i in range(3):
                llop.gc__collect(lltype.Void)
            return state.freed_counter

        fn = self.getcompiled(f, [])
        freed_counter = fn()
        print freed_counter
        if self.gcpolicy == 'boehm':
            assert freed_counter > 0
        else:
            assert freed_counter == 50

    def test_gc_locking(self):
        import time

        class State:
            pass
        state = State()

        class Z:
            def __init__(self, i, j):
                self.i = i
                self.j = j
            def run(self):
                j = self.j
                state.gil.acquire(True)
                assert j == self.j
                if self.i > 1:
                    g(self.i-1, self.j * 2)
                    g(self.i-2, self.j * 2 + 1)
                else:
                    state.answers.append(self.i)
                assert j == self.j
                state.gil.release()
                assert j == self.j
            run._dont_inline_ = True

        class Y(object):
            _alloc_flavor_ = 'raw'
            def bootstrap(self):
                self.z.run()
                self.z = None
                free_non_gc_object(self)
                state.done = 1

        def g(i, j):
            y = Y()
            y.z = Z(i, j)
            start_new_thread(Y.bootstrap, (y,))
        g._dont_inline_ = True

        def f():
            state.gil = allocate_lock_NOAUTO()
            state.answers = []
            state.finished = 0
            g(7, 1)
            done = False
            willing_to_wait_more = 1000
            while not done:
                if not willing_to_wait_more:
                    raise Exception("didn't get enough answers: got %d,"
                                    " expected %d" % (len(state.answers),
                                                      expected))
                willing_to_wait_more -= 1
                state.gil.acquire(True)
                done = len(state.answers) == expected
                state.gil.release()
                time.sleep(0.01)
            time.sleep(0.1)
            return len(state.answers)

        expected = 21
        fn = self.getcompiled(f, [])
        answers = fn()
        assert answers == expected

class TestUsingFramework(TestUsingBoehm):
    gcpolicy = 'generation'

    def test_gc_locking(self):
        py.test.skip("in-progress")
