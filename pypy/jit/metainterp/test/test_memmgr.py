from pypy.jit.metainterp.memmgr import MemoryManager
from pypy.jit.metainterp.history import LoopToken

##missing:

##    in _free_old_loops_now(), remove looptoken from everywhere
##    or mark it as freed

##    contains_jumps_to needs to be filled


class FakeCPU:
    def free_loop_and_bridges(self, looptoken):
        looptoken.has_been_freed = True
cpu = FakeCPU()


class TestMemoryManager:

    def test_disabled(self):
        memmgr = MemoryManager(cpu)
        memmgr.set_max_age(0)
        tokens = [LoopToken() for i in range(10)]
        for token in tokens:
            memmgr.record_loop(token)
            memmgr.next_generation()
        for token in tokens:
            assert not token.has_been_freed

    def test_basic(self):
        memmgr = MemoryManager(cpu)
        memmgr.set_max_age(3, 1)
        tokens = [LoopToken() for i in range(10)]
        for token in tokens:
            memmgr.record_loop(token)
            memmgr.next_generation()
        for i in range(len(tokens)):
            assert tokens[i].has_been_freed == (i < 7)

    def test_basic_2(self):
        memmgr = MemoryManager(cpu)
        memmgr.set_max_age(3, 1)
        token = LoopToken()
        memmgr.record_loop(token)
        for i in range(10):
            memmgr.next_generation()
            assert token.has_been_freed == (i >= 3)

    def test_enter_loop_1(self):
        memmgr = MemoryManager(cpu)
        memmgr.set_max_age(3, 1)
        tokens = [LoopToken() for i in range(10)]
        for i in range(len(tokens)):
            print 'record tokens[%d]' % i
            memmgr.record_loop(tokens[i])
            memmgr.next_generation()
            for j in range(0, i, 2):
                assert not tokens[j].has_been_freed
                print 'enter and leave tokens[%d]' % j
                memmgr.enter_loop(tokens[j])
                memmgr.leave_loop(tokens[j])
        for i in range(len(tokens)):
            assert tokens[i].has_been_freed == (i < 7 and (i%2) != 0)

    def test_enter_loop_2(self):
        memmgr = MemoryManager(cpu)
        memmgr.set_max_age(3, 1)
        tokens = [LoopToken() for i in range(10)]
        for i in range(len(tokens)):
            print 'record tokens[%d]' % i
            memmgr.record_loop(tokens[i])
            memmgr.next_generation()
            for j in range(i-2, i+1):
                if j >= 0:
                    assert not tokens[j].has_been_freed
                    print 'enter and leave tokens[%d]' % j
                    memmgr.enter_loop(tokens[j])
                    memmgr.leave_loop(tokens[j])
        for i in range(len(tokens)):
            assert tokens[i].has_been_freed == (i < 4)

    def test_loop_is_running(self):
        memmgr = MemoryManager(cpu)
        memmgr.set_max_age(3, 1)
        token = LoopToken()
        memmgr.record_loop(token)
        memmgr.enter_loop(token)
        for i in range(10):
            memmgr.next_generation()
            assert token.has_been_freed == False
        memmgr.leave_loop(token)
        for i in range(10):
            memmgr.next_generation()
            assert token.has_been_freed == (i >= 3)

    def test_nested_enter_loop(self):
        memmgr = MemoryManager(cpu)
        memmgr.set_max_age(3, 1)
        token = LoopToken()
        memmgr.record_loop(token)
        memmgr.enter_loop(token)
        # here we recursively end up seeing the same token again
        memmgr.enter_loop(token)
        for i in range(10):
            memmgr.next_generation()
            assert token.has_been_freed == False
        memmgr.leave_loop(token)
        # out of the recursive call, but the loop is still "locked"
        for i in range(10):
            memmgr.next_generation()
            assert token.has_been_freed == False
        memmgr.leave_loop(token)
        for i in range(10):
            memmgr.next_generation()
            assert token.has_been_freed == (i >= 3)

    def test_contains_jumps_to(self):
        memmgr = MemoryManager(cpu)
        memmgr.set_max_age(3, 1)
        token1 = LoopToken()
        token2 = LoopToken()
        token1.contains_jumps_to[token2] = None
        memmgr.record_loop(token1)
        memmgr.record_loop(token2)
        memmgr.enter_loop(token1)
        for i in range(10):
            memmgr.next_generation()
            assert token1.has_been_freed == False
            assert token2.has_been_freed == False
        memmgr.leave_loop(token1)
        for i in range(10):
            memmgr.next_generation()
            assert token1.has_been_freed == (i >= 3)
            assert token2.has_been_freed == (i >= 3)

    def test_contains_jumps_to_2(self):
        memmgr = MemoryManager(cpu)
        memmgr.set_max_age(3, 1)
        token1 = LoopToken()
        token2 = LoopToken()
        token3 = LoopToken()
        token1.contains_jumps_to[token2] = None
        token2.contains_jumps_to[token3] = None
        memmgr.record_loop(token1)
        memmgr.record_loop(token2)
        memmgr.record_loop(token3)
        memmgr.enter_loop(token1)
        for i in range(10):
            memmgr.next_generation()
            assert token1.has_been_freed == False
            assert token2.has_been_freed == False
            assert token3.has_been_freed == False
        memmgr.leave_loop(token1)
        for i in range(10):
            memmgr.next_generation()
            assert token1.has_been_freed == (i >= 3)
            assert token2.has_been_freed == (i >= 3)
            assert token3.has_been_freed == (i >= 3)
