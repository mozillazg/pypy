from pypy.jit.metainterp.memmgr import MemoryManager
from pypy.jit.metainterp.test.test_basic import LLJitMixin
from pypy.rlib.jit import JitDriver


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
        memmgr.set_max_age(4, 1)
        tokens = [FakeLoopToken() for i in range(10)]
        for token in tokens:
            memmgr.keep_loop_alive(token)
            memmgr.next_generation()
        assert memmgr.alive_loops == dict.fromkeys(tokens[7:])

    def test_basic_2(self):
        memmgr = MemoryManager()
        memmgr.set_max_age(4, 1)
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
        memmgr.set_max_age(4, 1)
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


class TestIntegration(LLJitMixin):

    def test_loop_kept_alive(self):
        myjitdriver = JitDriver(greens=[], reds=['n'])
        def g():
            n = 10
            while n > 0:
                myjitdriver.can_enter_jit(n=n)
                myjitdriver.jit_merge_point(n=n)
                n = n - 1
            return 21
        def f():
            for i in range(15):
                g()
            return 42

        res = self.meta_interp(f, [], loop_longevity=2)
        assert res == 42

        # we should see only the loop and the entry bridge
        self.check_tree_loop_count(2)

    def test_target_loop_kept_alive_or_not(self):
        myjitdriver = JitDriver(greens=['m'], reds=['n'])
        def g(m):
            n = 10
            while n > 0:
                myjitdriver.can_enter_jit(n=n, m=m)
                myjitdriver.jit_merge_point(n=n, m=m)
                n = n - 1
            return 21
        def f():
            # Depending on loop_longevity, either:
            # A. create the loop and the entry bridge for 'g(5)'
            # B. create 8 loops (and throw them away at each iteration)
            for i in range(8):
                g(5)
            # create another loop and another entry bridge for 'g(7)',
            # to increase the current_generation
            for i in range(20):
                g(7)
                # Depending on loop_longevity, either:
                # A. reuse the existing loop and entry bridge for 'g(5)'.
                #    The entry bridge for g(5) should never grow too old.
                #    The loop itself gets old, but is kept alive by the
                #    entry bridge via contains_jumps_to.
                # B. or, create another loop (and throw away the previous one)
                g(5)
            return 42

        # case A
        res = self.meta_interp(f, [], loop_longevity=3)
        assert res == 42
        # we should see only the loop and the entry bridge for g(5) and g(7)
        self.check_tree_loop_count(4)

        # case B, with a lower longevity
        res = self.meta_interp(f, [], loop_longevity=1)
        assert res == 42
        # we should see a loop for each call to g()
        self.check_tree_loop_count(8 + 20*2)

    def test_throw_away_old_loops(self):
        myjitdriver = JitDriver(greens=['m'], reds=['n'])
        def g(m):
            n = 10
            while n > 0:
                myjitdriver.can_enter_jit(n=n, m=m)
                myjitdriver.jit_merge_point(n=n, m=m)
                n = n - 1
            return 21
        def f():
            for i in range(10):
                g(1)   # g(1) gets a loop and an entry bridge, stays alive
                g(2)   # (and an exit bridge, which does not count in
                g(1)   # check_tree_loop_count)
                g(3)
                g(1)
                g(4)   # g(2), g(3), g(4), g(5) are thrown away every iteration
                g(1)   # (no entry bridge for them)
                g(5)
            return 42

        res = self.meta_interp(f, [], loop_longevity=3)
        assert res == 42
        self.check_tree_loop_count(2 + 10*4)   # 42 :-)
