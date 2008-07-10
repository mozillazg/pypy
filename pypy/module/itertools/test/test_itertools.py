from pypy.conftest import gettestobjspace

class AppTestItertools: 
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['itertools'])

    def test_iterables(self):
        import itertools

        iterables = [
            itertools.count(),
            itertools.repeat(None),
            itertools.takewhile(bool, []),
            ]

        for it in iterables:
            assert hasattr(it, '__iter__')
            assert iter(it) is it
            assert hasattr(it, 'next')
            assert callable(it.next)

    def test_count(self):
        import itertools

        c = itertools.count()
        for x in range(10):
            assert c.next() == x

    def test_count_firstval(self):
        import itertools

        c = itertools.count(3)
        for x in range(10):
            assert c.next() == x + 3

    def test_count_overflow(self):
        import itertools, sys

        c = itertools.count(sys.maxint)
        assert c.next() == sys.maxint
        raises(OverflowError, c.next) 
        raises(OverflowError, c.next) 

        raises(OverflowError, itertools.count, sys.maxint + 1)

    def test_repeat(self):
        import itertools

        o = object()
        r = itertools.repeat(o)

        for x in range(10):
            assert o is r.next()

    def test_repeat_times(self):
        import itertools

        times = 10
        r = itertools.repeat(None, times=times)
        for i in range(times):
            r.next()
        raises(StopIteration, r.next)

        r = itertools.repeat(None, times=None)
        for x in range(10):
            r.next()    # Should be no StopIteration

        r = itertools.repeat(None, times=0)
        raises(StopIteration, r.next)
        raises(StopIteration, r.next)

        r = itertools.repeat(None, times=-1)
        raises(StopIteration, r.next)
        raises(StopIteration, r.next)

    def test_repeat_overflow(self):
        import itertools
        import sys

        raises(OverflowError, itertools.repeat, None, sys.maxint + 1)

    def test_takewhile(self):
        import itertools

        tw = itertools.takewhile(bool, [])
        raises(StopIteration, tw.next)

        tw = itertools.takewhile(bool, [False, True, True])
        raises(StopIteration, tw.next)

        tw = itertools.takewhile(bool, [1, 2, 3, 0, 1, 1])
        for x in range(3):
            assert tw.next() == x + 1

        raises(StopIteration, tw.next)

    def test_takewhile_wrongargs(self):
        import itertools

        tw = itertools.takewhile(None, [1])
        raises(TypeError, tw.next)

        raises(TypeError, itertools.takewhile, bool, None)
