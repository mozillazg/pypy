import py

from pypy.module.micronumpy.test.test_base import BaseNumpyAppTest

class AppTestDtype(BaseNumpyAppTest):
    def test_dtype(self):
        from numpy import dtype
        d = dtype('l')
        assert d.num == 7
        assert d.kind == 'i'
        assert dtype('int8').num == 1
        assert dtype('i1').num == 1
        assert dtype(d) is d

    def test_dtype_with_types(self):
        from numpy import dtype
        assert dtype(bool).num == 0
        assert dtype(int).num == 7
        assert dtype(long).num == 9
        assert dtype(float).num == 12

    def test_repr_str(self):
        from numpy import dtype
        d = dtype('?')
        assert repr(d) == "dtype('bool')"
        assert str(d) == "bool"
    
    def test_bool_array(self):
        from numpy import array
        a = array([0, 1, 2, 2.5], dtype='?')
        assert a[0] is False
        for i in xrange(1, 4):
            assert a[i] is True

    def test_overflow(self):
        from numpy import array
        # only one 32-bit system for now.. will change to 'i' when we can
        assert array([3], '?')[0] == True
        assert array([128], 'b')[0] == -128
        assert array([256], 'B')[0] == 0
        assert array([32768], 'h')[0] == -32768
        assert array([65536], 'H')[0] == 0
        raises(OverflowError, "array([2147483648], 'i')")
        raises(OverflowError, "array([4294967296], 'I')")
        raises(OverflowError, "array([9223372036854775808], 'q')")
        raises(OverflowError, "array([18446744073709551616], 'Q')")

    def test_int_array(self):
        from numpy import array
        a = array([1.5, 2.5, 3.5], 'l')
        assert a[0] == 1
        assert a[1] == 2
        assert a[2] == 3

    def test_bool_binop_types(self):
        from numpy import array, dtype
        types = ('?','b','B','h','H','i','I','l','L','q','Q','f','d','g')
        dtypes = [dtype(t) for t in types]
        N = len(types)
        a = array([True], '?')
        for i in xrange(N):
            assert (a + array([0], types[i])).dtype is dtypes[i]

    def test_binop_types(self):
        from numpy import array, dtype
        tests = (('b','B','h'), ('b','h','h'), ('b','H','i'), ('b','I','q'),
                 ('b','Q','d'), ('B','H','H'), ('B','I','I'), ('B','Q','Q'),
                 ('B','h','h'), ('h','H','i'), ('h','i','i'), ('H','i','i'),
                 ('H','I','I'), ('i','I','q'), ('I','q','q'), ('q','Q','d'),
                 ('i','f','f'), ('q','f','d'), ('Q','f','d'))
        for d1, d2, dout in tests:
            assert (array([1], d1) + array([1], d2)).dtype is dtype(dout)
