
from pypy.conftest import gettestobjspace

class AppTestNumpy(object):
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
        cls.w_array_type_test = cls.space.appexec([cls.w_compare],
        """(compare):
        def array_type_test(data_type):
            from numpy import array
            data = [data_type(x) for x in xrange(4)] 
            ar = array(data)

            assert compare(ar, data)
        return array_type_test
        """)
        cls.w_array_scalar_op_test = cls.space.appexec([cls.w_compare],
        """(compare):
        def array_scalar_op_test(self, data_type, f, value, length):
            compare = self.compare
            from numpy import array
            data = [data_type(x) for x in range(length)]
            ar = array(data)
            assert compare(f(ar, value), [f(x, value) for x in data])
        return array_scalar_op_test
        """)

    def test_int_array(self): self.array_type_test(int)
    def test_float_array(self): self.array_type_test(float)

    def test_sdarray_operators(self):
        from operator import mul, div, add, sub
        self.array_scalar_op_test(self, float, mul, 2.0, 16)
        self.array_scalar_op_test(self, float, div, 2.0, 16)
        self.array_scalar_op_test(self, float, add, 2.0, 16)
        self.array_scalar_op_test(self, float, sub, 2.0, 16)

    def test_iterable_construction(self):
        compare = self.compare
        from numpy import array
        ar = array(xrange(4))

        assert compare(ar, xrange(4))

    def test_zeroes(self):
        from numpy import zeros
        ar = zeros(3, dtype=int)
        assert ar[0] == 0
    
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
