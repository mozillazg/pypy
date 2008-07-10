from pypy.conftest import gettestobjspace

class AppTestItertools: 

    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['itertools'])

    def test_count(self):
        import itertools

        c = itertools.count()
        for x in range(10):
            assert c.next() == x

    def test_count_iterable(self):
        import itertools

        c = itertools.count()
        assert hasattr(c, '__iter__')
        assert iter(c) is c
        assert hasattr(c, 'next')

    def test_count_param(self):
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

    def test_repeat(self):
        skip("for now")
        import itertools

        o = object()
        r = itertools.repeat(o)

        for x in range(10):
            assert o is r.next()

