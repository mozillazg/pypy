import gc
from pypy.module.thread.ll_thread import *
from pypy.translator.c.test.test_boehm import AbstractGCTestClass
from pypy.rpython.lltypesystem import lltype, rffi
import py

def setup_module(mod):
    # Hack to avoid a deadlock if the module is run after other test files :-(
    # In this module, we assume that ll_thread.start_new_thread() is not
    # providing us with a GIL equivalent.
    rffi.aroundstate._freeze_()

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


class AbstractThreadTests(AbstractGCTestClass):
    use_threads = True

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

        def bootstrap():
            state.my_thread_ident = get_ident()
            assert state.my_thread_ident == get_ident()
            state.seen_value = state.z.value
            state.z = None
            state.done = 1

        def g(i):
            state.z = Z(i)
            start_new_thread(bootstrap, ())
        g._dont_inline_ = True

        def f():
            main_ident = get_ident()
            assert main_ident == get_ident()
            state.freed_counter = 0
            for i in range(50):
                state.done = 0
                state.seen_value = 0
                g(i)
                gc.collect()
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
                gc.collect()
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
                if self.i > 1:
                    g(self.i-1, self.j * 2)
                    assert j == self.j
                    g(self.i-2, self.j * 2 + 1)
                else:
                    if len(state.answers) % 7 == 5:
                        gc.collect()
                    state.answers.append(self.j)
                assert j == self.j
            run._dont_inline_ = True

        def bootstrap():
            acquire_NOAUTO(state.gil, True)
            gc_thread_run()
            z = state.z
            state.z = None
            z.run()
            gc_thread_die()
            release_NOAUTO(state.gil)

        def g(i, j):
            state.z = Z(i, j)
            gc_thread_prepare()
            start_new_thread(bootstrap, ())
            # now wait until the new thread really started and consumed 'z'
            willing_to_wait_more = 1000
            while state.z is not None:
                assert willing_to_wait_more > 0
                willing_to_wait_more -= 1
                release_NOAUTO(state.gil)
                time.sleep(0.005)
                acquire_NOAUTO(state.gil, True)
                gc_thread_run()

        def f():
            state.gil = allocate_ll_lock()
            acquire_NOAUTO(state.gil, True)
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
                done = len(state.answers) == expected
                release_NOAUTO(state.gil)
                time.sleep(0.01)
                acquire_NOAUTO(state.gil, True)
                gc_thread_run()
            release_NOAUTO(state.gil)
            time.sleep(0.1)
            return len(state.answers)

        expected = 21
        fn = self.getcompiled(f, [])
        answers = fn()
        assert answers == expected

class TestRunDirectly(AbstractThreadTests):
    def getcompiled(self, f, argtypes):
        return f

class TestUsingBoehm(AbstractThreadTests):
    gcpolicy = 'boehm'

class TestUsingFramework(AbstractThreadTests):
    gcpolicy = 'generation'
