from pypy.jit.metainterp.memmgr import MemoryManager

##missing:
##    contains_jumps_to needs to be filled


class FakeLoopToken:
    generation = 0


class TestMemoryManager:

    def test_disabled(self):
        memmgr = MemoryManager()
        memmgr.set_max_age(0)
        tokens = [FakeLoopToken() for i in range(10)]
        for token in tokens:
            memmgr.keep_loop_alive(token)
            memmgr.next_generation()
        assert memmgr.alive_loops == dict.fromkeys(tokens)

    def test_basic(self):
        memmgr = MemoryManager()
        memmgr.set_max_age(3, 1)
        tokens = [FakeLoopToken() for i in range(10)]
        for token in tokens:
            memmgr.keep_loop_alive(token)
            memmgr.next_generation()
        assert memmgr.alive_loops == dict.fromkeys(tokens[7:])

    def test_basic_2(self):
        memmgr = MemoryManager()
        memmgr.set_max_age(3, 1)
        token = FakeLoopToken()
        memmgr.keep_loop_alive(token)
        for i in range(10):
            memmgr.next_generation()
            if i < 3:
                assert memmgr.alive_loops == {token: None}
            else:
                assert memmgr.alive_loops == {}

    def test_basic_3(self):
        memmgr = MemoryManager()
        memmgr.set_max_age(3, 1)
        tokens = [FakeLoopToken() for i in range(10)]
        for i in range(len(tokens)):
            print 'record tokens[%d]' % i
            memmgr.keep_loop_alive(tokens[i])
            memmgr.next_generation()
            for j in range(0, i, 2):
                assert tokens[j] in memmgr.alive_loops
                print 'also keep alive tokens[%d]' % j
                memmgr.keep_loop_alive(tokens[j])
        for i in range(len(tokens)):
            if i < 7 and (i%2) != 0:
                assert tokens[i] not in memmgr.alive_loops
            else:
                assert tokens[i] in memmgr.alive_loops
