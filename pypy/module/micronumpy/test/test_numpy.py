
from pypy.conftest import gettestobjspace

class AppTestSDArray(object):
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=('micronumpy',))
        cls.w_compare = cls.space.appexec([],
        """():
           def compare(a, b):
               for x, y in zip(a, b):
                   if x != y: return False
                   assert type(x) == type(y)
               return True
           return compare""")
        cls.w_length = cls.space.appexec([], """(): return 16""")
        cls.w_value = cls.space.appexec([], """(): return 3.0""")

    def test_type_array(self):
        compare = self.compare
        from numpy import array
        for data_type in (int, float):
            data = [data_type(x) for x in xrange(4)] 
            ar = array(data)
            assert compare(ar, data)

    def test_sdarray_operators(self):
        from operator import mul, div, add, sub
        #FIXME: overkill...
        for data_type in (int, float):
            for operator in (mul, div, add, sub):
                for value in xrange(1, 16):
                    compare = self.compare
                    from numpy import array
                    data = [data_type(x) for x in range(self.length)]
                    ar = array(data)
                    assert compare(operator(ar, value), [operator(x, value) for x in data])

    def test_operator_result_types(self):
        skip("Haven't implemented dispatching for array/array operations")
        from operator import mul, div, add, sub
        from numpy import array
        types = {
                 (int, int): int,
                 (int, float): float,
                 (float, int): float,
                 (float, float): float
                }

        for operand_types, result_type in types.iteritems():
            for operator in (mul, div, add, sub):
                a_type, b_type = operand_types
                a = array(xrange(1, self.length + 1), dtype=a_type)
                b = array(xrange(1, self.length + 1), dtype=b_type)

                c = operator(a, b)
                assert c.dtype == result_type

                d = operator(b, a)
                assert d.dtype == result_type

                e = operator(a, b_type(self.value))
                assert e.dtype == result_type

                f = operator(a_type(self.value), b)
                assert f.dtype == result_type

    def test_iter(self):
        from numpy import array
        for iterable_type in (list, tuple):
            for data_type in (int, float):
                data = iterable_type([data_type(x) for x in xrange(self.length)])
                ar = array(data, dtype=data_type)
                ar_data = iterable_type([x for x in ar])
                assert ar_data == data

    def test_iterable_construction(self):
        compare = self.compare
        from numpy import array
        ar = array(xrange(4))

        assert compare(ar, xrange(4))

    def test_zeroes(self):
        from numpy import zeros
        for data_type in (int, float):
            ar = zeros(3, dtype=int)
            assert ar[0] == data_type(0.0)
    
    def test_setitem_getitem(self):
        from numpy import zeros
        ar = zeros(8, dtype=int)
        assert ar[0] == 0
        ar[1] = 3
        assert ar[1] == 3
        raises((TypeError, ValueError), ar.__getitem__, 'xyz')
        raises(IndexError, ar.__getitem__, 38)
        assert ar[-2] == 0
        assert ar[-7] == 3
        assert len(ar) == 8

    def test_minimum(self):
        from numpy import zeros, minimum
        ar = zeros(5, dtype=int)
        ar2 = zeros(5, dtype=int)
        ar[0] = 3
        ar[1] = -3
        ar[2] = 8
        ar2[3] = -1
        ar2[4] = 8
        x = minimum(ar, ar2)
        assert x[0] == 0
        assert x[1] == -3
        assert x[2] == 0
        assert x[3] == -1
        assert x[4] == 0
        assert len(x) == 5
        raises(ValueError, minimum, ar, zeros(3, dtype=int))

class AppTestMultiDim(object):
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=('micronumpy',))

    def test_multidim(self):
        from numpy import zeros
        ar = zeros((3, 3), dtype=int)
        assert ar[0, 2] == 0
        raises(IndexError, ar.__getitem__, (3, 0))
        assert ar[-2, 1] == 0

    def test_multidim_getset(self):
        from numpy import zeros
        ar = zeros((3, 3, 3), dtype=int)
        ar[1, 2, 1] = 3
        assert ar[1, 2, 1] == 3
        assert ar[-2, 2, 1] == 3
        assert ar[2, 2, 1] == 0
        assert ar[-2, 2, -2] == 3

    def test_len(self):
        from numpy import zeros
        assert len(zeros((3, 2, 1), dtype=int)) == 3
