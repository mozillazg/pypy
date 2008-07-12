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
            itertools.dropwhile(bool, []),
            itertools.ifilter(None, []),
            itertools.ifilterfalse(None, []),
            itertools.islice([], 0),
            itertools.chain(),
            itertools.imap(None),
            ]

        for it in iterables:
            assert hasattr(it, '__iter__')
            assert iter(it) is it
            assert hasattr(it, 'next')
            assert callable(it.next)

    def test_count(self):
        import itertools

        it = itertools.count()
        for x in range(10):
            assert it.next() == x

    def test_count_firstval(self):
        import itertools

        it = itertools.count(3)
        for x in range(10):
            assert it.next() == x + 3

    def test_count_overflow(self):
        import itertools, sys

        it = itertools.count(sys.maxint)
        assert it.next() == sys.maxint
        raises(OverflowError, it.next) 
        raises(OverflowError, it.next) 

        raises(OverflowError, itertools.count, sys.maxint + 1)

    def test_repeat(self):
        import itertools

        o = object()
        it = itertools.repeat(o)

        for x in range(10):
            assert o is it.next()

    def test_repeat_times(self):
        import itertools

        times = 10
        it = itertools.repeat(None, times=times)
        for i in range(times):
            it.next()
        raises(StopIteration, it.next)

        it = itertools.repeat(None, times=None)
        for x in range(10):
            it.next()    # Should be no StopIteration

        it = itertools.repeat(None, times=0)
        raises(StopIteration, it.next)
        raises(StopIteration, it.next)

        it = itertools.repeat(None, times=-1)
        raises(StopIteration, it.next)
        raises(StopIteration, it.next)

    def test_repeat_overflow(self):
        import itertools
        import sys

        raises(OverflowError, itertools.repeat, None, sys.maxint + 1)

    def test_takewhile(self):
        import itertools

        it = itertools.takewhile(bool, [])
        raises(StopIteration, it.next)

        it = itertools.takewhile(bool, [False, True, True])
        raises(StopIteration, it.next)

        it = itertools.takewhile(bool, [1, 2, 3, 0, 1, 1])
        for x in [1, 2, 3]:
            assert it.next() == x

        raises(StopIteration, it.next)

    def test_takewhile_wrongargs(self):
        import itertools

        it = itertools.takewhile(None, [1])
        raises(TypeError, it.next)

        raises(TypeError, itertools.takewhile, bool, None)

    def test_dropwhile(self):
        import itertools

        it = itertools.dropwhile(bool, [])
        raises(StopIteration, it.next)

        it = itertools.dropwhile(bool, [True, True, True])
        raises(StopIteration, it.next)

        def is_odd(arg):
            return (arg % 2 == 1)

        it = itertools.dropwhile(is_odd, [1, 3, 5, 2, 4, 6])
        for x in [2, 4, 6]:
            assert it.next() == x

        raises(StopIteration, it.next)

    def test_takewhile_wrongargs(self):
        import itertools

        it = itertools.dropwhile(None, [1])
        raises(TypeError, it.next)

        raises(TypeError, itertools.dropwhile, bool, None)

    def test_ifilter(self):
        import itertools

        it = itertools.ifilter(None, [])
        raises(StopIteration, it.next)

        it = itertools.ifilter(None, [1, 0, 2, 3, 0])
        for x in [1, 2, 3]:
            assert it.next() == x
        raises(StopIteration, it.next)

        def is_odd(arg):
            return (arg % 2 == 1)

        it = itertools.ifilter(is_odd, [1, 2, 3, 4, 5, 6])
        for x in [1, 3, 5]:
            assert it.next() == x
        raises(StopIteration, it.next)

    def test_ifilter_wrongargs(self):
        import itertools

        it = itertools.ifilter(0, [1])
        raises(TypeError, it.next)

        raises(TypeError, itertools.ifilter, bool, None)

    def test_ifilterfalse(self):
        import itertools

        it = itertools.ifilterfalse(None, [])
        raises(StopIteration, it.next)

        it = itertools.ifilterfalse(None, [1, 0, 2, 3, 0])
        for x in [0, 0]:
            assert it.next() == x
        raises(StopIteration, it.next)

        def is_odd(arg):
            return (arg % 2 == 1)

        it = itertools.ifilterfalse(is_odd, [1, 2, 3, 4, 5, 6])
        for x in [2, 4, 6]:
            assert it.next() == x
        raises(StopIteration, it.next)

    def test_ifilterfalse_wrongargs(self):
        import itertools

        it = itertools.ifilterfalse(0, [1])
        raises(TypeError, it.next)

        raises(TypeError, itertools.ifilterfalse, bool, None)

    def test_islice(self):
        import itertools

        it = itertools.islice([], 0)
        raises(StopIteration, it.next)

        it = itertools.islice([1, 2, 3], 0)
        raises(StopIteration, it.next)

        it = itertools.islice([1, 2, 3, 4, 5], 3)
        for x in [1, 2, 3]:
            assert it.next() == x
        raises(StopIteration, it.next)

        it = itertools.islice([1, 2, 3, 4, 5], 3)
        for x in [1, 2, 3]:
            assert it.next() == x
        raises(StopIteration, it.next)

        it = itertools.islice([1, 2, 3, 4, 5], 1, 3)
        for x in [2, 3]:
            assert it.next() == x
        raises(StopIteration, it.next)

        it = itertools.islice([1, 2, 3, 4, 5], 0, 3, 2)
        for x in [1, 3]:
            assert it.next() == x
        raises(StopIteration, it.next)

        it = itertools.islice([1, 2, 3], 0, None)
        for x in [1, 2, 3]:
            assert it.next() == x
        raises(StopIteration, it.next)

    def test_islice_overflow(self):
        import itertools
        import sys

        raises(OverflowError, itertools.islice, [], sys.maxint + 1)

    def test_islice_wrongargs(self):
        import itertools

        raises(TypeError, itertools.islice, None, 0)

        raises(ValueError, itertools.islice, [], -1)

        raises(ValueError, itertools.islice, [], -1, 0)
        raises(ValueError, itertools.islice, [], 0, -1)

        raises(ValueError, itertools.islice, [], 0, 0, -1)
        raises(ValueError, itertools.islice, [], 0, 0, 0)
        raises(TypeError, itertools.islice, [], 0, 0, None)

        raises(TypeError, itertools.islice, [], 0, 0, 0, 0)

    def test_chain(self):
        import itertools
        
        it = itertools.chain()
        raises(StopIteration, it.next)
        raises(StopIteration, it.next)
        
        it = itertools.chain([1, 2, 3])
        for x in [1, 2, 3]:
            assert it.next() == x
        raises(StopIteration, it.next)

        it = itertools.chain([1, 2, 3], [4], [5, 6])
        for x in [1, 2, 3, 4, 5, 6]:
            assert it.next() == x
        raises(StopIteration, it.next)

        it = itertools.chain([], [], [1], [])
        assert it.next() == 1
        raises(StopIteration, it.next)

    def test_chain_wrongargs(self):
        import itertools
        
        raises(TypeError, itertools.chain, None)
        raises(TypeError, itertools.chain, [], None)
        
        for x in range(10):
            args = [()] * x + [None] + [()] * (9 - x)
            try:
                itertools.chain(*args)
            except TypeError, e:
                assert str(e) == "chain argument #%d must support iteration" % (x + 1)

    def test_imap(self):
        import itertools

        it = itertools.imap(None)
        raises(StopIteration, it.next)

        obj_list = [object(), object(), object()]
        it = itertools.imap(None, obj_list)
        for x in obj_list:
            assert it.next() == (x, )
        raises(StopIteration, it.next)

        it = itertools.imap(None, [1, 2, 3], [4], [5, 6])
        assert it.next() == (1, 4, 5)
        raises(StopIteration, it.next)

        it = itertools.imap(None, [], [], [1], [])
        raises(StopIteration, it.next)

        it = itertools.imap(str, [0, 1, 0, 1])
        for x in ['0', '1', '0', '1']:
            assert it.next() == x
        raises(StopIteration, it.next)

        import operator
        it = itertools.imap(operator.add, [1, 2, 3], [4, 5, 6])
        for x in [5, 7, 9]:
            assert it.next() == x
        raises(StopIteration, it.next)

    def test_docstrings(self):
        import itertools
        
        assert itertools.__doc__
        methods = [
            itertools.count,
            itertools.repeat,
            itertools.takewhile,
            itertools.dropwhile,
            itertools.ifilter,
            itertools.ifilterfalse,
            itertools.islice,
            itertools.chain,
            itertools.imap,
            ]
        for method in methods:
            assert method.__doc__

    def test_subclassing(self):
        import itertools
        # not sure how useful this actually is, but CPython implements it
        iterables = [
            (itertools.count, ()),
            (itertools.repeat, (None,)),
            (itertools.takewhile, (bool, [])),
            (itertools.dropwhile, (bool, [])),
            (itertools.ifilter, (None, [])),
            (itertools.ifilterfalse, (None, [])),
            (itertools.islice, ([], 0)),
            (itertools.chain, ()),
            (itertools.imap, (None,)),
            ]
        for cls, args in iterables:
            try:
                class A(cls):
                    pass
            except TypeError:
                pass
            else:
                assert False, "Subclassing should fail."

